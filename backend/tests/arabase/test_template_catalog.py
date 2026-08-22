from unittest.mock import patch

from django.test import override_settings

import pytest

from arabase.template_catalog import (
    ARABIC_TEMPLATE_CATEGORY,
    ENGLISH_TEMPLATE_CATEGORY,
    LOCAL_TEMPLATE_CATALOG,
    LocalTemplateCatalogIncomplete,
    local_template_catalog_is_current,
    reconcile_local_template_catalog,
    schedule_local_template_catalog_reconciliation,
)
from jadawel.core.models import Template, TemplateCategory, Workspace


def create_template(data_fixture, slug, category):
    return data_fixture.create_template(slug=slug, category=category)


@pytest.mark.django_db
@patch("arabase.template_catalog.CoreHandler.sync_templates")
def test_reconcile_local_template_catalog_imports_then_prunes(
    sync_templates, data_fixture
):
    old_category = data_fixture.create_template_category(name="Old templates")
    old_template = create_template(data_fixture, "obsolete-template", old_category)
    old_workspace_id = old_template.workspace_id

    def install_missing_templates(*args, **kwargs):
        for slug in LOCAL_TEMPLATE_CATALOG:
            if not Template.objects.filter(slug=slug).exists():
                create_template(data_fixture, slug, old_category)

    sync_templates.side_effect = install_missing_templates

    result = reconcile_local_template_catalog()

    assert result == {"changed": True, "removed": 1, "templates": 6}
    assert set(Template.objects.values_list("slug", flat=True)) == set(
        LOCAL_TEMPLATE_CATALOG
    )
    assert not Workspace.objects.filter(id=old_workspace_id).exists()
    assert set(TemplateCategory.objects.values_list("name", flat=True)) == {
        ARABIC_TEMPLATE_CATEGORY,
        ENGLISH_TEMPLATE_CATEGORY,
    }
    for slug, expected_category in LOCAL_TEMPLATE_CATALOG.items():
        assert set(
            Template.objects.get(slug=slug).categories.values_list("name", flat=True)
        ) == {expected_category}
    assert local_template_catalog_is_current()


@pytest.mark.django_db
@patch("arabase.template_catalog.CoreHandler.sync_templates")
def test_reconcile_local_template_catalog_does_not_prune_when_import_is_incomplete(
    sync_templates, data_fixture
):
    old_template = data_fixture.create_template(slug="obsolete-template")

    with pytest.raises(LocalTemplateCatalogIncomplete):
        reconcile_local_template_catalog()

    sync_templates.assert_called_once()
    assert Template.objects.filter(id=old_template.id).exists()


@pytest.mark.django_db
@patch("arabase.template_catalog.CoreHandler.sync_templates")
def test_reconcile_local_template_catalog_is_noop_when_current(
    sync_templates, data_fixture
):
    categories = {
        ARABIC_TEMPLATE_CATEGORY: data_fixture.create_template_category(
            name=ARABIC_TEMPLATE_CATEGORY
        ),
        ENGLISH_TEMPLATE_CATEGORY: data_fixture.create_template_category(
            name=ENGLISH_TEMPLATE_CATEGORY
        ),
    }
    for slug, category_name in LOCAL_TEMPLATE_CATALOG.items():
        create_template(data_fixture, slug, categories[category_name])

    assert reconcile_local_template_catalog() == {
        "changed": False,
        "removed": 0,
        "templates": 6,
    }
    sync_templates.assert_not_called()


@override_settings(TESTS=False)
@patch("arabase.tasks.reconcile_local_template_catalog_task.delay")
def test_schedule_local_template_catalog_reconciliation(delay):
    schedule_local_template_catalog_reconciliation(sender=None)

    delay.assert_called_once_with()
