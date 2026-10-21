"""The long-running process: wire Roon, Discord and covers together."""

import json
import logging
import os
import signal
import sys
import time
from logging.handlers import RotatingFileHandler

from . import APP_ID, __version__, paths
from .config import Config
from .covers import CoverCache, make_provider
from .discord import Discord
from .roon import RoonClient
from .tracker import Tracker

log = logging.getLogger(__name__)

TICK = 1.0

APPINFO = {
    "extension_id": APP_ID,
    "display_name": "Discord Presence",
    "display_version": __version__,
    "publisher": "roon-discord-presence",
    "email": "11978267+alvinism@users.noreply.github.com",
    "website": "https://github.com/alvinism/roon-discord-presence",
}


def setup_logging(verbose: bool = False):
    paths.LOG_DIR.mkdir(parents=True, exist_ok=True)
    if paths.LAUNCHD_ERR.exists():
        paths.LAUNCHD_ERR.write_text("")  # launchd opens it O_APPEND, so later writes start at 0
    handler = RotatingFileHandler(paths.LOG_FILE, maxBytes=512_000, backupCount=1)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handlers: list[logging.Handler] = [handler]
    if sys.stderr.isatty():
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, handlers=handlers,
                        force=True)
    for name in ("websocket", "asyncio", "botocore", "boto3", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)


def roon_status_line(roon: RoonClient, discord: Discord, tracker: Tracker) -> tuple[str, bool]:
    if not discord.connected:
        return "Waiting for Discord to open", False
    if tracker.now and tracker.shown:
        n = tracker.now
        return f"Showing: {n['title']} — {n['artist']} ({n['zone']})", False
    return "Connected to Discord · nothing playing", False


def write_status(status: dict):
    paths.STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.STATUS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(status, ensure_ascii=False))
    tmp.replace(paths.STATUS_FILE)


def run(cfg: Config, verbose: bool = False) -> int:
    setup_logging(verbose)
    log.info("roon-discord-presence %s starting (pid %d)", __version__, os.getpid())

    stopping = False

    def on_signal(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    roon = RoonClient(cfg.roon.host, cfg.roon.port, APPINFO, paths.TOKEN_FILE)
    discord = Discord(cfg.discord.client_id)
    provider = make_provider(cfg.covers)
    covers = CoverCache(provider, lambda key: roon.image_url(key, cfg.covers.size),
                        paths.COVERS_FILE) if provider else None
    log.info("Cover provider: %s", provider.name if provider else "none")
    tracker = Tracker(roon.zones, discord, covers, cfg)

    roon.start()
    last_status = None
    try:
        while not stopping:
            if roon.paired:
                try:
                    tracker.tick()
                except Exception:
                    log.exception("Tick failed")
                roon.set_status(*roon_status_line(roon, discord, tracker))
            status = {
                "pid": os.getpid(),
                "version": __version__,
                "roon": roon.state,
                "core": roon.core_name,
                "discord": discord.connected,
                "covers": provider.name if provider else "none",
                "playing": tracker.now if roon.paired else None,
                "shown": tracker.shown,
                "zones": sorted(({"name": z.get("display_name"), "state": z.get("state")}
                                 for z in roon.zones()), key=lambda z: z["name"] or ""),
            }
            if status != last_status:
                write_status(dict(status, updated=int(time.time())))
                last_status = status
            time.sleep(TICK)
    finally:
        log.info("Shutting down")
        discord.close()
        if covers:
            covers.close()
        roon.stop()
        paths.STATUS_FILE.unlink(missing_ok=True)
    return 0
