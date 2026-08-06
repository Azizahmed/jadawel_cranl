from django.db import transaction

from jadawel.config.celery import app
from jadawel.core.services.registries import service_type_registry


@app.task(
    name="jadawel.contrib.integrations.tasks.call_periodic_services_that_are_due",
    bind=True,
    queue="export",
)
def call_periodic_services_that_are_due(self):
    from jadawel.contrib.integrations.core.service_types import CorePeriodicServiceType

    with transaction.atomic():
        service_type_registry.get(
            CorePeriodicServiceType.type
        ).call_periodic_services_that_are_due()
