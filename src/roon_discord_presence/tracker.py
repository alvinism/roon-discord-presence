"""Decide what to show on Discord from Roon's zones, without spamming Discord."""

import logging
import time
from collections.abc import Callable

from pypresence import ActivityType, StatusDisplayType

from .config import Config

log = logging.getLogger(__name__)

MIN_PUSH_GAP = 4.0     # Discord allows ~5 activity updates / 20 s
SEEK_TOLERANCE = 2.0   # re-push timestamps only if they drift more than this (s)
IDLE_GRACE = 5.0       # keep presence through short "loading" gaps before clearing (s)
HEARTBEAT = 60.0       # re-send unchanged presence so a reloaded Discord picks it up (s)

STATUS_DISPLAY = {
    "name": StatusDisplayType.NAME,
    "state": StatusDisplayType.STATE,
    "details": StatusDisplayType.DETAILS,
}


def clip(text: str | None, limit: int = 128) -> str:
    """Discord requires 2..128 characters for text fields."""
    text = (text or "").strip()
    if len(text) < 2:
        text = text.ljust(2, "⠀")  # braille blank pads without showing
    return text if len(text) <= limit else text[: limit - 1] + "…"


class Tracker:
    def __init__(self, zones: Callable[[], list[dict]], discord, covers, cfg: Config,
                 clock: Callable[[], float] = time.monotonic,
                 wall: Callable[[], float] = time.time):
        self.zones = zones
        self.discord = discord
        self.covers = covers  # CoverCache or None
        self.cfg = cfg
        self.clock, self.wall = clock, wall
        self.zone_id: str | None = None
        self.pushed: tuple | None = None   # (track_key, start, cover) last sent to Discord
        self.last_push = float("-inf")
        self.last_playing = float("-inf")
        self.now: dict | None = None       # what is playing, for status reporting

    def pick_zone(self) -> dict | None:
        allowed = set(self.cfg.roon.zones)
        playing = [z for z in self.zones()
                   if z.get("state") == "playing" and z.get("now_playing")
                   and (not allowed or z.get("display_name") in allowed)]
        for z in playing:
            if z["zone_id"] == self.zone_id:
                return z
        return playing[0] if playing else None

    def tick(self):
        if not self.discord.connected:
            self.pushed = None  # Discord (re)started: whatever we sent before is gone
        zone = self.pick_zone()

        if zone is None:
            self.now = None
            self.discord.ensure()  # stay connected while idle so status reflects Discord
            if self.pushed and self.clock() - self.last_playing > IDLE_GRACE:
                if self.discord.clear():
                    log.info("Nothing playing, cleared presence")
                    self.pushed = None
            return

        self.last_playing = self.clock()
        if zone["zone_id"] != self.zone_id:
            self.zone_id = zone["zone_id"]
            log.info("Following zone: %s", zone.get("display_name"))

        np = zone["now_playing"]
        lines = np.get("three_line") or {}
        title, artist, album = lines.get("line1"), lines.get("line2"), lines.get("line3")
        length = np.get("length")
        seek = zone.get("seek_position", np.get("seek_position")) or 0
        image_key = np.get("image_key")
        cover = self.covers.get(image_key) if (self.covers and image_key) else None
        self.now = {"zone": zone.get("display_name"), "title": title, "artist": artist,
                    "album": album, "cover": cover}

        track_key = (self.zone_id, title, artist, album, length)
        start = int(self.wall() - seek)
        if self.pushed:
            unchanged = (self.pushed[0] == track_key and self.pushed[2] == cover
                         and abs(self.pushed[1] - start) <= SEEK_TOLERANCE)
            if unchanged and self.clock() - self.last_push < HEARTBEAT:
                return
        if self.clock() - self.last_push < MIN_PUSH_GAP:
            return

        large_image = cover or self.cfg.discord.fallback_image or None
        ok = self.discord.update(
            activity_type=ActivityType.LISTENING,
            status_display_type=STATUS_DISPLAY[self.cfg.discord.status_display],
            details=clip(title),
            state=clip(artist),
            large_image=large_image,
            large_text=clip(album) if (album and large_image) else None,
            start=start,
            end=start + int(length) if length else None,
        )
        if ok:
            self.last_push = self.clock()
            if not self.pushed or self.pushed[0] != track_key:
                log.info("Now playing: %s — %s [%s]", artist, title, album)
            self.pushed = (track_key, start, cover)

    @property
    def shown(self) -> bool:
        return self.pushed is not None
