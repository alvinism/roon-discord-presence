"""Interactive `setup`: write the config, check each piece works, start the service."""

import json
import socket
import subprocess
import sys
import time
import urllib.request

from . import DEFAULT_DISCORD_CLIENT_ID, paths, service
from .config import Config, ConfigError, load

KEYCHAIN_SERVICE = "roon-discord-presence"
KEYCHAIN_ACCOUNT = "s3"
APPROVAL_WAIT = 180  # s


# prompts --------------------------------------------------------------------------------------

def ask(question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{question}{suffix}: ").strip()
    return answer or default


def ask_yes(question: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{question} [{hint}]: ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes", "n", "no"):
            return answer.startswith("y")


def ask_choice(question: str, choices: list[tuple[str, str]], default: str) -> str:
    print(question)
    for i, (key, label) in enumerate(choices, 1):
        print(f"  {i}. {label}{'  (current)' if key == default else ''}")
    keys = [k for k, _ in choices]
    while True:
        answer = input(f"Choose 1-{len(choices)} [{keys.index(default) + 1}]: ").strip()
        if not answer:
            return default
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return keys[int(answer) - 1]


def heading(text: str):
    print(f"\n── {text} " + "─" * max(0, 60 - len(text)))


# checks ---------------------------------------------------------------------------------------

def roon_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except OSError:
        return False


def store_keychain_secret() -> str:
    """Let `security` prompt for the secret itself so it never appears in argv or our memory."""
    print("Enter the secret access key (input is hidden; you will be asked twice).")
    subprocess.run(["security", "add-generic-password", "-U", "-s", KEYCHAIN_SERVICE,
                    "-a", KEYCHAIN_ACCOUNT, "-w"], check=True)
    return f"keychain:{KEYCHAIN_SERVICE}/{KEYCHAIN_ACCOUNT}"


def test_s3(cfg: Config) -> str | None:
    """Upload, fetch publicly, delete a tiny test object. Returns an error message or None."""
    try:
        from .covers.s3 import S3Provider
        provider = S3Provider(cfg.covers.s3)
    except ConfigError as e:
        return str(e)
    name = f"rdp-setup-test-{int(time.time())}.txt"
    key = provider.prefix + name
    try:
        provider.client.put_object(Bucket=cfg.covers.s3.bucket, Key=key, Body=b"ok",
                                   ContentType="text/plain")
    except Exception as e:
        return f"upload failed: {e}"
    try:
        url = f"{provider.base_url}/{key}"
        req = urllib.request.Request(url, headers={"User-Agent": "roon-discord-presence"})
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.read() != b"ok":
                return f"{url} did not return the uploaded file"
    except Exception as e:
        return f"uploaded, but could not fetch it publicly ({e}); check public_base_url"
    finally:
        try:
            provider.client.delete_object(Bucket=cfg.covers.s3.bucket, Key=key)
        except Exception:
            pass
    return None


# config file ----------------------------------------------------------------------------------

def _toml(value) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)  # JSON strings are valid TOML strings
    if isinstance(value, list):
        return "[" + ", ".join(_toml(v) for v in value) + "]"
    return str(value)


def render(cfg: Config) -> str:
    """Config as TOML, writing only values that differ from the defaults."""
    default = Config()
    lines = ["# Written by `roon-discord-presence setup`. All keys are optional.",
             "# Docs: https://github.com/alvinism/roon-discord-presence#configuration"]

    def section(name, obj, base, keys):
        body = [f"{k} = {_toml(getattr(obj, k))}" for k in keys
                if getattr(obj, k) != getattr(base, k)]
        if body:
            lines.extend(["", f"[{name}]", *body])

    section("roon", cfg.roon, default.roon, ["host", "port", "zones"])
    section("discord", cfg.discord, default.discord,
            ["client_id", "fallback_image", "status_display"])
    lines.extend(["", "[covers]", f"provider = {_toml(cfg.covers.provider)}"])
    if cfg.covers.size != default.covers.size:
        lines.append(f"size = {cfg.covers.size}")
    if cfg.covers.provider == "s3":
        section("covers.s3", cfg.covers.s3, default.covers.s3,
                ["endpoint", "bucket", "region", "access_key_id", "secret_access_key",
                 "public_base_url", "prefix", "reupload_after_days"])
    if cfg.covers.provider == "command":
        section("covers.command", cfg.covers.command, default.covers.command,
                ["command", "timeout"])
    return "\n".join(lines) + "\n"


# steps ----------------------------------------------------------------------------------------

def setup_roon(cfg: Config):
    heading("Roon")
    while True:
        cfg.roon.host = ask("Roon Core address (127.0.0.1 if it runs on this Mac)", cfg.roon.host)
        port = ask("Port", str(cfg.roon.port))
        cfg.roon.port = int(port) if port.isdigit() else cfg.roon.port
        if roon_reachable(cfg.roon.host, cfg.roon.port):
            print(f"✓ Roon Core reachable at {cfg.roon.host}:{cfg.roon.port}")
            return
        print(f"✗ Nothing answering at {cfg.roon.host}:{cfg.roon.port}. Is Roon Server running? "
              "(Roon → Settings → General shows the Core's address.)")
        if not ask_yes("Try another address?"):
            return


def setup_discord(cfg: Config):
    heading("Discord")
    print("Your status will read “Listening to <app name>”. The default app is shared by all")
    print("users; use your own Discord application to choose the name and images.")
    current = "" if cfg.discord.client_id == DEFAULT_DISCORD_CLIENT_ID else cfg.discord.client_id
    client_id = ask("Discord application ID (empty = default)", current)
    cfg.discord.client_id = client_id or DEFAULT_DISCORD_CLIENT_ID


def setup_covers(cfg: Config):
    heading("Album art")
    print("Discord can only show covers from a public URL, so they need to be uploaded somewhere.")
    cfg.covers.provider = ask_choice("Where should covers go?", [
        ("none", "Nowhere — no album art"),
        ("s3", "An S3-compatible bucket (Cloudflare R2, AWS S3, Backblaze B2, MinIO…)"),
        ("command", "My own upload script"),
    ], cfg.covers.provider)

    if cfg.covers.provider == "s3":
        s3 = cfg.covers.s3
        while True:
            if not s3.endpoint and ask_yes("Is it Cloudflare R2?"):
                account = ask("R2 account ID")
                s3.endpoint = f"https://{account}.r2.cloudflarestorage.com"
                s3.region = "auto"
            s3.endpoint = ask("S3 endpoint URL", s3.endpoint)
            s3.region = ask("Region", s3.region)
            s3.bucket = ask("Bucket", s3.bucket)
            s3.access_key_id = ask("Access key ID", s3.access_key_id)
            if not s3.secret_access_key or ask_yes("Replace the stored secret key?", False):
                s3.secret_access_key = store_keychain_secret()
            s3.public_base_url = ask("Public URL of the bucket (e.g. https://covers.example.com)",
                                     s3.public_base_url).rstrip("/")
            print("Testing: upload, public fetch, delete…")
            error = test_s3(cfg)
            if error is None:
                print("✓ Covers will work")
                return
            print(f"✗ {error}")
            if not ask_yes("Change the settings and try again?"):
                if not ask_yes("Keep these settings anyway?", False):
                    cfg.covers.provider = "none"
                return

    if cfg.covers.provider == "command":
        print("The command gets the JPEG on stdin and the file name as last argument,")
        print("and must print the public https URL. See docs/covers.md.")
        current = " ".join(cfg.covers.command.command)
        cfg.covers.command.command = ask("Command", current).split()


def wait_for_roon() -> bool:
    print("\nNow open Roon → Settings → Extensions and click Enable next to “Discord Presence”.")
    print("Waiting", end="", flush=True)
    deadline = time.time() + APPROVAL_WAIT
    while time.time() < deadline:
        try:
            st = json.loads(paths.STATUS_FILE.read_text())
        except (OSError, ValueError):
            st = {}
        if st.get("roon") == "ok":
            print(f"\n✓ Paired with Roon Core “{st.get('core')}”")
            print("✓ Discord connected" if st.get("discord")
                  else "• Discord isn't open — the status appears once it is")
            return True
        print(".", end="", flush=True)
        time.sleep(2)
    print("\nStill waiting — it will pair as soon as you enable it in Roon.")
    return False


def run() -> int:
    if not sys.stdin.isatty():
        sys.exit("setup is interactive; run it in a terminal")
    print("roon-discord-presence setup — press Enter to keep the value in [brackets].")

    try:
        cfg = load(paths.CONFIG_FILE)
    except ConfigError as e:
        print(f"(Ignoring the existing config, it has an error: {e})")
        cfg = Config()

    try:
        setup_roon(cfg)
        setup_discord(cfg)
        setup_covers(cfg)

        heading("Save")
        text = render(cfg)
        if paths.CONFIG_FILE.exists():
            backup = paths.CONFIG_FILE.with_suffix(".toml.bak")
            backup.write_text(paths.CONFIG_FILE.read_text())
            print(f"Previous config saved to {backup}")
        paths.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        paths.CONFIG_FILE.write_text(text)
        paths.CONFIG_FILE.chmod(0o600)
        load(paths.CONFIG_FILE)  # sanity check what we wrote
        print(f"✓ Wrote {paths.CONFIG_FILE}")

        heading("Start")
        warning = service.ephemeral_install_warning()
        if warning:
            print(f"Not installing the background service: {warning}")
            return 1
        if not ask_yes("Run in the background now and at every login?"):
            print("Start later with: roon-discord-presence start")
            return 0
        print(service.restart() if service.is_loaded() else service.start())
        wait_for_roon()
        print("\nDone. Check anytime with: roon-discord-presence status")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled; nothing was changed unless shown above.")
        return 130
