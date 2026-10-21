"""Command line interface. Front-ends (Alfred, Raycast, …) only use `status --json` and
`start` / `stop` / `restart`."""

import argparse
import json
import os
import sys

from . import __version__, paths, service
from .config import TEMPLATE, ConfigError, load

STATUS_SCHEMA = 1


def _load_config():
    try:
        return load(paths.CONFIG_FILE)
    except ConfigError as e:
        sys.exit(f"Config error: {e}")


def status() -> dict:
    running = service.is_loaded()
    data = None
    if running:
        try:
            data = json.loads(paths.STATUS_FILE.read_text())
        except (OSError, ValueError):
            pass
    return {
        "schema": STATUS_SCHEMA,
        "service": "running" if running else "stopped",
        "state": _summary(running, data),
        **({k: data[k] for k in ("roon", "core", "discord", "covers", "playing", "shown",
                                 "zones", "updated") if k in data} if data else {}),
    }


def _summary(running: bool, data: dict | None) -> str:
    """One word for front-ends: stopped | starting | approve | roon-offline | idle | playing"""
    if not running:
        return "stopped"
    if not data:
        return "starting"
    if data["roon"] == "approve":
        return "approve"
    if data["roon"] != "ok":
        return "roon-offline"
    return "playing" if data.get("playing") else "idle"


def print_status(st: dict):
    lines = {
        "stopped": "Stopped (run `roon-discord-presence start`)",
        "starting": "Starting…",
        "approve": "Waiting for approval: enable “Discord Presence” in "
                   "Roon → Settings → Extensions",
        "roon-offline": "Cannot reach Roon Core (check [roon] host/port)",
        "idle": "Running · nothing playing",
    }
    if st["state"] == "playing":
        p = st["playing"]
        print(f"Playing: {p['title']} — {p['artist']} [{p['album']}] on {p['zone']}")
        print("Shown on Discord" if st.get("shown") else "Not shown on Discord yet")
    else:
        print(lines[st["state"]])
    if st["service"] == "running" and st["state"] not in ("starting",):
        print(f"Discord: {'connected' if st.get('discord') else 'not connected'}"
              f" · covers: {st.get('covers', 'none')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="roon-discord-presence",
                                     description="Show what Roon is playing on Discord.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("setup", help="guided setup: config, covers, background service")
    run_p = sub.add_parser("run", help="run in the foreground")
    run_p.add_argument("-v", "--verbose", action="store_true")
    sub.add_parser("start", help="run in the background now and at every login")
    sub.add_parser("stop", help="stop and disable running at login")
    sub.add_parser("restart", help="restart the background service (e.g. after config changes)")
    st_p = sub.add_parser("status", help="show what is going on")
    st_p.add_argument("--json", action="store_true", help="machine-readable output")
    cfg_p = sub.add_parser("config", help="manage the config file")
    cfg_sub = cfg_p.add_subparsers(dest="config_cmd", required=True)
    init_p = cfg_sub.add_parser("init", help="write a commented config file")
    init_p.add_argument("--force", action="store_true", help="overwrite an existing file")
    cfg_sub.add_parser("path", help="print the config file path")
    cfg_sub.add_parser("check", help="validate the config file")
    logs_p = sub.add_parser("logs", help="show the log")
    logs_p.add_argument("-f", "--follow", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "setup":
        from .wizard import run as setup
        return setup()

    if args.cmd == "run":
        from .daemon import run
        return run(_load_config(), args.verbose)

    if args.cmd in ("start", "stop", "restart"):
        if args.cmd != "stop":
            _load_config()  # fail early instead of crash-looping under launchd
            warning = service.ephemeral_install_warning()
            if warning:
                sys.exit(f"Refusing to install the service: {warning}")
        print(getattr(service, args.cmd)())
        return 0

    if args.cmd == "status":
        st = status()
        if args.json:
            print(json.dumps(st, ensure_ascii=False))
        else:
            print_status(st)
        return 0

    if args.cmd == "config":
        if args.config_cmd == "path":
            print(paths.CONFIG_FILE)
        elif args.config_cmd == "init":
            if paths.CONFIG_FILE.exists() and not args.force:
                sys.exit(f"{paths.CONFIG_FILE} already exists (use --force to overwrite)")
            paths.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            paths.CONFIG_FILE.write_text(TEMPLATE)
            print(f"Wrote {paths.CONFIG_FILE}")
        elif args.config_cmd == "check":
            cfg = _load_config()
            if cfg.covers.provider == "s3":
                from .config import resolve_secret
                try:
                    resolve_secret(cfg.covers.s3.secret_access_key)
                except ConfigError as e:
                    sys.exit(f"Config error: {e}")
            print(f"OK: {paths.CONFIG_FILE} (covers: {cfg.covers.provider})")
        return 0

    if args.cmd == "logs":
        if not paths.LOG_FILE.exists():
            sys.exit(f"No log yet at {paths.LOG_FILE}")
        cmd = ["tail", "-n", "50"] + (["-F"] if args.follow else []) + [str(paths.LOG_FILE)]
        os.execvp("tail", cmd)
    return 0
