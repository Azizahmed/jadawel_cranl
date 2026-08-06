"""Tests for the records list, progress and upcoming dates widgets."""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models.deletion import ProtectedError
from django.http import HttpRequest
from django.utils import timezone

import pytest
from rest_framework.exceptions import ValidationError as DRFValidationError

from arabase.dashboard.widgets.models import (
    ProgressWidget,
    RecordsListWidget,
    UpcomingDatesWidget,
)
from arabase.dashboard.widgets.widget_types import (
    RecordsListWidgetType,
    UpcomingDatesWidgetType,
)
from arabase.integrations.local_jadawel.models import LocalJadawelUpcomingRows
from arabase.integrations.local_jadawel.upcoming_rows import (
    LocalJadawelUpcomingRowsUserServiceType,
)
from jadawel.contrib.dashboard.data_sources.dispatch_context import (
    DashboardDispatchContext,
)
from jadawel.contrib.dashboard.data_sources.models import DashboardDataSource
from jadawel.contrib.dashboard.data_sources.service import DashboardDataSourceService
from jadawel.contrib.dashboard.widgets.service import WidgetService
from jadawel.contrib.dashboard.widgets.trash_types import WidgetTrashableItemType
from jadawel.contrib.database.rows.handler import RowHandler
from jadawel.contrib.integrations.local_jadawel.models import (
    LocalJadawelAggregateRows,
    LocalJadawelListRows,
)
from jadawel.core.services.exceptions import (
    ServiceImproperlyConfiguredDispatchException,
)
from jadawel.core.services.registries import service_type_registry
from jadawel.core.trash.handler import TrashHandler


@pytest.fixture
def dashboard_setup(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    name_field = data_fixture.create_text_field(table=table, name="Name")
    amount_field = data_fixture.create_number_field(table=table, name="Amount")
    due_field = data_fixture.create_date_field(table=table, name="Due")

    today = timezone.localdate()
    RowHandler().create_rows(
        user,
        table,
        [
            {
                f"field_{name_field.id}": "Tomorrow",
                f"field_{amount_field.id}": 10,
                f"field_{due_field.id}": today + timedelta(days=1),
            },
            {
                f"field_{name_field.id}": "Next month",
                f"field_{amount_field.id}": 20,
                f"field_{due_field.id}": today + timedelta(days=30),
            },
            {
                f"field_{name_field.id}": "Overdue",
                f"field_{amount_field.id}": 5,
                f"field_{due_field.id}": today - timedelta(days=3),
            },
            {
                f"field_{name_field.id}": "No date",
                f"field_{amount_field.id}": 1,
                f"field_{due_field.id}": None,
            },
        ],
    )

    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    data_fixture.create_local_jadawel_integration(
        authorized_user=user, application=dashboard
    )

    return {
        "user": user,
        "table": table,
        "name_field": name_field,
        "amount_field": amount_field,
        "due_field": due_field,
        "dashboard": dashboard,
        "today": today,
    }


def create_widget(setup, widget_type, **kwargs):
    return WidgetService().create_widget(
        setup["user"],
        widget_type,
        setup["dashboard"].id,
        title="Widget",
        description="",
        **kwargs,
    )


def configure(setup, widget, service_type_name, **kwargs):
    DashboardDataSourceService().update_data_source(
        setup["user"],
        widget.data_source_id,
        service_type_registry.get(service_type_name),
        **kwargs,
    )


def dispatch(setup, widget):
    return DashboardDataSourceService().dispatch_data_source(
        setup["user"],
        widget.data_source_id,
        DashboardDispatchContext(HttpRequest(), widget),
    )


# --- records list ----------------------------------------------------------


@pytest.mark.django_db
def test_records_list_widget_creates_a_list_rows_data_source(dashboard_setup):
    widget = create_widget(dashboard_setup, "records_list")

    assert widget.data_source.service.content_type == ContentType.objects.get_for_model(
        LocalJadawelListRows
    )
    assert widget.field_ids == []


@pytest.mark.django_db
def test_records_list_widget_dispatches_rows(dashboard_setup):
    widget = create_widget(dashboard_setup, "records_list")
    configure(
        dashboard_setup,
        widget,
        "local_jadawel_list_rows",
        table_id=dashboard_setup["table"].id,
    )

    result = dispatch(dashboard_setup, widget)

    assert len(result["results"]) == 4
    assert result["results"][0]["Name"] == "Tomorrow"


@pytest.mark.django_db
def test_records_list_widget_stores_displayed_fields(dashboard_setup):
    widget = create_widget(
        dashboard_setup,
        "records_list",
        field_ids=[dashboard_setup["name_field"].id],
    )

    assert RecordsListWidget.objects.get(id=widget.id).field_ids == [
        dashboard_setup["name_field"].id
    ]


@pytest.mark.django_db
def test_displayed_field_ids_are_remapped_on_import():
    # Field ids are renumbered on import, and an id with no mapping belonged to a
    # field that was deleted before the export.
    remapped = RecordsListWidgetType().deserialize_property(
        "field_ids", [1, 2, 99], {"database_fields": {1: 11, 2: 22}}
    )

    assert remapped == [11, 22]


@pytest.mark.django_db
def test_records_list_widget_trash_restore_follows_its_data_source(dashboard_setup):
    widget = create_widget(dashboard_setup, "records_list")
    data_source_id = widget.data_source_id

    TrashHandler.trash(
        dashboard_setup["user"],
        dashboard_setup["dashboard"].workspace,
        dashboard_setup["dashboard"],
        widget,
    )
    assert DashboardDataSource.objects_and_trash.get(id=data_source_id).trashed is True

    TrashHandler.restore_item(
        dashboard_setup["user"], WidgetTrashableItemType.type, widget.id
    )
    assert DashboardDataSource.objects_and_trash.get(id=data_source_id).trashed is False


# --- progress --------------------------------------------------------------


@pytest.mark.django_db
def test_progress_widget_creates_an_aggregate_rows_data_source(dashboard_setup):
    widget = create_widget(dashboard_setup, "progress")

    assert widget.data_source.service.content_type == ContentType.objects.get_for_model(
        LocalJadawelAggregateRows
    )
    assert widget.display_style == "bar"
    assert widget.target_value == 100
    assert widget.warning_threshold == 50
    assert widget.success_threshold == 100


@pytest.mark.django_db
def test_progress_widget_dispatches_the_aggregation(dashboard_setup):
    widget = create_widget(dashboard_setup, "progress", target_value=100)
    configure(
        dashboard_setup,
        widget,
        "local_jadawel_aggregate_rows",
        table_id=dashboard_setup["table"].id,
        field_id=dashboard_setup["amount_field"].id,
        aggregation_type="sum",
    )

    # The widget turns the result into a percentage of its target in the browser;
    # the backend's job is only to produce the number.
    assert dispatch(dashboard_setup, widget) == {"result": "36"}


@pytest.mark.django_db
def test_progress_widget_target_must_be_positive(dashboard_setup):
    with pytest.raises(DRFValidationError):
        create_widget(dashboard_setup, "progress", target_value=0)


@pytest.mark.django_db
def test_progress_widget_thresholds_cannot_cross(dashboard_setup):
    with pytest.raises(DRFValidationError):
        create_widget(
            dashboard_setup,
            "progress",
            warning_threshold=90,
            success_threshold=50,
        )


@pytest.mark.django_db
def test_progress_widget_accepts_a_ring_and_custom_thresholds(dashboard_setup):
    widget = create_widget(
        dashboard_setup,
        "progress",
        display_style="ring",
        warning_threshold=60,
        success_threshold=80,
    )

    stored = ProgressWidget.objects.get(id=widget.id)
    assert (
        stored.display_style,
        stored.warning_threshold,
        stored.success_threshold,
    ) == (
        "ring",
        60,
        80,
    )


@pytest.mark.django_db
def test_progress_widget_data_source_cannot_be_deleted_on_its_own(dashboard_setup):
    widget = create_widget(dashboard_setup, "progress")

    with pytest.raises(ProtectedError):
        DashboardDataSourceService().delete_data_source(
            dashboard_setup["user"], widget.data_source_id
        )


# --- upcoming dates --------------------------------------------------------


@pytest.mark.django_db
def test_upcoming_dates_widget_creates_an_upcoming_rows_data_source(dashboard_setup):
    widget = create_widget(dashboard_setup, "upcoming_dates")

    assert widget.data_source.service.content_type == ContentType.objects.get_for_model(
        LocalJadawelUpcomingRows
    )
    assert UpcomingDatesWidget.objects.filter(id=widget.id).exists()


def configure_upcoming(setup, widget, **kwargs):
    configure(
        setup,
        widget,
        LocalJadawelUpcomingRowsUserServiceType.type,
        table_id=setup["table"].id,
        date_field_id=setup["due_field"].id,
        **kwargs,
    )


@pytest.mark.django_db
def test_upcoming_dates_window_excludes_rows_beyond_it(dashboard_setup):
    widget = create_widget(dashboard_setup, "upcoming_dates")
    configure_upcoming(dashboard_setup, widget, days_ahead=7)

    names = [row["Name"] for row in dispatch(dashboard_setup, widget)["results"]]

    # Overdue first (soonest-first ordering puts the past at the top), then
    # tomorrow. "Next month" is outside the window and "No date" has none.
    assert names == ["Overdue", "Tomorrow"]


@pytest.mark.django_db
def test_upcoming_dates_can_exclude_overdue_rows(dashboard_setup):
    widget = create_widget(dashboard_setup, "upcoming_dates")
    configure_upcoming(dashboard_setup, widget, days_ahead=7, include_overdue=False)

    names = [row["Name"] for row in dispatch(dashboard_setup, widget)["results"]]

    assert names == ["Tomorrow"]


@pytest.mark.django_db
def test_upcoming_dates_widens_with_days_ahead(dashboard_setup):
    widget = create_widget(dashboard_setup, "upcoming_dates")
    configure_upcoming(dashboard_setup, widget, days_ahead=60)

    names = [row["Name"] for row in dispatch(dashboard_setup, widget)["results"]]

    assert names == ["Overdue", "Tomorrow", "Next month"]


@pytest.mark.django_db
def test_upcoming_dates_without_a_date_field_is_a_configuration_error(dashboard_setup):
    widget = create_widget(dashboard_setup, "upcoming_dates")
    configure(
        dashboard_setup,
        widget,
        LocalJadawelUpcomingRowsUserServiceType.type,
        table_id=dashboard_setup["table"].id,
    )

    with pytest.raises(ServiceImproperlyConfiguredDispatchException):
        dispatch(dashboard_setup, widget)


@pytest.mark.django_db
def test_upcoming_dates_rejects_a_non_date_field(dashboard_setup):
    widget = create_widget(dashboard_setup, "upcoming_dates")

    with pytest.raises(DRFValidationError):
        configure(
            dashboard_setup,
            widget,
            LocalJadawelUpcomingRowsUserServiceType.type,
            table_id=dashboard_setup["table"].id,
            date_field_id=dashboard_setup["name_field"].id,
        )


@pytest.mark.django_db
def test_upcoming_dates_rejects_an_absurd_window(dashboard_setup):
    widget = create_widget(dashboard_setup, "upcoming_dates")

    with pytest.raises(DRFValidationError):
        configure_upcoming(dashboard_setup, widget, days_ahead=5000)


@pytest.mark.django_db
def test_upcoming_dates_handles_a_datetime_field(dashboard_setup, data_fixture):
    # A timestamp column compared against a date would include or drop a whole
    # day at the boundary depending on the time, so it is compared by date part.
    datetime_field = data_fixture.create_date_field(
        table=dashboard_setup["table"], name="DueAt", date_include_time=True
    )
    model = dashboard_setup["table"].get_model()
    row = model.objects.get(**{f"field_{dashboard_setup['name_field'].id}": "Tomorrow"})
    setattr(
        row,
        f"field_{datetime_field.id}",
        timezone.now() + timedelta(days=1),
    )
    row.save()

    widget = create_widget(dashboard_setup, "upcoming_dates")
    configure(
        dashboard_setup,
        widget,
        LocalJadawelUpcomingRowsUserServiceType.type,
        table_id=dashboard_setup["table"].id,
        date_field_id=datetime_field.id,
        days_ahead=7,
    )

    names = [row["Name"] for row in dispatch(dashboard_setup, widget)["results"]]
    assert names == ["Tomorrow"]


@pytest.mark.django_db
def test_upcoming_dates_date_field_is_remapped_on_import(dashboard_setup):
    remapped = UpcomingDatesWidgetType().deserialize_property(
        "field_ids", [7], {"database_fields": {7: 70}}
    )
    assert remapped == [70]

    service_type = LocalJadawelUpcomingRowsUserServiceType()
    assert (
        service_type.deserialize_property(
            "date_field_id", 7, {"database_fields": {7: 70}}
        )
        == 70
    )


@pytest.mark.django_db
def test_changing_the_table_drops_the_date_field(dashboard_setup, data_fixture):
    widget = create_widget(dashboard_setup, "upcoming_dates")
    configure_upcoming(dashboard_setup, widget)
    other_table = data_fixture.create_database_table(
        database=dashboard_setup["table"].database
    )

    configure(
        dashboard_setup,
        widget,
        LocalJadawelUpcomingRowsUserServiceType.type,
        table_id=other_table.id,
    )

    service = DashboardDataSource.objects.get(id=widget.data_source_id).service.specific
    assert service.date_field_id is None
