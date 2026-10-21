"""Maps Roon image keys to published URLs, publishing new covers on a background thread."""

import hashlib
import json
import logging
import threading
import time
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .base import CoverProvider

log = logging.getLogger(__name__)

RECHECK = 86400        # call publish() again for a known cover after this (s)
RETRY = 300            # wait before retrying a failed cover (s)
FORGET = 30 * 86400    # drop entries unused for this long (s)


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read()


class CoverCache:
    def __init__(self, provider: CoverProvider, image_url: Callable[[str], str], path: Path,
                 fetcher: Callable[[str], bytes] = fetch, clock: Callable[[], float] = time.time):
        self.provider = provider
        self.image_url = image_url
        self.path = path
        self.fetch = fetcher
        self.clock = clock
        self.lock = threading.Lock()
        self.map = self._load()   # image_key -> {"url": str, "checked": epoch}
        self.pending: set[str] = set()
        self.failed: dict[str, float] = {}
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="covers")

    def get(self, image_key: str) -> str | None:
        """Return the cover URL if known; schedule a (re)publish when new or stale."""
        now = self.clock()
        with self.lock:
            entry = self.map.get(image_key)
            url = entry["url"] if entry else None
            if entry and now - entry["checked"] < RECHECK:
                return url
            if image_key in self.pending or now - self.failed.get(image_key, 0) < RETRY:
                return url
            self.pending.add(image_key)
        self.pool.submit(self._publish, image_key)
        return url

    def wait(self):
        """Block until queued work is done (tests and shutdown)."""
        self.pool.submit(lambda: None).result()

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)

    def _publish(self, image_key: str):
        try:
            data = self.fetch(self.image_url(image_key))
            filename = hashlib.sha256(data).hexdigest()[:32] + ".jpg"
            url = self.provider.publish(filename, data)
            with self.lock:
                self.map[image_key] = {"url": url, "checked": self.clock()}
                self._save()
        except Exception as e:
            log.warning("Cover %s failed: %s", image_key, e)
            with self.lock:
                self.failed[image_key] = self.clock()
        finally:
            with self.lock:
                self.pending.discard(image_key)

    def _load(self) -> dict:
        try:
            entries = json.loads(self.path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        cutoff = self.clock() - FORGET
        return {k: v for k, v in entries.items() if v.get("checked", 0) > cutoff}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.map))
        tmp.replace(self.path)
