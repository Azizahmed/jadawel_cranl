import json
from pathlib import Path

from django.core.files.storage import FileSystemStorage

import pytest

from arabase.dashboard.widgets.models import ChartWidget, RecordsListWidget
from jadawel.contrib.dashboard.models import Dashboard
from jadawel.contrib.database.models import Database
from jadawel.core.handler import CoreHandler
from jadawel.core.models import Template

TEMPLATE_PATH = (
    Path(__file__).parents[2] / "templates" / "saudi-budget-consolidation-en.json"
)


def _collect_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _collect_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _collect_strings(item)


@pytest.mark.django_db(transaction=True)
def test_english_saudi_budget_template_syncs_and_installs(data_fixture, tmpdir):
    payload = json.loads(TEMPLATE_PATH.read_text())
    assert payload["jadawel_template_version"] == 1
    assert payload["name"] == "Saudi Budget Consolidation and Approval"
    assert payload["categories"] == ["English Templates"]
    assert not any(
        "\u0600" <= char <= "\u06ff"
        for value in _collect_strings(payload)
        for char in value
    )

    handler = CoreHandler()
    storage = FileSystemStorage(location=str(tmpdir), base_url="http://localhost")
    handler.sync_templates(
        storage=storage, pattern="saudi-budget-consolidation-en", force=True
    )

    template = Template.objects.get(slug="saudi-budget-consolidation-en")
    user = data_fixture.create_user()
    workspace_user = data_fixture.create_user_workspace(user=user)
    applications, _ = handler.install_template(
        user, workspace_user.workspace, template, storage=storage
    )

    assert len(applications) == 2
    database = Database.objects.get(workspace=workspace_user.workspace)
    dashboard = Dashboard.objects.get(workspace=workspace_user.workspace)
    assert list(
        database.table_set.order_by("order").values_list("name", flat=True)
    ) == [
        "Budget Cycles",
        "Unified Chart of Accounts",
        "Departments and Cost Centers",
        "Budget Files",
        "Budget Items",
    ]
    assert database.table_set.get(name="Budget Items").get_model().objects.count() == 36
    assert ChartWidget.objects.filter(dashboard=dashboard).count() == 1
    assert RecordsListWidget.objects.filter(dashboard=dashboard).count() == 1
    assert dashboard.widget_set.count() == 6
