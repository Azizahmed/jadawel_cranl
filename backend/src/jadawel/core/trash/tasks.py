from datetime import timedelta

from django.conf import settings

from jadawel.config.celery import app


# noinspection PyUnusedLocal
@app.task(
    name="baserow.core.trash.tasks.mark_old_trash_for_permanent_deletion",
    bind=True,
)
def mark_old_trash_for_permanent_deletion(self):
    from jadawel.core.trash.handler import TrashHandler

    TrashHandler.mark_old_trash_for_permanent_deletion()


# noinspection PyUnusedLocal
@app.task(
    name="baserow.core.trash.tasks.permanently_delete_marked_trash",
    bind=True,
)
def permanently_delete_marked_trash(self):
    from jadawel.core.trash.handler import TrashHandler

    TrashHandler.permanently_delete_marked_trash()


# noinspection PyUnusedLocal
@app.on_after_finalize.connect
def setup_period_trash_tasks(sender, **kwargs):
    sender.add_periodic_task(
        timedelta(minutes=settings.OLD_TRASH_CLEANUP_CHECK_INTERVAL_MINUTES),
        mark_old_trash_for_permanent_deletion.s(),
    )
    sender.add_periodic_task(
        timedelta(minutes=settings.OLD_TRASH_CLEANUP_CHECK_INTERVAL_MINUTES),
        permanently_delete_marked_trash.s(),
    )
