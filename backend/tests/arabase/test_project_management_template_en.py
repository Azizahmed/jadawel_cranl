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


def _contains_arabic(value):
    return any("\u0600" <= char <= "\u06ff" for char in value)


def _schema_strings(payload):
    yield payload["name"]
    yield from payload["categories"]
    for application in payload["export"]:
        yield application["name"]
        for table in application.get("tables", []):
            yield table["name"]
            yield from (field["name"] for field in table["fields"])
            yield from (view["name"] for view in table["views"])


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
    assert not any(_contains_arabic(value) for value in _schema_strings(english))

    tables = {table["name"]: table for table in english["export"][0]["tables"]}
    team_rows = tables["Team"]["rows"]
    assert [row["field_11602"] for row in team_rows] == [
        "Sara AlOtaibi",
        "Khalid AlHarbi",
        "Nora AlQahtani",
        "Abdullah AlShammari",
    ]
    assert not any(_contains_arabic(row["field_11602"]) for row in team_rows)
    assert all(row["field_11608"].startswith("+966") for row in team_rows)
    assert all(row["field_11607"].endswith("@riyadh.example") for row in team_rows)

    project_rows = tables["Projects"]["rows"]
    assert {row["field_11609"] for row in project_rows} == {
        "Riyadh E-commerce Platform",
        "Saudi Cloud Migration",
        "Arabic Brand Launch",
        "ZATCA Reporting Automation",
    }
    task_titles = {row["field_11620"] for row in tables["Tasks"]["rows"]}
    assert "Integrate mada and SADAD Payments" in task_titles

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
