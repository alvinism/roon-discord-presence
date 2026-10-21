"""Minimal Roon extension client: register, follow zones, and provide ping + status services."""

import logging
import threading
from collections.abc import Callable
from pathlib import Path

import websocket

from . import moo

log = logging.getLogger(__name__)

REGISTRY = "com.roonlabs.registry:1"
TRANSPORT = "com.roonlabs.transport:2"
PING = "com.roonlabs.ping:1"
STATUS = "com.roonlabs.status:1"

RETRY_MIN, RETRY_MAX = 2.0, 30.0  # reconnect backoff (s)


class RoonClient:
    """Keeps a live copy of Roon's zones. All network work happens on a background thread."""

    def __init__(self, host: str, port: int, appinfo: dict, token_file: Path):
        self.host, self.port = host, port
        self.appinfo = appinfo
        self.token_file = token_file
        self.core_name: str | None = None
        self.connected = False  # websocket open
        self.paired = False     # registered and authorised by the user in Roon

        self._lock = threading.Lock()
        self._zones: dict[str, dict] = {}
        self._handlers: dict[int, Callable[[moo.Message], None]] = {}
        self._next_id = 0
        self._ws: websocket.WebSocketApp | None = None
        self._status = {"message": "Starting…", "is_error": False}
        self._status_subs: dict[str, int] = {}  # subscription_key -> request id
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="roon", daemon=True)

    # public API -----------------------------------------------------------------------------

    @property
    def state(self) -> str:
        """offline | approve | ok"""
        if not self.connected:
            return "offline"
        return "ok" if self.paired else "approve"

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._ws:
            self._ws.close()
        self._thread.join(timeout=5)

    def zones(self) -> list[dict]:
        with self._lock:
            return list(self._zones.values())

    def image_url(self, image_key: str, size: int) -> str:
        return (f"http://{self.host}:{self.port}/api/image/{image_key}"
                f"?scale=fit&width={size}&height={size}&format=image/jpeg")

    def set_status(self, message: str, is_error: bool = False):
        """Status line shown under the extension in Roon → Settings → Extensions."""
        status = {"message": message, "is_error": is_error}
        with self._lock:
            if status == self._status:
                return
            self._status = status
            subs = list(self._status_subs.values())
        for rid in subs:
            self._send("CONTINUE", "Changed", rid, status)

    # connection -----------------------------------------------------------------------------

    def _run(self):
        delay = RETRY_MIN
        url = f"ws://{self.host}:{self.port}/api"
        while not self._stop.is_set():
            self._ws = websocket.WebSocketApp(
                url, on_open=self._on_open, on_message=self._on_message,
                on_error=self._on_error, on_close=self._on_close,
            )
            self._ws.run_forever(ping_interval=10, ping_timeout=5)
            was_paired = self.paired
            self._reset()
            if self._stop.is_set():
                break
            if was_paired:
                log.warning("Lost connection to Roon, reconnecting")
                delay = RETRY_MIN
            self._stop.wait(delay)
            delay = min(delay * 2, RETRY_MAX)

    def _reset(self):
        self.connected = self.paired = False
        with self._lock:
            self._zones.clear()
            self._handlers.clear()
            self._status_subs.clear()

    def _on_open(self, _ws):
        self.connected = True
        log.info("Connected to Roon at %s:%s", self.host, self.port)
        info = dict(self.appinfo, required_services=[TRANSPORT], optional_services=[],
                    provided_services=[PING, STATUS])
        token = self._load_token()
        if token:
            info["token"] = token
        else:
            log.info("Waiting for approval: enable “%s” in Roon → Settings → Extensions",
                     self.appinfo["display_name"])
        self._request(f"{REGISTRY}/register", info, self._on_registered)

    def _on_error(self, _ws, error):
        log.debug("Roon socket error: %s", error)

    def _on_close(self, _ws, *_):
        self.connected = False

    def _on_message(self, _ws, data):
        try:
            msg = moo.decode(data)
        except (moo.MooError, ValueError) as e:
            log.warning("Ignoring malformed message from Roon: %s", e)
            return
        if msg.verb == "REQUEST":
            self._serve(msg)
            return
        with self._lock:
            handler = self._handlers.get(msg.request_id)
            if msg.verb == "COMPLETE":
                self._handlers.pop(msg.request_id, None)
        if handler:
            try:
                handler(msg)
            except Exception:
                log.exception("Error handling %s %s", msg.verb, msg.name)

    def _send(self, verb, name, request_id, body=None):
        ws = self._ws
        if not (ws and self.connected):
            return
        try:
            ws.send(moo.encode(verb, name, request_id, body), opcode=websocket.ABNF.OPCODE_BINARY)
        except websocket.WebSocketException as e:
            log.debug("Send failed: %s", e)

    def _request(self, name, body, handler):
        with self._lock:
            rid = self._next_id
            self._next_id += 1
            self._handlers[rid] = handler
        self._send("REQUEST", name, rid, body)

    # services we provide --------------------------------------------------------------------

    def _serve(self, msg: moo.Message):
        service, _, method = msg.name.rpartition("/")
        rid = msg.request_id
        if service == PING and method == "ping":
            self._send("COMPLETE", "Success", rid)
        elif service == STATUS and method == "get_status":
            self._send("COMPLETE", "Success", rid, self._status)
        elif service == STATUS and method == "subscribe_status":
            key = str((msg.body or {}).get("subscription_key"))
            with self._lock:
                self._status_subs[key] = rid
            self._send("CONTINUE", "Subscribed", rid, self._status)
        elif service == STATUS and method == "unsubscribe_status":
            key = str((msg.body or {}).get("subscription_key"))
            with self._lock:
                self._status_subs.pop(key, None)
            self._send("COMPLETE", "Unsubscribed", rid)
        else:
            self._send("COMPLETE", "InvalidRequest", rid, {"error": f"unknown request {msg.name}"})

    # registration and zones -----------------------------------------------------------------

    def _on_registered(self, msg: moo.Message):
        if msg.name != "Registered":
            log.warning("Roon registration failed: %s %s", msg.name, msg.body)
            return
        body = msg.body or {}
        self.core_name = body.get("display_name")
        if body.get("token") and body["token"] != self._load_token():
            self._save_token(body["token"])
        self.paired = True
        log.info("Paired with Roon Core “%s”", self.core_name)
        self._request(f"{TRANSPORT}/subscribe_zones", {"subscription_key": 0}, self._on_zones)

    def _on_zones(self, msg: moo.Message):
        body = msg.body or {}
        with self._lock:
            if msg.name == "Subscribed":
                self._zones = {z["zone_id"]: z for z in body.get("zones", [])}
                return
            if msg.name != "Changed":
                return
            for zone_id in body.get("zones_removed", []):
                self._zones.pop(zone_id, None)
            for key in ("zones_added", "zones_changed"):
                for zone in body.get(key, []):
                    self._zones[zone["zone_id"]] = zone
            for seek in body.get("zones_seek_changed", []):
                zone = self._zones.get(seek["zone_id"])
                if zone is None:
                    continue
                zone["seek_position"] = seek.get("seek_position")
                zone["queue_time_remaining"] = seek.get("queue_time_remaining")
                if zone.get("now_playing") and "seek_position" in seek:
                    zone["now_playing"]["seek_position"] = seek["seek_position"]

    def _load_token(self) -> str | None:
        try:
            return self.token_file.read_text().strip() or None
        except FileNotFoundError:
            return None

    def _save_token(self, token: str):
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(token)
        self.token_file.chmod(0o600)
