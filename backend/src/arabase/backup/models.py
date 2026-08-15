"""Persisted state for the backup feature: the schedule, and what has run.

Until now the schedule lived only in ``JADAWEL_BACKUP_CRONTAB`` and nothing
recorded a run at all. Both are needed by the admin page: an operator has to be
able to change the frequency without a redeploy, and — more importantly — has to
be able to see that backups are *still happening*. A backup that quietly stopped
running months ago looks exactly like one that is working, right up until the
day it is needed.
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone

FREQUENCY_HOURLY = "hourly"
FREQUENCY_DAILY = "daily"
FREQUENCY_WEEKLY = "weekly"
FREQUENCY_CHOICES = [
    (FREQUENCY_HOURLY, "Hourly"),
    (FREQUENCY_DAILY, "Daily"),
    (FREQUENCY_WEEKLY, "Weekly"),
]

# 23:00 UTC is 02:00 in Riyadh, the daily low point for this deployment. The
# weekly run keeps that hour and lands on Friday night into Saturday, the start
# of the Saudi weekend.
FREQUENCY_CRONTABS = {
    FREQUENCY_HOURLY: "0 * * * *",
    FREQUENCY_DAILY: "0 23 * * *",
    FREQUENCY_WEEKLY: "0 23 * * 5",
}

# How long after its due time a run may be missing before the page calls the
# backups unhealthy. Generous enough to absorb a slow dump or a restart.
FREQUENCY_GRACE = {
    FREQUENCY_HOURLY: timedelta(hours=2),
    FREQUENCY_DAILY: timedelta(days=1, hours=6),
    FREQUENCY_WEEKLY: timedelta(days=8),
}


class BackupSchedule(models.Model):
    """Singleton row holding the operator-chosen schedule.

    Kept in the database rather than in the environment because the admin page
    has to change it, and an environment variable cannot be changed without a
    redeploy. ``JADAWEL_BACKUP_ENABLED`` still gates the feature entirely — this
    row decides *how often* once it is switched on, not *whether*.
    """

    frequency = models.CharField(
        max_length=16,
        choices=FREQUENCY_CHOICES,
        default=FREQUENCY_DAILY,
        help_text="How often a backup is taken.",
    )
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "backup schedule"

    @classmethod
    def get_solo(cls) -> "BackupSchedule":
        """The one row, created on first read."""

        schedule, _ = cls.objects.get_or_create(pk=1)
        return schedule

    @property
    def crontab(self) -> str:
        return FREQUENCY_CRONTABS[self.frequency]

    @property
    def grace_period(self) -> timedelta:
        return FREQUENCY_GRACE[self.frequency]


class BackupRun(models.Model):
    """One attempt to take a backup, successful or not.

    Failures are recorded as rows too. That is the whole point: a run that
    failed writes no object to storage, so listing the bucket would show nothing
    and look indistinguishable from a run that never started.
    """

    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    TRIGGER_SCHEDULED = "scheduled"
    TRIGGER_MANUAL = "manual"
    TRIGGER_CHOICES = [
        (TRIGGER_SCHEDULED, "Scheduled"),
        (TRIGGER_MANUAL, "Manual"),
    ]

    started_on = models.DateTimeField(default=timezone.now, db_index=True)
    finished_on = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_RUNNING
    )
    trigger = models.CharField(
        max_length=16, choices=TRIGGER_CHOICES, default=TRIGGER_SCHEDULED
    )
    key = models.TextField(
        blank=True, default="", help_text="Object key of the database dump."
    )
    size_bytes = models.BigIntegerField(default=0)
    media_key = models.TextField(
        blank=True, default="", help_text="Object key of the user-file archive."
    )
    media_size_bytes = models.BigIntegerField(default=0)
    pruned_count = models.IntegerField(default=0)
    error = models.TextField(
        blank=True,
        default="",
        help_text="Why the run failed. Empty on a successful run.",
    )

    class Meta:
        ordering = ("-started_on", "-id")

    def __str__(self):
        return f"<BackupRun {self.started_on:%Y-%m-%dT%H:%M:%SZ} {self.status}>"

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_on is None:
            return None
        return (self.finished_on - self.started_on).total_seconds()

    def mark_succeeded(self, result) -> None:
        self.status = self.STATUS_SUCCESS
        self.finished_on = timezone.now()
        self.key = result.key
        self.size_bytes = result.size_bytes
        self.media_key = result.media_key or ""
        self.media_size_bytes = result.media_size_bytes
        self.pruned_count = len(result.pruned_keys)
        self.save()

    def mark_failed(self, exc: BaseException) -> None:
        self.status = self.STATUS_FAILED
        self.finished_on = timezone.now()
        # str() rather than the traceback: this is rendered in an admin page, and
        # the traceback is already in the logs and in Sentry.
        self.error = str(exc)[:2000]
        self.save()
