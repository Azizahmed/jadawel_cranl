"""Restore a backup into a *separate* database, never over the live one.

The restore offered from the admin page is deliberately non-destructive. A
button that overwrites the production database has no undo — the restore
destroys the very rows you would need to recover from a wrong choice — and the
one moment anyone reaches for it is a moment of panic. So this downloads the
dump, restores it into a target database the operator supplies, and stops. The
switch-over stays a human decision made with the restored copy in front of them.

`docs/BACKUP_RESTORE.md` describes the same procedure by hand; this runs it, and
uses the same `--no-owner --no-privileges` the dump was taken with, so it
restores under whatever role the target URL connects as.
"""

import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from urllib.parse import urlparse

from arabase.backup.config import BackupConfig
from arabase.backup.runner import BackupError, _client, client_binary

logger = logging.getLogger(__name__)

RESTORE_TIMEOUT_SECONDS = 3600


class RestoreError(Exception):
    """Raised when a restore cannot be completed."""


@dataclass(frozen=True)
class RestoreResult:
    key: str
    target: str
    """The target database, with any password stripped."""


def _pg_restore_path() -> str:
    # Resolved the same way as pg_dump, and for the same reason: /usr/bin is
    # pg_wrapper, which picks a major version from the embedded cluster rather
    # than from the dump being restored. A dump written by a newer pg_dump is
    # unreadable by an older pg_restore, so the two must agree — taking the
    # newest installed version in both places is what makes them agree.
    path = client_binary("pg_restore")
    if path is None:
        raise RestoreError(
            "pg_restore is not installed. It ships with the postgresql-client "
            "package, which the all-in-one image installs in its base stage "
            "at the version in POSTGRES_CLIENT_VERSION."
        )
    return path


def redact(database_url: str) -> str:
    """A connection string safe to show in an API response or a log line."""

    return re.sub(r"://([^:/@]+):[^@]*@", r"://\1:***@", database_url)


def validate_target(database_url: str, config: BackupConfig | None = None) -> None:
    """Refuse anything that is not a plausible, non-live Postgres target.

    The live database is rejected by comparing against the running connection.
    That check is the difference between this being a rehearsal tool and being
    an undoable production wipe with extra steps.
    """

    from django.conf import settings

    parsed = urlparse(database_url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise RestoreError("The target must be a postgresql:// connection string.")
    if not parsed.hostname or not (parsed.path or "").strip("/"):
        raise RestoreError("The target must include a host and a database name.")

    live = settings.DATABASES["default"]
    target_name = parsed.path.strip("/")
    same_host = parsed.hostname == live.get("HOST")
    same_name = target_name == live.get("NAME")
    if same_host and same_name:
        raise RestoreError(
            "That is the live database. Restore into a separate database and "
            "switch over once you have verified it."
        )


def restore_backup(key: str, target_database_url: str) -> RestoreResult:
    """Download ``key`` and restore it into ``target_database_url``."""

    config = BackupConfig.from_env()
    errors = config.validation_errors()
    if errors:
        raise RestoreError("Backup is not configured: " + " ".join(errors))

    validate_target(target_database_url, config)

    if not key.startswith(config.prefix):
        raise RestoreError(
            f"{key!r} is not under the configured backup prefix {config.prefix!r}."
        )

    handle, path = tempfile.mkstemp(prefix="jadawel-restore-", suffix=".dump")
    os.close(handle)
    try:
        client = _client(config)
        try:
            client.download_file(config.bucket, key, path)
        except Exception as exc:
            raise RestoreError(f"Could not download {key}: {exc}") from exc

        env = os.environ.copy()
        argv = [
            _pg_restore_path(),
            f"--dbname={target_database_url}",
            "--no-owner",
            "--no-privileges",
            # Repeatable: restoring twice into the same target is a normal thing
            # to do while rehearsing.
            "--clean",
            "--if-exists",
            path,
        ]
        try:
            # S603: argv is a resolved absolute path plus constant flags; the
            # only variable is the target URL, which validate_target has checked
            # and which is passed as a single argument, not through a shell.
            process = subprocess.run(  # noqa: S603
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=RESTORE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise RestoreError(
                f"pg_restore did not finish within {RESTORE_TIMEOUT_SECONDS}s."
            ) from exc
        except OSError as exc:
            raise RestoreError(f"Could not run pg_restore: {exc}") from exc

        if process.returncode != 0:
            stderr = process.stderr.decode("utf-8", errors="replace").strip()
            # pg_restore exits non-zero for warnings too, so the message matters
            # more than the code when this reaches an operator.
            raise RestoreError(
                f"pg_restore exited with {process.returncode}: {stderr[:2000]}"
            )
    except BackupError as exc:
        raise RestoreError(str(exc)) from exc
    finally:
        try:
            os.remove(path)
        except OSError:
            logger.warning("Could not remove the temporary dump at %s.", path)

    redacted = redact(target_database_url)
    logger.info("Restored %s into %s.", key, redacted)
    return RestoreResult(key=key, target=redacted)
