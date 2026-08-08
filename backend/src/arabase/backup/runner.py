"""Dump the database with ``pg_dump`` and upload it to object storage."""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.db import connection

from arabase.backup.config import BackupConfig

logger = logging.getLogger(__name__)

# -Fc is PostgreSQL's custom format: compressed, and restorable selectively
# with pg_restore, which plain SQL is not.
DUMP_FORMAT_ARGS = ["--format=custom", "--compress=9"]


class BackupError(Exception):
    """Raised when a backup cannot be produced or stored."""


@dataclass(frozen=True)
class BackupResult:
    key: str
    size_bytes: int
    duration_seconds: float
    pruned_keys: list[str]


def _pg_dump_path() -> str:
    """Resolve pg_dump to an absolute path, failing with a useful message."""

    path = shutil.which("pg_dump")
    if path is None:
        raise BackupError(
            "pg_dump is not on PATH. It ships with the postgresql-client "
            "package, which the all-in-one image installs in its base stage."
        )
    return path


def _pg_dump_major_version() -> int:
    try:
        # S603: argv is a resolved absolute path plus a constant flag.
        output = subprocess.run(  # noqa: S603
            [_pg_dump_path(), "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        raise BackupError(f"Could not determine the pg_dump version: {exc}") from exc

    match = re.search(r"(\d+)", output)
    if not match:
        raise BackupError(f"Could not parse the pg_dump version from {output!r}.")
    return int(match.group(1))


def _server_major_version() -> int:
    # Django exposes the server version as e.g. 150004 for 15.4.
    return connection.pg_version // 10000


def check_versions() -> tuple[int, int]:
    """Verify pg_dump is new enough for the server.

    pg_dump refuses outright to dump a server newer than itself, so this is
    checked before anything else rather than discovered halfway through a
    scheduled run.
    """

    client = _pg_dump_major_version()
    server = _server_major_version()
    if client < server:
        raise BackupError(
            f"pg_dump is version {client} but the server is version {server}. "
            f"pg_dump refuses to dump a newer server. Install "
            f"postgresql-client-{server} in the image (see "
            f"deploy/all-in-one/Dockerfile, POSTGRES_VERSION)."
        )
    return client, server


def _dump_argv(db: dict) -> list[str]:
    argv = [_pg_dump_path(), "--no-owner", "--no-privileges", *DUMP_FORMAT_ARGS]
    if db.get("HOST"):
        argv += [f"--host={db['HOST']}"]
    if db.get("PORT"):
        argv += [f"--port={db['PORT']}"]
    if db.get("USER"):
        argv += [f"--username={db['USER']}"]
    argv += [db["NAME"]]
    return argv


def _dump_to_file(path: str) -> int:
    """Run pg_dump into ``path``, returning the size written.

    The dump lands on disk before it is uploaded so that a pg_dump failure can
    never publish a truncated object: the exit code is checked first. The
    tradeoff is transient disk use equal to the compressed dump size, which is
    why the caller removes the file in a ``finally``.
    """

    db = settings.DATABASES["default"]
    env = os.environ.copy()
    if db.get("PASSWORD"):
        # Passed via the environment, never argv, so it stays out of `ps`.
        env["PGPASSWORD"] = db["PASSWORD"]

    with open(path, "wb") as handle:
        # S603: argv is built from Django's DATABASES setting, not from any
        # request input, and the password is passed through the environment.
        process = subprocess.run(  # noqa: S603
            _dump_argv(db),
            stdout=handle,
            stderr=subprocess.PIPE,
            env=env,
            timeout=int(os.getenv("JADAWEL_BACKUP_TIMEOUT_SECONDS", "3600")),
        )

    if process.returncode != 0:
        stderr = process.stderr.decode("utf-8", errors="replace").strip()
        raise BackupError(f"pg_dump exited with {process.returncode}: {stderr}")

    size = os.path.getsize(path)
    if size == 0:
        raise BackupError("pg_dump produced an empty file.")
    return size


def _client(config: BackupConfig):
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=config.endpoint_url,
        region_name=config.region,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
    )


def _upload(client, config: BackupConfig, path: str, key: str) -> None:
    extra = {"ACL": "private"}
    if config.sse:
        extra["ServerSideEncryption"] = config.sse
    with open(path, "rb") as handle:
        client.upload_fileobj(handle, config.bucket, key, ExtraArgs=extra)


def _prune(client, config: BackupConfig, now: datetime) -> list[str]:
    """Delete backups older than the retention window.

    Age comes from the object's own LastModified rather than its name, so a
    hand-uploaded or renamed object is still aged out correctly.
    """

    cutoff = now - timedelta(days=config.retention_days)
    pruned: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=config.bucket, Prefix=config.prefix):
        for obj in page.get("Contents", []):
            if obj["LastModified"] < cutoff:
                client.delete_object(Bucket=config.bucket, Key=obj["Key"])
                pruned.append(obj["Key"])
    return pruned


def run_backup(config: BackupConfig | None = None) -> BackupResult:
    """Dump the database, upload it, and prune expired backups."""

    config = config or BackupConfig.from_env()
    errors = config.validation_errors()
    if errors:
        raise BackupError("Backup is not configured: " + " ".join(errors))

    check_versions()

    now = datetime.now(timezone.utc)
    key = f"{config.prefix}jadawel-{now:%Y%m%dT%H%M%SZ}.dump"
    started = now

    handle, path = tempfile.mkstemp(prefix="jadawel-backup-", suffix=".dump")
    os.close(handle)
    try:
        size = _dump_to_file(path)
        client = _client(config)
        _upload(client, config, path, key)
        pruned = _prune(client, config, now)
    finally:
        try:
            os.remove(path)
        except OSError:
            logger.warning("Could not remove the temporary dump at %s.", path)

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    logger.info(
        "Database backup uploaded to %s (%s bytes) in %.1fs; pruned %s expired.",
        key,
        size,
        duration,
        len(pruned),
    )
    return BackupResult(
        key=key, size_bytes=size, duration_seconds=duration, pruned_keys=pruned
    )
