"""Where config, state and logs live. Each base directory can be overridden by env var."""

import os
from pathlib import Path

from . import APP_NAME

_HOME = Path.home()

CONFIG_DIR = Path(os.environ.get("RDP_CONFIG_DIR") or _HOME / ".config" / APP_NAME)
STATE_DIR = Path(
    os.environ.get("RDP_STATE_DIR") or _HOME / "Library/Application Support" / APP_NAME
)
LOG_DIR = Path(os.environ.get("RDP_LOG_DIR") or _HOME / "Library/Logs" / APP_NAME)

CONFIG_FILE = CONFIG_DIR / "config.toml"
TOKEN_FILE = STATE_DIR / "roon_token"
COVERS_FILE = STATE_DIR / "covers.json"
STATUS_FILE = STATE_DIR / "status.json"
LOG_FILE = LOG_DIR / f"{APP_NAME}.log"
LAUNCHD_ERR = LOG_DIR / "launchd.err"
