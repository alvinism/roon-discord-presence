"""Any S3-compatible bucket with a public URL: Cloudflare R2, AWS S3, Backblaze B2, MinIO…"""

import logging
import time

from ..config import ConfigError, S3Config, resolve_secret

log = logging.getLogger(__name__)


class S3Provider:
    name = "s3"

    def __init__(self, cfg: S3Config):
        try:
            import boto3
            from botocore.config import Config
        except ImportError as e:
            raise ConfigError(
                "covers.provider = \"s3\" needs boto3: "
                "uv tool install 'roon-discord-presence[s3]'"
            ) from e
        self.cfg = cfg
        self.base_url = cfg.public_base_url.rstrip("/")
        self.prefix = cfg.prefix.strip("/") + "/" if cfg.prefix.strip("/") else ""
        self.client = boto3.client(
            "s3",
            endpoint_url=cfg.endpoint,
            aws_access_key_id=cfg.access_key_id,
            aws_secret_access_key=resolve_secret(cfg.secret_access_key),
            region_name=cfg.region,
            config=Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 2}),
        )

    def publish(self, filename: str, data: bytes) -> str:
        key = self.prefix + filename
        if self._needs_upload(key):
            self.client.put_object(
                Bucket=self.cfg.bucket, Key=key, Body=data, ContentType="image/jpeg",
                CacheControl="public, max-age=2592000",
            )
            log.info("Uploaded cover %s (%d KB)", key, len(data) // 1024)
        return f"{self.base_url}/{key}"

    def _needs_upload(self, key: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            head = self.client.head_object(Bucket=self.cfg.bucket, Key=key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return True
            raise
        age = time.time() - head["LastModified"].timestamp()
        return age > self.cfg.reupload_after_days * 86400
