"""Environment-driven configuration for database backups.

These are read straight from the environment rather than added to
``jadawel/config/settings/base.py``: fork features are additive and a core
edit would have to be logged in ``PATCHES.md`` for no gain, since nothing in
core needs to read them.

The credentials are deliberately *separate* from the ``AWS_*`` variables that
configure user-file storage. Two reasons: the media bucket is public-read by
default, and a backup target should be writable by a key that cannot read or
delete anything a web request can reach.
"""

import os
from dataclasses import dataclass

# 23:00 UTC is 02:00 in Riyadh (UTC+3), the daily low point for this deployment.
DEFAULT_CRONTAB = "0 23 * * *"
DEFAULT_RETENTION_DAYS = 14
DEFAULT_PREFIX = "postgres/"


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, ""))
    except ValueError:
        return default


@dataclass(frozen=True)
class BackupConfig:
    """Resolved backup settings. Build with :meth:`from_env`."""

    enabled: bool
    bucket: str
    prefix: str
    endpoint_url: str | None
    region: str | None
    access_key_id: str | None
    secret_access_key: str | None
    retention_days: int
    crontab: str
    # Server-side encryption header. Empty disables it; not every
    # S3-compatible provider implements SSE, so it must be opt-in.
    sse: str | None

    @classmethod
    def from_env(cls) -> "BackupConfig":
        prefix = os.getenv("JADAWEL_BACKUP_S3_PREFIX", DEFAULT_PREFIX)
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        return cls(
            enabled=_env_flag("JADAWEL_BACKUP_ENABLED"),
            bucket=os.getenv("JADAWEL_BACKUP_S3_BUCKET", ""),
            prefix=prefix,
            endpoint_url=os.getenv("JADAWEL_BACKUP_S3_ENDPOINT_URL") or None,
            region=os.getenv("JADAWEL_BACKUP_S3_REGION") or None,
            access_key_id=os.getenv("JADAWEL_BACKUP_S3_ACCESS_KEY_ID") or None,
            secret_access_key=os.getenv("JADAWEL_BACKUP_S3_SECRET_ACCESS_KEY") or None,
            retention_days=_env_int(
                "JADAWEL_BACKUP_RETENTION_DAYS", DEFAULT_RETENTION_DAYS
            ),
            crontab=os.getenv("JADAWEL_BACKUP_CRONTAB", DEFAULT_CRONTAB),
            sse=os.getenv("JADAWEL_BACKUP_S3_SSE") or None,
        )

    def validation_errors(self) -> list[str]:
        """Return the reasons this config cannot be used, empty if usable."""

        errors = []
        if not self.bucket:
            errors.append("JADAWEL_BACKUP_S3_BUCKET is not set.")
        if not self.access_key_id:
            errors.append("JADAWEL_BACKUP_S3_ACCESS_KEY_ID is not set.")
        if not self.secret_access_key:
            errors.append("JADAWEL_BACKUP_S3_SECRET_ACCESS_KEY is not set.")
        if self.retention_days < 1:
            errors.append("JADAWEL_BACKUP_RETENTION_DAYS must be at least 1.")
        media_bucket = os.getenv("AWS_STORAGE_BUCKET_NAME", "")
        if media_bucket and media_bucket == self.bucket and not self.prefix:
            errors.append(
                "The backup bucket is the same as the user-file bucket and no "
                "prefix is set. User files are served public-read, so backups "
                "must at least be namespaced under their own prefix."
            )
        return errors
