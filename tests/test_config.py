import pytest

from roon_discord_presence import DEFAULT_DISCORD_CLIENT_ID
from roon_discord_presence.config import TEMPLATE, ConfigError, load, resolve_secret


def write(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text)
    return p


def test_missing_file_gives_defaults(tmp_path):
    cfg = load(tmp_path / "nope.toml")
    assert cfg.roon.host == "127.0.0.1"
    assert cfg.discord.client_id == DEFAULT_DISCORD_CLIENT_ID
    assert cfg.covers.provider == "none"


def test_template_is_valid(tmp_path):
    cfg = load(write(tmp_path, TEMPLATE))
    assert cfg.covers.provider == "none"


def test_s3_section(tmp_path):
    cfg = load(write(tmp_path, """
[covers]
provider = "s3"
[covers.s3]
endpoint = "https://acct.r2.cloudflarestorage.com"
bucket = "covers"
access_key_id = "AK"
secret_access_key = "env:SECRET"
public_base_url = "https://covers.example.com"
"""))
    assert cfg.covers.s3.bucket == "covers"
    assert cfg.covers.s3.region == "auto"


@pytest.mark.parametrize("text, message", [
    ('[roon]\nhots = "x"', "unknown key"),
    ('[roon]\nport = "9330"', "roon.port must be int"),
    ('[roon]\nport = true', "roon.port must be int"),
    ('[covers]\nprovider = "imgur"', "covers.provider"),
    ('[covers]\nprovider = "s3"', "covers.s3 is missing"),
    ('[covers]\nprovider = "command"', "covers.command.command"),
    ('[discord]\nstatus_display = "artist"', "status_display"),
])
def test_invalid(tmp_path, text, message):
    with pytest.raises(ConfigError, match=message):
        load(write(tmp_path, text))


def test_resolve_secret_env(monkeypatch):
    monkeypatch.setenv("RDP_TEST_SECRET", "s3cr3t")
    assert resolve_secret("env:RDP_TEST_SECRET") == "s3cr3t"
    assert resolve_secret("plain") == "plain"
    with pytest.raises(ConfigError):
        resolve_secret("env:RDP_DOES_NOT_EXIST")


def test_resolve_secret_keychain(monkeypatch):
    import subprocess
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="from-keychain\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert resolve_secret("keychain:svc/acct") == "from-keychain"
    assert resolve_secret("keychain:svc") == "from-keychain"
    assert calls == [
        ["security", "find-generic-password", "-s", "svc", "-a", "acct", "-w"],
        ["security", "find-generic-password", "-s", "svc", "-w"],
    ]
