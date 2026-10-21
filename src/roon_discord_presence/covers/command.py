"""Bring your own uploader: run a command with the JPEG on stdin, read the URL from stdout."""

import subprocess

from ..config import CommandConfig


class CommandProvider:
    name = "command"

    def __init__(self, cfg: CommandConfig):
        self.cfg = cfg

    def publish(self, filename: str, data: bytes) -> str:
        result = subprocess.run(
            [*self.cfg.command, filename], input=data, capture_output=True,
            timeout=self.cfg.timeout,
        )
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace").strip()
            raise RuntimeError(f"cover command exited {result.returncode}: {err[:300]}")
        lines = [ln.strip() for ln in result.stdout.decode(errors="replace").splitlines()]
        url = next((ln for ln in reversed(lines) if ln), "")
        if not url.startswith("https://"):
            raise RuntimeError(f"cover command must print an https URL, got {url[:200]!r}")
        return url
