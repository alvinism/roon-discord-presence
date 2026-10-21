"""Discord Rich Presence over the local IPC socket, with self-healing reconnects."""

import logging
import time

from pypresence import Presence

log = logging.getLogger(__name__)

RETRY = 15.0  # wait between connection attempts while Discord is unreachable (s)


class Discord:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.rpc = Presence(client_id)
        self.connected = False
        self._next_attempt = 0.0

    def ensure(self) -> bool:
        """Connect if needed (rate limited). Returns whether we are connected."""
        if self.connected:
            return True
        if time.monotonic() < self._next_attempt:
            return False
        try:
            self.rpc.connect()
            self.connected = True
            log.info("Connected to Discord")
        except Exception as e:
            log.debug("Discord not available: %s", e)
            self._next_attempt = time.monotonic() + RETRY
        return self.connected

    def update(self, **kwargs) -> bool:
        return self._call(self.rpc.update, **kwargs)

    def clear(self) -> bool:
        return self._call(self.rpc.clear)

    def close(self):
        if self.connected:
            try:
                self.rpc.clear()
                self.rpc.close()
            except Exception:
                pass
            self.connected = False

    def _call(self, fn, **kwargs) -> bool:
        # Discord drops idle IPC pipes when it reloads (e.g. after an in-app update) without
        # telling us, so on failure reconnect and retry once right away; back off only if
        # Discord is really unreachable.
        for attempt in (1, 2):
            if not self.ensure():
                return False
            try:
                fn(**kwargs)
                return True
            except Exception as e:
                log.warning("Discord call failed (%s), reconnecting", e)
                self._reset()
                self._next_attempt = 0.0 if attempt == 1 else time.monotonic() + RETRY
        return False

    def _reset(self):
        self.connected = False
        try:
            self.rpc.close()
        except Exception:
            pass
        if not self.rpc.loop.is_closed():  # close() skips this when the pipe is already dead
            self.rpc.loop.close()
        self.rpc = Presence(self.client_id)
