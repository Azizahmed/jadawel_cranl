"""Celery tasks for the Jadawel fork.

Autodiscovered by ``jadawel.config.celery``: ``arabase`` is an installed app,
so this module needs no registration in ``ArabaseConfig.ready()``.
"""

import logging

from arabase.backup.config import BackupConfig
from arabase.backup.runner import BackupError, run_backup
from jadawel.config.celery import app
from jadawel.config.settings.utils import get_crontab_from_env

logger = logging.getLogger(__name__)


@app.task(
    name="arabase.tasks.backup_database",
    queue="export",
    # The deployment runs one worker at concurrency 1, so a dump occupies the
    # only slot for its duration. The soft limit lets a stuck pg_dump be
    # interrupted rather than blocking exports and imports indefinitely.
    soft_time_limit=3600,
    time_limit=3900,
)
def backup_database():
    config = BackupConfig.from_env()
    if not config.enabled:
        logger.debug("Skipping the database backup: JADAWEL_BACKUP_ENABLED is not set.")
        return

    try:
        result = run_backup(config)
    except BackupError:
        # Logged with the traceback so it reaches Sentry once a DSN is set;
        # re-raised so the task is recorded as failed rather than silently
        # succeeding, which is the failure mode that makes a backup useless.
        logger.exception("The scheduled database backup failed.")
        raise

    return {"key": result.key, "size_bytes": result.size_bytes}


# noinspection PyUnusedLocal
@app.on_after_finalize.connect
def setup_periodic_backup_tasks(sender, **kwargs):
    config = BackupConfig.from_env()
    if not config.enabled:
        return
    sender.add_periodic_task(
        get_crontab_from_env("JADAWEL_BACKUP_CRONTAB", config.crontab),
        backup_database.s(),
    )
