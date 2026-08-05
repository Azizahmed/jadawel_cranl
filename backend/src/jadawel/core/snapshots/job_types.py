from jadawel.api.errors import (
    ERROR_MAX_LOCKS_PER_TRANSACTION_EXCEEDED,
    ERROR_USER_NOT_IN_GROUP,
)
from jadawel.api.snapshots.errors import ERROR_SNAPSHOT_DOES_NOT_EXIST
from jadawel.contrib.database.exceptions import (
    DatabaseSnapshotMaxLocksExceededException,
)
from jadawel.core.action.registries import action_type_registry
from jadawel.core.exceptions import UserNotInWorkspace
from jadawel.core.jobs.registries import JobType
from jadawel.core.registries import application_type_registry
from jadawel.core.service import CoreService
from jadawel.core.snapshots.exceptions import SnapshotDoesNotExist

from .models import CreateSnapshotJob, RestoreSnapshotJob


class CreateSnapshotJobType(JobType):
    type = "create_snapshot"
    model_class = CreateSnapshotJob
    max_count = 1

    api_exceptions_map = {
        UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
        SnapshotDoesNotExist: ERROR_SNAPSHOT_DOES_NOT_EXIST,
        DatabaseSnapshotMaxLocksExceededException: ERROR_MAX_LOCKS_PER_TRANSACTION_EXCEEDED,
    }

    job_exceptions_map = {
        DatabaseSnapshotMaxLocksExceededException: DatabaseSnapshotMaxLocksExceededException.message
    }

    serializer_field_names = ["snapshot"]

    @property
    def serializer_field_overrides(self):
        from jadawel.api.snapshots.serializers import SnapshotSerializer

        return {
            "snapshot": SnapshotSerializer(),
        }

    def transaction_atomic_context(self, job: CreateSnapshotJob):
        application = CoreService().get_application(
            job.user, job.snapshot.snapshot_from_application.id
        )
        application_type = application_type_registry.get_by_model(application)
        return application_type.export_safe_transaction_context(application)

    def run(self, job: CreateSnapshotJob, progress):
        from .actions import CreateSnapshotActionType

        action_type_registry.get(CreateSnapshotActionType.type).do(
            job.user, job.snapshot, progress
        )

    def before_delete(self, job):
        # Delete the dangling snapshot if it didn't finish correctly but the snapshot is
        # still there.
        if not job.finished and job.snapshot_id is not None:
            job.snapshot.delete()


class RestoreSnapshotJobType(JobType):
    type = "restore_snapshot"
    model_class = RestoreSnapshotJob
    max_count = 1

    api_exceptions_map = {
        UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
        SnapshotDoesNotExist: ERROR_SNAPSHOT_DOES_NOT_EXIST,
    }

    serializer_field_names = ["snapshot"]

    @property
    def serializer_field_overrides(self):
        from jadawel.api.snapshots.serializers import SnapshotSerializer

        return {
            "snapshot": SnapshotSerializer(),
        }

    def run(self, job: RestoreSnapshotJob, progress):
        from .actions import RestoreSnapshotActionType

        action_type_registry.get(RestoreSnapshotActionType.type).do(
            job.user, job.snapshot, progress
        )
