"""Cover art: fetch from Roon, publish through a provider, remember the public URL."""

from ..config import CoversConfig
from .base import CoverProvider
from .cache import CoverCache


def make_provider(cfg: CoversConfig) -> CoverProvider | None:
    if cfg.provider == "s3":
        from .s3 import S3Provider
        return S3Provider(cfg.s3)
    if cfg.provider == "command":
        from .command import CommandProvider
        return CommandProvider(cfg.command)
    return None


__all__ = ["CoverCache", "CoverProvider", "make_provider"]
