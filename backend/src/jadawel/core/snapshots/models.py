from django.db import models

from jadawel.core.jobs.mixins import JobWithUserIpAddress
from jadawel.core.jobs.models import Job
from jadawel.core.models import Snapshot


class CreateSnapshotJob(JobWithUserIpAddress, Job):
    snapshot: Snapshot = models.ForeignKey(
        Snapshot, null=True, on_delete=models.SET_NULL
    )


class RestoreSnapshotJob(JobWithUserIpAddress, Job):
    snapshot: Snapshot = models.ForeignKey(
        Snapshot, null=True, on_delete=models.SET_NULL
    )
