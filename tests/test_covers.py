import json
import sys

import pytest

from roon_discord_presence.config import CommandConfig
from roon_discord_presence.covers.cache import FORGET, RECHECK, RETRY, CoverCache
from roon_discord_presence.covers.command import CommandProvider


class FakeProvider:
    name = "fake"

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def publish(self, filename, data):
        self.calls.append(filename)
        if self.fail:
            raise RuntimeError("boom")
        return f"https://covers.example.com/{filename}"


def make(tmp_path, provider, now):
    return CoverCache(provider, lambda key: f"roon://{key}", tmp_path / "covers.json",
                      fetcher=lambda url: url.encode(), clock=lambda: now[0])


def test_publishes_once_then_serves_from_map(tmp_path):
    now = [1000.0]
    provider = FakeProvider()
    cache = make(tmp_path, provider, now)
    assert cache.get("k1") is None  # first call schedules
    cache.wait()
    url = cache.get("k1")
    assert url.startswith("https://covers.example.com/") and url.endswith(".jpg")
    cache.get("k1")
    cache.wait()
    assert len(provider.calls) == 1
    assert json.loads((tmp_path / "covers.json").read_text())["k1"]["url"] == url


def test_rechecks_stale_entries_but_keeps_serving(tmp_path):
    now = [1000.0]
    provider = FakeProvider()
    cache = make(tmp_path, provider, now)
    cache.get("k1")
    cache.wait()
    now[0] += RECHECK + 1
    assert cache.get("k1") is not None
    cache.wait()
    assert len(provider.calls) == 2


def test_failures_back_off(tmp_path):
    now = [1000.0]
    provider = FakeProvider(fail=True)
    cache = make(tmp_path, provider, now)
    cache.get("k1")
    cache.wait()
    cache.get("k1")
    cache.wait()
    assert len(provider.calls) == 1
    now[0] += RETRY + 1
    cache.get("k1")
    cache.wait()
    assert len(provider.calls) == 2


def test_forgets_old_entries_on_load(tmp_path):
    (tmp_path / "covers.json").write_text(json.dumps({
        "old": {"url": "https://x/old.jpg", "checked": 0},
        "new": {"url": "https://x/new.jpg", "checked": FORGET + 500},
    }))
    cache = make(tmp_path, FakeProvider(), [FORGET + 1000])
    assert set(cache.map) == {"new"}


def script(tmp_path, body):
    p = tmp_path / "upload.py"
    p.write_text(body)
    return [sys.executable, str(p)]


def test_command_provider_reads_url(tmp_path):
    cmd = script(tmp_path, "import sys\n"
                           "data = sys.stdin.buffer.read()\n"
                           "print('uploading', len(data), file=sys.stderr)\n"
                           "print('https://covers.example.com/' + sys.argv[1])\n")
    provider = CommandProvider(CommandConfig(command=cmd))
    assert provider.publish("abc.jpg", b"jpeg") == "https://covers.example.com/abc.jpg"


@pytest.mark.parametrize("body, message", [
    ("import sys; sys.exit(3)", "exited 3"),
    ("print('not a url')", "https URL"),
])
def test_command_provider_errors(tmp_path, body, message):
    provider = CommandProvider(CommandConfig(command=script(tmp_path, body)))
    with pytest.raises(RuntimeError, match=message):
        provider.publish("abc.jpg", b"jpeg")
