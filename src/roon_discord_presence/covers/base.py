from typing import Protocol


class CoverProvider(Protocol):
    """Makes a cover image publicly reachable so Discord can fetch it."""

    name: str

    def publish(self, filename: str, data: bytes) -> str:
        """Ensure `data` is served publicly as `filename` and return its https URL.

        Must be idempotent: it is called again periodically for covers already published, so
        providers can refresh objects that a storage lifecycle rule would otherwise expire.
        """
        ...
