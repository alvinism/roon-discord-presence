"""Run in the background via a launchd LaunchAgent (macOS)."""

import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

from . import APP_ID, paths

LABEL = APP_ID
PLIST = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"


def _domain() -> str:
    return f"gui/{os.getuid()}"


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def is_loaded() -> bool:
    return _launchctl("print", f"{_domain()}/{LABEL}").returncode == 0


def program_arguments() -> list[str]:
    return [sys.executable, "-m", "roon_discord_presence", "run"]


def ephemeral_install_warning() -> str | None:
    """uvx/pipx-run environments can vanish; launchd needs a stable interpreter path."""
    exe = sys.executable
    if "/.cache/uv/" in exe or "/pipx/.cache/" in exe:
        return ("this looks like a temporary environment; install it permanently first:\n"
                "  uv tool install roon-discord-presence")
    return None


def write_plist():
    paths.LOG_DIR.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": program_arguments(),
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},  # restart after crashes, not after `stop`
        "ThrottleInterval": 30,
        "ProcessType": "Background",
        "StandardErrorPath": str(paths.LAUNCHD_ERR),
        "EnvironmentVariables": {
            k: v for k, v in os.environ.items()
            if k in ("RDP_CONFIG_DIR", "RDP_STATE_DIR", "RDP_LOG_DIR")
        },
    }
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    with open(PLIST, "wb") as f:
        plistlib.dump(plist, f)


def start() -> str:
    if is_loaded():
        return "Already running"
    write_plist()
    r = _launchctl("bootstrap", _domain(), str(PLIST))
    if r.returncode != 0:
        raise RuntimeError(f"launchctl bootstrap failed: {r.stderr.strip()}")
    return "Started — runs at login"


def stop() -> str:
    if is_loaded():
        _launchctl("bootout", f"{_domain()}/{LABEL}")
        # bootout returns before the daemon finishes its clean shutdown (clearing Discord)
        for _ in range(50):
            if not is_loaded():
                break
            time.sleep(0.2)
    PLIST.unlink(missing_ok=True)
    return "Stopped — will not run at login"


def restart() -> str:
    # full reload rather than `kickstart -k`, so a changed interpreter path after upgrades
    # lands in the plist too
    stop()
    start()
    return "Restarted"
