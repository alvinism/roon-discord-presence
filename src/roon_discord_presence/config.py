"""TOML configuration: loading, validation and secret references."""

import dataclasses
import os
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import DEFAULT_DISCORD_CLIENT_ID

STATUS_DISPLAYS = ("name", "state", "details")
PROVIDERS = ("none", "s3", "command")


class ConfigError(Exception):
    pass


@dataclass
class RoonConfig:
    host: str = "127.0.0.1"
    port: int = 9330
    zones: list[str] = field(default_factory=list)  # empty = follow any playing zone


@dataclass
class DiscordConfig:
    client_id: str = DEFAULT_DISCORD_CLIENT_ID
    fallback_image: str = ""      # asset key or URL shown when there is no cover
    status_display: str = "state"  # what the member list shows: app name, artist, or title


@dataclass
class S3Config:
    endpoint: str = ""
    bucket: str = ""
    region: str = "auto"
    access_key_id: str = ""
    secret_access_key: str = ""   # supports keychain:/env: references
    public_base_url: str = ""
    prefix: str = ""
    reupload_after_days: int = 20  # keep ahead of a bucket lifecycle rule


@dataclass
class CommandConfig:
    command: list[str] = field(default_factory=list)
    timeout: int = 30


@dataclass
class CoversConfig:
    provider: str = "none"
    size: int = 512
    s3: S3Config = field(default_factory=S3Config)
    command: CommandConfig = field(default_factory=CommandConfig)


@dataclass
class Config:
    roon: RoonConfig = field(default_factory=RoonConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    covers: CoversConfig = field(default_factory=CoversConfig)


def _build(cls, data, where):
    if not isinstance(data, dict):
        raise ConfigError(f"[{where}] must be a table")
    fields = {f.name: f for f in dataclasses.fields(cls)}
    unknown = set(data) - set(fields)
    if unknown:
        raise ConfigError(f"unknown key(s) in [{where}]: {', '.join(sorted(unknown))}")
    kwargs = {}
    for name, value in data.items():
        default = fields[name].default_factory() if callable(fields[name].default_factory) \
            else fields[name].default
        if dataclasses.is_dataclass(default):
            kwargs[name] = _build(type(default), value, f"{where}.{name}")
        elif type(value) is not type(default):  # strict: rejects true for an int, etc.
            raise ConfigError(f"{where}.{name} must be {type(default).__name__}")
        else:
            kwargs[name] = value
    return cls(**kwargs)


def validate(cfg: Config) -> None:
    if cfg.discord.status_display not in STATUS_DISPLAYS:
        raise ConfigError(f"discord.status_display must be one of {', '.join(STATUS_DISPLAYS)}")
    if cfg.covers.provider not in PROVIDERS:
        raise ConfigError(f"covers.provider must be one of {', '.join(PROVIDERS)}")
    if cfg.covers.provider == "s3":
        s3 = cfg.covers.s3
        missing = [k for k in ("endpoint", "bucket", "access_key_id", "secret_access_key",
                               "public_base_url") if not getattr(s3, k)]
        if missing:
            raise ConfigError(f"covers.s3 is missing: {', '.join(missing)}")
    if cfg.covers.provider == "command" and not cfg.covers.command.command:
        raise ConfigError("covers.command.command must be a non-empty list")


def load(path: Path) -> Config:
    """Load config; a missing file means all defaults."""
    try:
        data = tomllib.loads(path.read_text())
    except FileNotFoundError:
        data = {}
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from e
    cfg = _build(Config, data, "config")
    validate(cfg)
    return cfg


def resolve_secret(value: str) -> str:
    """Resolve `keychain:<service>[/<account>]` and `env:<VAR>` references; else literal."""
    if value.startswith("keychain:"):
        service, _, account = value.removeprefix("keychain:").partition("/")
        cmd = ["security", "find-generic-password", "-s", service,
               *(["-a", account] if account else []), "-w"]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()
        except subprocess.CalledProcessError as e:
            raise ConfigError(f"Keychain item not found: {value}") from e
    if value.startswith("env:"):
        var = value.removeprefix("env:")
        if var not in os.environ:
            raise ConfigError(f"environment variable not set: {var}")
        return os.environ[var]
    return value


TEMPLATE = '''\
# roon-discord-presence configuration
# Docs: https://github.com/alvinism/roon-discord-presence#configuration

[roon]
host = "127.0.0.1"   # Roon Core address; use its IP if the Core runs on another machine
port = 9330
# zones = ["Living Room"]   # only follow these zones (default: whichever zone is playing)

[discord]
# client_id = "..."         # your own Discord application, to change the "Listening to ..." name
fallback_image = ""          # asset key or https URL shown when no cover is available
status_display = "state"     # member list shows: "name" (app), "state" (artist), "details" (title)

[covers]
provider = "none"            # none | s3 | command   (see docs/covers.md)
size = 512

# [covers.s3]                # any S3-compatible storage: Cloudflare R2, AWS S3, Backblaze B2, MinIO
# endpoint = "https://<account-id>.r2.cloudflarestorage.com"
# bucket = "roon-covers"
# access_key_id = "..."
# secret_access_key = "keychain:roon-discord-presence"   # or "env:RDP_S3_SECRET"
# public_base_url = "https://covers.example.com"

# [covers.command]           # your own uploader: JPEG on stdin, file name as last arg, print URL
# command = ["/path/to/upload-cover.sh"]
# timeout = 30
'''
