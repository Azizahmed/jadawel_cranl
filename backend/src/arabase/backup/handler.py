"""Recording backup runs, judging their health, and republishing the schedule."""

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.utils import timezone

from celery.schedules import crontab as celery_crontab

from arabase.backup.config import BackupConfig
from arabase.backup.models import BackupRun, BackupSchedule

logger = logging.getLogger(__name__)

HEALTH_OK = "ok"
HEALTH_NEVER_RUN = "never_run"
HEALTH_LAST_FAILED = "last_failed"
HEALTH_OVERDUE = "overdue"
HEALTH_DISABLED = "disabled"
HEALTH_MISCONFIGURED = "misconfigured"


@dataclass(frozen=True)
class BackupHealth:
    """What the admin page shows at the top of the section."""

    status: str
    last_success_on: Optional[datetime]
    last_run: Optional[BackupRun]
    next_run_on: Optional[datetime]
    configuration_errors: list[str]

    @property
    def healthy(self) -> bool:
        return self.status == HEALTH_OK


def parse_crontab(expression: str) -> celery_crontab:
    """A celery crontab from a five-field expression.

    Celery's constructor takes its arguments in a different order to the crontab
    spec, which is a reliable source of quiet mistakes.
    """

    minute, hour, day_of_month, month_of_year, day_of_week = expression.split(" ")
    return celery_crontab(minute, hour, day_of_week, day_of_month, month_of_year)


def next_run_on(schedule: BackupSchedule, now: Optional[datetime] = None):
    """When the next run is due, or None if the schedule cannot be read."""

    now = now or timezone.now()
    try:
        remaining = parse_crontab(schedule.crontab).remaining_estimate(now)
    except (ValueError, AttributeError):
        return None
    return now + remaining


@contextmanager
def record_run(trigger: str = BackupRun.TRIGGER_SCHEDULED):
    """Wrap a backup attempt so that the outcome is recorded either way.

    A failed run writes no object to storage, so without a row here a failure is
    indistinguishable from a run that never happened — which is precisely the
    state a backup system must never be able to reach silently.
    """

    run = BackupRun.objects.create(trigger=trigger)
    try:
        yield run
    except BaseException as exc:
        run.mark_failed(exc)
        raise


def get_health(now: Optional[datetime] = None) -> BackupHealth:
    """Judge whether backups can be relied on right now."""

    now = now or timezone.now()
    config = BackupConfig.from_env()
    schedule = BackupSchedule.get_solo()

    last_run = BackupRun.objects.first()
    last_success = BackupRun.objects.filter(status=BackupRun.STATUS_SUCCESS).first()
    last_success_on = last_success.started_on if last_success else None
    upcoming = next_run_on(schedule, now) if config.enabled else None

    def health(status, errors=None):
        return BackupHealth(
            status=status,
            last_success_on=last_success_on,
            last_run=last_run,
            next_run_on=upcoming,
            configuration_errors=errors or [],
        )

    if not config.enabled:
        return health(HEALTH_DISABLED)

    # Enabled but unusable is its own state: the task is scheduled and will fail
    # every time it fires, which is worse than being switched off.
    errors = config.validation_errors()
    if errors:
        return health(HEALTH_MISCONFIGURED, errors)

    if last_success_on is None:
        return health(HEALTH_NEVER_RUN)

    # Overdue is checked before the last run's status. A backup that is days late
    # is the more urgent fact even if the most recent attempt happened to fail.
    if now - last_success_on > schedule.grace_period:
        return health(HEALTH_OVERDUE)

    if last_run is not None and last_run.status == BackupRun.STATUS_FAILED:
        return health(HEALTH_LAST_FAILED)

    return health(HEALTH_OK)


def republish_schedule() -> None:
    """Push the stored frequency into RedBeat so it applies without a redeploy.

    The periodic task is registered once at worker start, so changing the row
    alone would leave beat firing on the old frequency until the next deploy —
    which is exactly the kind of gap that makes an admin toggle untrustworthy.
    """

    from arabase.tasks import BACKUP_TASK_NAME, backup_database

    config = BackupConfig.from_env()
    schedule = BackupSchedule.get_solo()

    try:
        from redbeat import RedBeatSchedulerEntry

        from jadawel.config.celery import app

        if not config.enabled:
            try:
                RedBeatSchedulerEntry.from_key(
                    f"redbeat:{BACKUP_TASK_NAME}", app=app
                ).delete()
            except KeyError:
                pass
            return

        entry = RedBeatSchedulerEntry(
            BACKUP_TASK_NAME,
            backup_database.name,
            parse_crontab(schedule.crontab),
            app=app,
        )
        entry.save()
    except Exception:
        # Beat re-reads the schedule at start, so the worst case is that the new
        # frequency applies on the next restart rather than immediately. Not
        # worth failing the operator's save over.
        logger.exception(
            "Could not republish the backup schedule to RedBeat; it will apply "
            "on the next worker restart."
        )
