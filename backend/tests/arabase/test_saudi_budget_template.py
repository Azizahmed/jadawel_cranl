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
    Path(__file__).parents[2] / "templates" / "saudi-budget-consolidation.json"
)


@pytest.mark.django_db(transaction=True)
def test_saudi_budget_template_sync_install_and_dashboard(data_fixture, tmpdir):
    payload = json.loads(TEMPLATE_PATH.read_text())
    assert payload["jadawel_template_version"] == 1
    assert payload["open_application"] == 2
    assert payload["export"][0]["type"] == "database"
    assert payload["export"][1]["type"] == "dashboard"
    assert len(payload["export"][0]["tables"][-1]["rows"]) == 36

    handler = CoreHandler()
    storage = FileSystemStorage(location=str(tmpdir), base_url="http://localhost")
    handler.sync_templates(
        storage=storage, pattern="saudi-budget-consolidation", force=True
    )

    template = Template.objects.get(slug="saudi-budget-consolidation")
    user = data_fixture.create_user()
    workspace_user = data_fixture.create_user_workspace(user=user)
    applications, id_mapping = handler.install_template(
        user, workspace_user.workspace, template, storage=storage
    )

    assert len(applications) == 2
    database = Database.objects.get(workspace=workspace_user.workspace)
    dashboard = Dashboard.objects.get(workspace=workspace_user.workspace)
    assert database.table_set.count() == 5
    assert list(
        database.table_set.order_by("order").values_list("name", flat=True)
    ) == [
        "دورات الميزانية",
        "دليل الحسابات الموحد",
        "الإدارات ومراكز التكلفة",
        "ملفات الميزانية",
        "بنود الميزانية",
    ]
    assert (
        database.table_set.get(name="دليل الحسابات الموحد").get_model().objects.count()
        == 6
    )

    items = database.table_set.get(name="بنود الميزانية")
    model = items.get_model()
    assert model.objects.count() == 36
    item_id = items.field_set.get(name="معرف البند")
    validation = items.field_set.get(name="حالة التحقق")
    nonrecoverable_vat = items.field_set.get(name="VAT غير القابل للاسترداد")
    recommendation = items.field_set.get(name="توصية المالية")
    assert validation.get_type().type == "formula"
    assert items.field_set.get(name="حالة الملف").get_type().type == "lookup"

    valid_row = model.objects.get(**{item_id.db_column: "BUD-001"})
    warning_row = model.objects.get(**{item_id.db_column: "BUD-003"})
    assert getattr(valid_row, validation.db_column) == "✅ صالح للتجميع"
    assert getattr(warning_row, validation.db_column) == "⚠️ لم تراجع المالية"
    assert getattr(valid_row, nonrecoverable_vat.db_column) == 37800
    assert getattr(valid_row, recommendation.db_column) == 289800

    board_view = items.view_set.get(name="جاهز للمجلس")
    follow_up_view = items.view_set.get(name="بنود تحتاج متابعة")
    assert board_view.viewfilter_set.filter(type="single_select_equal").exists()
    assert follow_up_view.viewfilter_set.filter(type="single_select_not_equal").exists()

    assert ChartWidget.objects.filter(dashboard=dashboard).count() == 1
    assert RecordsListWidget.objects.filter(dashboard=dashboard).count() == 1
    assert dashboard.widget_set.count() == 6
    chart = ChartWidget.objects.get(dashboard=dashboard)
    chart_service = chart.data_source.service.specific
    assert chart_service.table_id == items.id
    assert chart_service.view_id == board_view.id
    assert chart_service.service_aggregation_series.count() == 1
    assert chart_service.service_aggregation_group_bys.count() == 1

    records = RecordsListWidget.objects.get(dashboard=dashboard)
    assert records.data_source.service.specific.view_id == follow_up_view.id
    assert records.data_source.service.specific.table_id == items.id
    assert (
        records.data_source.service.specific.integration.specific.authorized_user_id
        == user.id
    )
    assert id_mapping["database_fields"]

    preview_dashboard = Dashboard.objects.get(workspace=template.workspace)
    assert template.open_application == preview_dashboard.id
    assert template.open_application != dashboard.id
