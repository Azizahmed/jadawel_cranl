"""Keep the hosted Jadawel template picker limited to the local catalog."""

import logging
import re

from django.db import transaction

from jadawel.core.handler import CoreHandler
from jadawel.core.models import Template, TemplateCategory
from jadawel.core.trash.handler import TrashHandler

logger = logging.getLogger(__name__)

ARABIC_TEMPLATE_CATEGORY = "قوالب عربية"
ENGLISH_TEMPLATE_CATEGORY = "English Templates"

LOCAL_TEMPLATE_CATALOG = {
    "arabic-performance-review": ARABIC_TEMPLATE_CATEGORY,
    "arabic-project-management": ARABIC_TEMPLATE_CATEGORY,
    "saudi-budget-consolidation": ARABIC_TEMPLATE_CATEGORY,
    "performance-reviews": ENGLISH_TEMPLATE_CATEGORY,
    "project-management-en": ENGLISH_TEMPLATE_CATEGORY,
    "saudi-budget-consolidation-en": ENGLISH_TEMPLATE_CATEGORY,
}

LOCAL_TEMPLATE_PATTERN = "^(?:{})$".format(
    "|".join(re.escape(slug) for slug in LOCAL_TEMPLATE_CATALOG)
)


class LocalTemplateCatalogIncomplete(Exception):
    """Raised before pruning when a required local template failed to import."""


def local_template_catalog_is_current() -> bool:
    """Return whether the database contains exactly the approved local catalog."""

    templates = {}
    for slug, category_name in Template.objects.values_list("slug", "categories__name"):
        templates.setdefault(slug, set())
        if category_name is not None:
            templates[slug].add(category_name)
    expected = {
        slug: {category_name} for slug, category_name in LOCAL_TEMPLATE_CATALOG.items()
    }
    category_names = set(TemplateCategory.objects.values_list("name", flat=True))
    expected_category_names = {
        ARABIC_TEMPLATE_CATEGORY,
        ENGLISH_TEMPLATE_CATEGORY,
    }
    return templates == expected and category_names == expected_category_names


def reconcile_local_template_catalog() -> dict:
    """Import the six bundled templates and remove obsolete catalog previews.

    This is intentionally fail-safe: imports happen first, and no old template is
    removed unless all six approved slugs exist afterward. The operation is
    idempotent, so normal restarts only perform the inexpensive state check.
    """

    if local_template_catalog_is_current():
        return {"changed": False, "removed": 0, "templates": 6}

    CoreHandler().sync_templates(pattern=LOCAL_TEMPLATE_PATTERN)

    installed_slugs = set(Template.objects.values_list("slug", flat=True))
    missing_slugs = set(LOCAL_TEMPLATE_CATALOG) - installed_slugs
    if missing_slugs:
        missing = ", ".join(sorted(missing_slugs))
        raise LocalTemplateCatalogIncomplete(
            f"Refusing to prune templates because these local templates are "
            f"missing: {missing}"
        )

    categories = {
        name: TemplateCategory.objects.get_or_create(name=name)[0]
        for name in (ARABIC_TEMPLATE_CATEGORY, ENGLISH_TEMPLATE_CATEGORY)
    }

    with transaction.atomic():
        for slug, category_name in LOCAL_TEMPLATE_CATALOG.items():
            Template.objects.get(slug=slug).categories.set([categories[category_name]])

    obsolete_templates = list(
        Template.objects.exclude(slug__in=LOCAL_TEMPLATE_CATALOG).select_related(
            "workspace"
        )
    )
    for template in obsolete_templates:
        with transaction.atomic():
            if template.workspace is not None:
                TrashHandler.permanently_delete(template.workspace)
            template.delete()

    TemplateCategory.objects.exclude(
        name__in=(ARABIC_TEMPLATE_CATEGORY, ENGLISH_TEMPLATE_CATEGORY)
    ).delete()

    logger.info(
        "Reconciled the local template catalog: kept %s templates and removed %s.",
        len(LOCAL_TEMPLATE_CATALOG),
        len(obsolete_templates),
    )
    return {
        "changed": True,
        "removed": len(obsolete_templates),
        "templates": len(LOCAL_TEMPLATE_CATALOG),
    }


def reconcile_local_template_catalog_after_migrate(sender, **kwargs):
    """Reconcile synchronously so startup cannot expose a stale catalog.

    CranL runs one combined Celery worker. Queueing this behind core's broad
    template sync left the old 157-template catalog live with no dependable
    completion signal. Running here makes a successful migration/startup the
    signal that the authoritative local catalog is ready.
    """

    from django.conf import settings

    if settings.TESTS:
        return

    result = reconcile_local_template_catalog()
    logger.info("Local template catalog is ready after migrations: %s", result)
    return result
