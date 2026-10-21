from roon_discord_presence.config import Config
from roon_discord_presence.tracker import HEARTBEAT, IDLE_GRACE, MIN_PUSH_GAP, Tracker, clip


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class FakeDiscord:
    def __init__(self):
        self.connected = True
        self.updates = []
        self.clears = 0

    def ensure(self):
        return self.connected

    def update(self, **kw):
        if not self.connected:
            return False
        self.updates.append(kw)
        return True

    def clear(self):
        self.clears += 1
        return True


def zone(zone_id="z1", name="Desk", state="playing", title="Song", seek=10, length=200):
    return {
        "zone_id": zone_id, "display_name": name, "state": state, "seek_position": seek,
        "now_playing": {"three_line": {"line1": title, "line2": "Artist", "line3": "Album"},
                        "length": length, "seek_position": seek, "image_key": "img"},
    }


def make(zones, cfg=None, covers=None):
    clock = FakeClock()
    discord = FakeDiscord()
    tracker = Tracker(lambda: zones, discord, covers, cfg or Config(), clock=clock,
                      wall=lambda: 50_000 + clock.t)
    return tracker, discord, clock


def test_pushes_listening_activity_with_timestamps():
    tracker, discord, clock = make([zone(seek=10, length=200)])
    tracker.tick()
    (u,) = discord.updates
    assert u["details"] == "Song" and u["state"] == "Artist"
    assert u["end"] - u["start"] == 200
    assert u["start"] == int(50_000 + clock.t - 10)
    assert u["large_image"] is None and u["large_text"] is None  # no cover, no fallback


def test_no_repush_when_unchanged_until_heartbeat():
    zones = [zone()]
    tracker, discord, clock = make(zones)
    tracker.tick()
    for _ in range(5):
        clock.t += 1
        zones[0]["seek_position"] += 1  # normal playback keeps start constant
        tracker.tick()
    assert len(discord.updates) == 1
    clock.t += HEARTBEAT
    zones[0]["seek_position"] += HEARTBEAT
    tracker.tick()
    assert len(discord.updates) == 2


def test_seek_and_track_change_are_rate_limited():
    zones = [zone()]
    tracker, discord, clock = make(zones)
    tracker.tick()
    zones[0] = zone(title="Next", seek=0)
    clock.t += 1
    tracker.tick()
    assert len(discord.updates) == 1  # within MIN_PUSH_GAP
    clock.t += MIN_PUSH_GAP
    tracker.tick()
    assert discord.updates[-1]["details"] == "Next"


def test_clears_after_idle_grace():
    zones = [zone()]
    tracker, discord, clock = make(zones)
    tracker.tick()
    zones[0] = zone(state="paused")
    clock.t += 1
    tracker.tick()
    assert discord.clears == 0
    clock.t += IDLE_GRACE
    tracker.tick()
    assert discord.clears == 1 and not tracker.shown


def test_prefers_current_zone_and_respects_filter():
    zones = [zone("a", "Kitchen"), zone("b", "Desk")]
    cfg = Config()
    cfg.roon.zones = ["Desk"]
    tracker, discord, _ = make(zones, cfg)
    tracker.tick()
    assert tracker.zone_id == "b"


def test_repushes_after_discord_reconnect():
    tracker, discord, clock = make([zone()])
    tracker.tick()
    discord.connected = False
    clock.t += 1
    tracker.tick()
    discord.connected = True
    clock.t += MIN_PUSH_GAP
    tracker.tick()
    assert len(discord.updates) == 2


def test_cover_used_when_available():
    class Covers:
        def get(self, key):
            return "https://covers.example.com/x.jpg"

    tracker, discord, _ = make([zone()], covers=Covers())
    tracker.tick()
    assert discord.updates[0]["large_image"] == "https://covers.example.com/x.jpg"
    assert discord.updates[0]["large_text"] == "Album"


def test_clip():
    assert len(clip("a")) == 2
    assert clip("x" * 200).endswith("…") and len(clip("x" * 200)) == 128
