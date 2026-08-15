"""Date columns are read from the column, not from the display setting.

`date_include_time` says whether the interface shows a time. It does not say
what the database stores: `created_on` and `last_modified` always store a
`timestamptz`. Two widgets asked the display setting anyway, which cost a
bucket explosion in one and a dropped final day in the other. These tests pin
the distinction at the helper and at both call sites.
"""

from datetime import timedelta

from django.http import HttpRequest
from django.utils import timezone

import pytest

from arabase.integrations.local_jadawel.date_columns import (
    field_tzinfo,
    is_datetime_column,
)
from arabase.integrations.local_jadawel.upcoming_rows import (
    LocalJadawelUpcomingRowsUserServiceType,
)
from jadawel.contrib.dashboard.data_sources.dispatch_context import (
    DashboardDispatchContext,
)
from jadawel.contrib.dashboard.data_sources.service import DashboardDataSourceService
from jadawel.contrib.dashboard.widgets.service import WidgetService
from jadawel.contrib.database.rows.handler import RowHandler
from jadawel.core.services.registries import service_type_registry


@pytest.mark.django_db
class TestIsDatetimeColumn:
    def test_a_plain_date_field_is_not_a_datetime(self, data_fixture):
        table = data_fixture.create_database_table()
        field = data_fixture.create_date_field(table=table, date_include_time=False)

        assert is_datetime_column(table.get_model(), field) is False

    def test_a_date_field_with_time_is_a_datetime(self, data_fixture):
        table = data_fixture.create_database_table()
        field = data_fixture.create_date_field(table=table, date_include_time=True)

        assert is_datetime_column(table.get_model(), field) is True

    def test_created_on_is_a_datetime_even_with_the_time_hidden(self, data_fixture):
        """The regression this helper exists for.

        `created_on` stores a timestamptz whatever `date_include_time` says, so
        reading the flag classified it as a plain date — which is what let a
        chart group on a raw timestamp and an agenda drop its last day.
        """

        table = data_fixture.create_database_table()
        field = data_fixture.create_created_on_field(
            table=table, date_include_time=False
        )

        assert field.date_include_time is False
        assert is_datetime_column(table.get_model(), field) is True

    def test_an_unknown_column_falls_back_to_the_flag(self, data_fixture):
        table = data_fixture.create_database_table()
        field = data_fixture.create_date_field(table=table, date_include_time=True)

        # No model at all: better to answer from the display flag than to raise
        # in the middle of a dispatch.
        assert is_datetime_column(None, field) is True


@pytest.mark.django_db
class TestFieldTzinfo:
    def test_no_forced_timezone_leaves_the_default_alone(self, data_fixture):
        table = data_fixture.create_database_table()
        field = data_fixture.create_date_field(table=table)

        assert field_tzinfo(field) is None

    def test_a_forced_timezone_is_honoured(self, data_fixture):
        table = data_fixture.create_database_table()
        field = data_fixture.create_date_field(
            table=table, date_include_time=True, date_force_timezone="Asia/Riyadh"
        )

        tzinfo = field_tzinfo(field)

        assert tzinfo is not None
        assert str(tzinfo) == "Asia/Riyadh"

    def test_an_unusable_timezone_does_not_raise(self, data_fixture):
        table = data_fixture.create_database_table()
        field = data_fixture.create_date_field(table=table, date_include_time=True)
        field.date_force_timezone = "Mars/Olympus_Mons"

        assert field_tzinfo(field) is None


@pytest.fixture
def agenda(data_fixture):
    """An upcoming-dates widget built on a `created_on` column.

    This is the shape that reproduces the bug rather than merely resembling it:
    `created_on` stores a timestamptz while `date_include_time` is False, so the
    old check classified it as a plain date and compared a timestamp against a
    date — which Django coerces to midnight.
    """

    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    name_field = data_fixture.create_text_field(table=table, name="Name")
    due_field = data_fixture.create_created_on_field(
        table=table, name="Due", date_include_time=False
    )

    RowHandler().create_rows(
        user,
        table,
        [
            {f"field_{name_field.id}": "Last day of the window"},
            {f"field_{name_field.id}": "Ancient"},
            {f"field_{name_field.id}": "Yesterday"},
        ],
    )

    # 21:00 rather than an offset from "now", so the row's date part is exactly
    # day 7 whatever time the suite runs at. Everything after midnight on the
    # final day is what used to be dropped.
    model = table.get_model()
    anchor = timezone.now().replace(hour=21, minute=0, second=0, microsecond=0)
    for name, when in (
        ("Last day of the window", anchor + timedelta(days=7)),
        ("Ancient", anchor - timedelta(days=400)),
        ("Yesterday", anchor - timedelta(days=1)),
    ):
        model.objects.filter(**{f"field_{name_field.id}": name}).update(
            **{due_field.db_column: when}
        )

    today = timezone.localdate()
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    data_fixture.create_local_jadawel_integration(
        authorized_user=user, application=dashboard
    )
    widget = WidgetService().create_widget(
        user, "upcoming_dates", dashboard.id, title="Agenda", description=""
    )
    return {
        "user": user,
        "widget": widget,
        "table": table,
        "due_field": due_field,
        "today": today,
    }


def _configure(setup, **kwargs):
    DashboardDataSourceService().update_data_source(
        setup["user"],
        setup["widget"].data_source_id,
        service_type_registry.get(LocalJadawelUpcomingRowsUserServiceType.type),
        table_id=setup["table"].id,
        date_field_id=setup["due_field"].id,
        **kwargs,
    )


def _names(setup):
    result = DashboardDataSourceService().dispatch_data_source(
        setup["user"],
        setup["widget"].data_source_id,
        DashboardDispatchContext(HttpRequest(), setup["widget"]),
    )
    return [row["Name"] for row in result["results"]]


@pytest.mark.django_db
def test_the_last_day_of_the_window_is_included(agenda):
    """A row due on day 7 of a 7-day window belongs in it.

    With a timestamp column compared against a date, Django coerces the date to
    midnight, so everything after 00:00 on the final day fell outside.
    """

    _configure(agenda, days_ahead=7)

    assert "Last day of the window" in _names(agenda)


@pytest.mark.django_db
def test_overdue_rows_are_bounded_on_the_past_side(agenda):
    """Including overdue rows must not mean including all of history.

    Results are ordered soonest-first and capped, so an unbounded past lets a
    tail of old rows fill the widget and hide everything upcoming.
    """

    _configure(agenda, days_ahead=7, include_overdue=True)

    names = _names(agenda)

    assert "Yesterday" in names
    assert "Ancient" not in names
