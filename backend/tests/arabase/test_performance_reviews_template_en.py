import json
from pathlib import Path

from django.core.files.storage import FileSystemStorage

import pytest

from jadawel.contrib.database.models import Database
from jadawel.contrib.database.views.handler import ViewHandler
from jadawel.contrib.database.views.models import GridView
from jadawel.core.handler import CoreHandler
from jadawel.core.models import Template

TEMPLATE_PATH = Path(__file__).parents[2] / "templates" / "performance-reviews.json"


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


@pytest.mark.django_db(transaction=True)
def test_english_performance_review_has_saudi_sample_data(data_fixture, tmpdir):
    payload = json.loads(TEMPLATE_PATH.read_text())
    assert payload["jadawel_template_version"] == 1
    assert payload["name"] == "Performance Reviews"
    assert payload["categories"] == ["English Templates"]
    assert not any(_contains_arabic(value) for value in _schema_strings(payload))

    database_export = payload["export"][0]
    tables = {table["name"]: table for table in database_export["tables"]}
    employee_rows = tables["Employees"]["rows"]
    assert len(employee_rows) == 23
    assert [
        (row["field_306886"], row["field_306885"]) for row in employee_rows[:5]
    ] == [
        ("Mohammed", "AlOtaibi"),
        ("Sara", "AlQahtani"),
        ("Khalid", "AlHarbi"),
        ("Nora", "AlGhamdi"),
        ("Abdullah", "AlShammari"),
    ]
    assert all(
        not _contains_arabic(row["field_306885"])
        and not _contains_arabic(row["field_306886"])
        for row in employee_rows
    )
    assert all(row["field_306888"].startswith("+966") for row in employee_rows)
    assert all(row["field_306889"].endswith("@riyadh.example") for row in employee_rows)

    reviewer_rows = tables["Reviewers"]["rows"]
    assert len(reviewer_rows) == 12
    assert [row["field_318853"] for row in reviewer_rows[:3]] == [
        "Ahmed AlSalem",
        "Latifa AlAbdullah",
        "Nasser AlDosari",
    ]
    assert all(not _contains_arabic(row["field_318853"]) for row in reviewer_rows)
    assert all(row["field_318880"].startswith("+966") for row in reviewer_rows)
    assert {row["field_318865"] for row in tables["Departments"]["rows"]} == {
        "Digital Products - Riyadh",
        "Finance and Zakat",
        "Legal and Compliance",
        "National Logistics",
        "People and Culture",
        "Saudi Customer Experience",
        "Procurement and Local Content",
    }
    assert all(
        any(
            marker in row["field_310035"]
            for marker in ("Saudi", "Riyadh", "Jeddah", "ZATCA", "Vision 2030")
        )
        for row in tables["Reviews"]["rows"]
    )

    handler = CoreHandler()
    storage = FileSystemStorage(location=str(tmpdir), base_url="http://localhost")
    handler.sync_templates(storage=storage, pattern="performance-reviews", force=True)

    template = Template.objects.get(slug="performance-reviews")
    user = data_fixture.create_user()
    workspace_user = data_fixture.create_user_workspace(user=user)
    applications, _ = handler.install_template(
        user, workspace_user.workspace, template, storage=storage
    )

    assert len(applications) == 1
    database = Database.objects.get(workspace=workspace_user.workspace)
    assert list(
        database.table_set.order_by("order").values_list("name", flat=True)
    ) == [
        "Employees",
        "Departments",
        "Titles",
        "Review periods",
        "Reviewers",
        "Reviews",
    ]
    assert [
        table.get_model().objects.count()
        for table in database.table_set.order_by("order")
    ] == [23, 7, 10, 12, 12, 45]

    view_handler = ViewHandler()
    for view in GridView.objects.filter(table__database=database):
        view_handler.get_view_field_aggregations(user, view)
