from django.db.models.signals import post_migrate

from .base import *  # noqa: F403, F401
from .utils import setup_dev_e2e

DEBUG = True

# ArabaseConfig synchronously reconciles the same six-template catalog used in
# production. The former E2E-only receiver imported upstream defaults which the
# production receiver then correctly removed, leaving readiness checks stale.
JADAWEL_TRIGGER_SYNC_TEMPLATES_AFTER_MIGRATION = False

# Don't bother waiting for the non-existent license authority
LICENSE_AUTHORITY_CHECK_TIMEOUT_SECONDS = 0.001

post_migrate.connect(setup_dev_e2e, dispatch_uid="setup_dev_e2e")
