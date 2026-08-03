"""Tests for the fork's dashboard chart widget."""

from django.contrib.contenttypes.models import ContentType
from django.db.models.deletion import ProtectedError

import pytest

from arabase.dashboard.widgets.models import ChartWidget
from arabase.dashboard.widgets.widget_types import ChartWidgetType
from arabase.integrations.local_baserow.models import LocalBaserowGroupedAggregateRows
from baserow.contrib.dashboard.data_sources.models import DashboardDataSource
from baserow.contrib.dashboard.data_sources.service import DashboardDataSourceService
from baserow.contrib.dashboard.widgets.service import WidgetService
from baserow.contrib.dashboard.widgets.trash_types import WidgetTrashableItemType
from baserow.core.trash.handler import TrashHandler


def create_chart(data_fixture, user=None, **kwargs):
    user = user or data_fixture.create_user()
    dashboard = kwargs.pop(
        "dashboard", None
    ) or data_fixture.create_dashboard_application(user=user)
    data_fixture.create_local_baserow_integration(
        authorized_user=user, application=dashboard
    )
    widget = WidgetService().create_widget(
        user, "chart", dashboard.id, title="Chart", description="", **kwargs
    )
    return user, dashboard, widget


@pytest.mark.django_db
def test_create_chart_widget_creates_a_grouped_data_source(data_fixture):
    _, _, widget = create_chart(data_fixture)

    assert widget.data_source is not None
    assert widget.data_source.service.content_type == ContentType.objects.get_for_model(
        LocalBaserowGroupedAggregateRows
    )


@pytest.mark.django_db
def test_create_chart_widget_defaults_to_a_bar_chart(data_fixture):
    _, _, widget = create_chart(data_fixture)

    assert widget.chart_type == "bar"
    assert widget.show_legend is True
    assert widget.series_config == {}


@pytest.mark.django_db
def test_chart_type_is_set_on_creation(data_fixture):
    _, _, widget = create_chart(data_fixture, chart_type="doughnut")

    assert ChartWidget.objects.get(id=widget.id).chart_type == "doughnut"


@pytest.mark.django_db
def test_chart_widget_trash_restore_follows_its_data_source(data_fixture):
    user, dashboard, widget = create_chart(data_fixture)
    data_source_id = widget.data_source_id

    TrashHandler.trash(user, dashboard.workspace, dashboard, widget)
    assert DashboardDataSource.objects_and_trash.get(id=data_source_id).trashed is True

    TrashHandler.restore_item(user, WidgetTrashableItemType.type, widget.id)
    assert DashboardDataSource.objects_and_trash.get(id=data_source_id).trashed is False


@pytest.mark.django_db
def test_chart_widget_data_source_cannot_be_deleted_on_its_own(data_fixture):
    user, _, widget = create_chart(data_fixture)

    with pytest.raises(ProtectedError):
        DashboardDataSourceService().delete_data_source(user, widget.data_source_id)


@pytest.mark.django_db
def test_series_config_field_ids_are_remapped_on_import():
    # `series_config` is keyed by `field_<id>_<aggregation type>`, so an import
    # that renumbers fields has to rewrite the keys or every colour override
    # would be orphaned.
    remapped = ChartWidgetType()._remap_series_config(
        {"field_1_sum": {"color": "blue"}, "not_a_series_key": {"color": "red"}},
        {"database_fields": {1: 42}},
    )

    assert remapped == {
        "field_42_sum": {"color": "blue"},
        "not_a_series_key": {"color": "red"},
    }
