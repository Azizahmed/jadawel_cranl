import json
from pathlib import Path

from django.core.files.storage import FileSystemStorage

import pytest

from jadawel.contrib.database.models import Database
from jadawel.core.handler import CoreHandler
from jadawel.core.models import Template

TEMPLATES_DIR = Path(__file__).parents[2] / "templates"
ARABIC_TEMPLATE_PATH = TEMPLATES_DIR / "arabic-project-management.json"
ENGLISH_TEMPLATE_PATH = TEMPLATES_DIR / "project-management-en.json"


def _collect_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _collect_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _collect_strings(item)


def _database_shape(payload):
    database = payload["export"][0]
    return [
        {
            "field_types": [field["type"] for field in table["fields"]],
            "view_types": [view["type"] for view in table["views"]],
            "row_count": len(table["rows"]),
        }
        for table in database["tables"]
    ]


@pytest.mark.django_db(transaction=True)
def test_english_project_management_mirrors_arabic_template(data_fixture, tmpdir):
    arabic = json.loads(ARABIC_TEMPLATE_PATH.read_text())
    english = json.loads(ENGLISH_TEMPLATE_PATH.read_text())

    assert english["name"] == "Project Management"
    assert english["categories"] == ["English Templates"]
    assert _database_shape(english) == _database_shape(arabic)
    assert not any(
        "\u0600" <= char <= "\u06ff"
        for value in _collect_strings(english)
        for char in value
    )

    handler = CoreHandler()
    storage = FileSystemStorage(location=str(tmpdir), base_url="http://localhost")
    handler.sync_templates(storage=storage, pattern="project-management-en", force=True)

    template = Template.objects.get(slug="project-management-en")
    user = data_fixture.create_user()
    workspace_user = data_fixture.create_user_workspace(user=user)
    applications, _ = handler.install_template(
        user, workspace_user.workspace, template, storage=storage
    )

    assert len(applications) == 1
    database = Database.objects.get(workspace=workspace_user.workspace)
    assert list(
        database.table_set.order_by("order").values_list("name", flat=True)
    ) == ["Team", "Projects", "Tasks"]
    assert [
        table.get_model().objects.count()
        for table in database.table_set.order_by("order")
    ] == [4, 4, 5]
