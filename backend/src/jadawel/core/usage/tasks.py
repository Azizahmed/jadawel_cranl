from datetime import timedelta

from django.conf import settings

from celery_singleton import Singleton

from jadawel.config.celery import app
from jadawel.core.handler import CoreHandler

CALCULATE_STORAGE_MINUTES = 30
CALCULATE_STORAGE_TIME_LIMIT = 60 * CALCULATE_STORAGE_MINUTES


@app.task(
    name="jadawel.core.usage.tasks.run_calculate_storage",
    base=Singleton,
    queue=settings.JADAWEL_GROUP_STORAGE_USAGE_QUEUE,
    raise_on_duplicate=False,
    soft_time_limit=CALCULATE_STORAGE_TIME_LIMIT,
    time_limit=CALCULATE_STORAGE_TIME_LIMIT,
    lock_expiry=CALCULATE_STORAGE_TIME_LIMIT,
)
def run_calculate_storage():
    """
    Runs the calculate storage job to keep track of how many mb of memory has been used
    via files by a group
    """

    from jadawel.core.usage.handler import UsageHandler

    if CoreHandler().get_settings().track_workspace_usage:
        UsageHandler.calculate_storage_usage()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        timedelta(minutes=CALCULATE_STORAGE_MINUTES),
        run_calculate_storage.s(),
    )
