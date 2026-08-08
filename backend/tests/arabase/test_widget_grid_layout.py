from decimal import Decimal

from django.urls import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
)

from jadawel.contrib.dashboard.application_types import DashboardApplicationType
from jadawel.contrib.dashboard.widgets.actions import UpdateWidgetActionType
from jadawel.contrib.dashboard.widgets.models import Widget
from jadawel.contrib.dashboard.widgets.service import WidgetService
from jadawel.core.action.handler import ActionHandler
from jadawel.core.action.registries import action_type_registry
from jadawel.core.action.scopes import ApplicationActionScopeType
from jadawel.core.registries import ImportExportConfig
from jadawel.test_utils.helpers import assert_undo_redo_actions_are_valid


@pytest.mark.django_db
def test_create_widget_uses_default_grid_size(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)

    url = reverse("api:dashboard:widgets:list", kwargs={"dashboard_id": dashboard.id})
    response = api_client.post(
        url,
        {"title": "Title", "type": "summary"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_200_OK, response_json
    assert response_json["width"] == 3
    assert response_json["height"] == 2

    widget = Widget.objects.get(id=response_json["id"])
    assert widget.width == 3
    assert widget.height == 2


@pytest.mark.django_db
def test_create_widget_with_explicit_grid_size(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)

    url = reverse("api:dashboard:widgets:list", kwargs={"dashboard_id": dashboard.id})
    response = api_client.post(
        url,
        {"title": "Title", "type": "summary", "width": 1, "height": 3},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_200_OK, response_json
    assert response_json["width"] == 1
    assert response_json["height"] == 3

    widget = Widget.objects.get(id=response_json["id"])
    assert widget.width == 1
    assert widget.height == 3


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value", [("width", 0), ("width", 4), ("height", 0), ("height", 4)]
)
def test_create_widget_with_invalid_grid_size(api_client, data_fixture, field, value):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)

    url = reverse("api:dashboard:widgets:list", kwargs={"dashboard_id": dashboard.id})
    response = api_client.post(
        url,
        {"title": "Title", "type": "summary", field: value},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert Widget.objects.count() == 0


@pytest.mark.django_db
def test_update_widget_grid_size(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)
    widget = WidgetService().create_widget(user, "summary", dashboard.id, title="T")

    url = reverse("api:dashboard:widgets:item", kwargs={"widget_id": widget.id})
    response = api_client.patch(
        url,
        {"width": 2, "height": 1},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_200_OK, response_json
    assert response_json["width"] == 2
    assert response_json["height"] == 1

    widget.refresh_from_db()
    assert widget.width == 2
    assert widget.height == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value", [("width", 0), ("width", 4), ("height", 0), ("height", 4)]
)
def test_update_widget_with_invalid_grid_size(api_client, data_fixture, field, value):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)
    widget = WidgetService().create_widget(user, "summary", dashboard.id, title="T")

    url = reverse("api:dashboard:widgets:item", kwargs={"widget_id": widget.id})
    response = api_client.patch(
        url,
        {field: value},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"

    widget.refresh_from_db()
    assert widget.width == 3
    assert widget.height == 2


@pytest.mark.django_db
def test_update_widget_order_reorders_widgets(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)
    service = WidgetService()
    widget_1 = service.create_widget(user, "summary", dashboard.id, title="W1")
    widget_2 = service.create_widget(user, "summary", dashboard.id, title="W2")
    widget_3 = service.create_widget(user, "summary", dashboard.id, title="W3")

    url = reverse("api:dashboard:widgets:item", kwargs={"widget_id": widget_1.id})
    response = api_client.patch(
        url,
        {"order": "2.5"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_200_OK, response_json
    assert response_json["order"] == "2.50000000000000000000"

    list_url = reverse(
        "api:dashboard:widgets:list", kwargs={"dashboard_id": dashboard.id}
    )
    response = api_client.get(
        list_url,
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK
    assert [w["id"] for w in response.json()] == [
        widget_2.id,
        widget_1.id,
        widget_3.id,
    ]


@pytest.mark.django_db
def test_update_widget_grid_size_and_order_permission_denied(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application()
    data_source = (
        data_fixture.create_dashboard_local_jadawel_aggregate_rows_data_source(
            dashboard=dashboard, name="Data source 1"
        )
    )
    widget = data_fixture.create_summary_widget(
        dashboard=dashboard, data_source=data_source
    )

    url = reverse("api:dashboard:widgets:item", kwargs={"widget_id": widget.id})
    response = api_client.patch(
        url,
        {"width": 1, "order": "5"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json()["error"] == "PERMISSION_DENIED"

    widget.refresh_from_db()
    assert widget.width == 3
    assert widget.order == Decimal("1")


@pytest.mark.django_db
@pytest.mark.undo_redo
def test_can_undo_redo_update_widget_grid_size_and_order(data_fixture):
    session_id = "session-id"
    user = data_fixture.create_user(session_id=session_id)
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(
        workspace=workspace, name="Dashboard 1", user=user
    )
    widget = WidgetService().create_widget(user, "summary", dashboard.id, title="W1")
    WidgetService().create_widget(user, "summary", dashboard.id, title="W2")
    original_order = widget.order

    # do
    updated_widget = action_type_registry.get_by_type(UpdateWidgetActionType).do(
        user,
        widget.id,
        "summary",
        {"width": 1, "height": 3, "order": Decimal("1.5")},
    )

    assert updated_widget.width == 1
    assert updated_widget.height == 3
    assert updated_widget.order == Decimal("1.5")

    # undo
    ActionHandler.undo(
        user,
        [ApplicationActionScopeType.value(application_id=dashboard.id)],
        session_id,
    )

    updated_widget.refresh_from_db()
    assert updated_widget.width == 3
    assert updated_widget.height == 2
    assert updated_widget.order == original_order

    # redo
    actions_redone = ActionHandler.redo(
        user,
        [ApplicationActionScopeType.value(application_id=dashboard.id)],
        session_id,
    )
    assert_undo_redo_actions_are_valid(actions_redone, [UpdateWidgetActionType])

    updated_widget.refresh_from_db()
    assert updated_widget.width == 1
    assert updated_widget.height == 3
    assert updated_widget.order == Decimal("1.5")


@pytest.mark.django_db
def test_dashboard_export_import_round_trip_preserves_grid_size(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    new_workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(
        workspace=workspace, name="Dashboard 1", user=user
    )
    widget = WidgetService().create_widget(
        user, "summary", dashboard.id, title="W1", width=1, height=3
    )

    serialized = DashboardApplicationType().export_serialized(
        dashboard, ImportExportConfig(include_permission_data=True)
    )
    serialized_widget = serialized["widgets"][0]
    assert serialized_widget["width"] == 1
    assert serialized_widget["height"] == 3
    assert serialized_widget["order"] == str(widget.order)

    imported_dashboard = DashboardApplicationType().import_serialized(
        new_workspace,
        serialized,
        ImportExportConfig(include_permission_data=True),
        {},
    )

    imported_widgets = Widget.objects.filter(dashboard=imported_dashboard)
    assert imported_widgets.count() == 1
    imported_widget = imported_widgets[0]
    assert imported_widget.title == "W1"
    assert imported_widget.width == 1
    assert imported_widget.height == 3
    assert imported_widget.order == widget.order
