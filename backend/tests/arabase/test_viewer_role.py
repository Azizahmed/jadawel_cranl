"""Tests for the additive workspace VIEWER role (#36).

A viewer sees everything a member sees — including row coloring — but the
operations that mutate a view's configuration (decorations, filters, filter
groups, sortings, group bys) are denied with the standard permission error.
"""

from django.urls import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
)

from jadawel.core.handler import CoreHandler
from jadawel.core.registries import permission_manager_type_registry


@pytest.fixture
def viewer_setup(data_fixture):
    owner, owner_token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=owner)
    view = data_fixture.create_grid_view(table=table, public=False)
    status = data_fixture.create_single_select_field(table=table, name="Status")

    viewer, viewer_token = data_fixture.create_user_and_token()
    data_fixture.create_user_workspace(
        workspace=table.database.workspace, user=viewer, permissions="VIEWER"
    )

    return {
        "owner": owner,
        "owner_token": owner_token,
        "viewer": viewer,
        "viewer_token": viewer_token,
        "table": table,
        "view": view,
        "status": status,
    }


def auth(token):
    return {"HTTP_AUTHORIZATION": f"JWT {token}"}


def decoration_payload(setup):
    return {
        "type": "background_color",
        "value_provider_type": "single_select_color",
        "value_provider_conf": {"field_id": setup["status"].id},
    }


VIEW_CONFIG_URLS = {
    "decorations": lambda setup: reverse(
        "api:database:views:list_decorations", kwargs={"view_id": setup["view"].id}
    ),
    "filters": lambda setup: reverse(
        "api:database:views:list_filters", kwargs={"view_id": setup["view"].id}
    ),
    "sortings": lambda setup: reverse(
        "api:database:views:list_sortings", kwargs={"view_id": setup["view"].id}
    ),
    "group_bys": lambda setup: reverse(
        "api:database:views:list_group_bys", kwargs={"view_id": setup["view"].id}
    ),
}


@pytest.mark.django_db
def test_viewer_role_manager_is_registered():
    manager = permission_manager_type_registry.get("viewer_role")
    assert "database.table.view.create_decoration" in manager.VIEWER_DENIED_OPERATIONS
    assert "database.table.view.list_decoration" not in manager.VIEWER_DENIED_OPERATIONS


def create_body(resource, setup):
    """A body that passes serializer validation for each resource.

    The permission check happens after body validation, so the request must
    be well-formed to prove the viewer is denied by the role and not by a
    validation error.
    """
    if resource == "decorations":
        return decoration_payload(setup)
    if resource == "filters":
        return {"field": setup["status"].id, "type": "contains", "value": "x"}
    # sortings and group bys
    return {"field": setup["status"].id, "order": "ASC"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "resource", ["decorations", "filters", "sortings", "group_bys"]
)
def test_viewer_cannot_create_view_configuration(
    api_client, data_fixture, viewer_setup, resource
):
    """A viewer is denied on every view-configuration create endpoint."""
    setup = viewer_setup
    response = api_client.post(
        VIEW_CONFIG_URLS[resource](setup),
        create_body(resource, setup),
        format="json",
        **auth(setup["viewer_token"]),
    )
    assert response.status_code == HTTP_401_UNAUTHORIZED, response.content
    assert response.json()["error"] == "PERMISSION_DENIED"


@pytest.mark.django_db
def test_viewer_can_read_but_not_change_decorations(
    api_client, data_fixture, viewer_setup
):
    setup = viewer_setup
    decoration = data_fixture.create_view_decoration(
        view=setup["view"],
        type="background_color",
        value_provider_type="single_select_color",
        value_provider_conf={"field_id": setup["status"].id},
        user=setup["owner"],
    )

    listing = api_client.get(
        reverse(
            "api:database:views:list_decorations", kwargs={"view_id": setup["view"].id}
        ),
        **auth(setup["viewer_token"]),
    )
    assert listing.status_code == HTTP_200_OK, listing.content
    assert [d["type"] for d in listing.json()] == ["background_color"]

    item_url = reverse(
        "api:database:views:decoration_item",
        kwargs={"view_decoration_id": decoration.id},
    )
    updated = api_client.patch(
        item_url,
        decoration_payload(setup),
        format="json",
        **auth(setup["viewer_token"]),
    )
    assert updated.status_code == HTTP_401_UNAUTHORIZED
    assert updated.json()["error"] == "PERMISSION_DENIED"

    deleted = api_client.delete(item_url, **auth(setup["viewer_token"]))
    assert deleted.status_code == HTTP_401_UNAUTHORIZED
    assert deleted.json()["error"] == "PERMISSION_DENIED"


@pytest.mark.django_db
def test_member_still_manages_view_configuration(
    api_client, data_fixture, viewer_setup
):
    """The VIEWER denials must not leak into the MEMBER role."""
    setup = viewer_setup
    member, member_token = data_fixture.create_user_and_token()
    data_fixture.create_user_workspace(
        workspace=setup["table"].database.workspace, user=member, permissions="MEMBER"
    )
    response = api_client.post(
        reverse(
            "api:database:views:list_decorations", kwargs={"view_id": setup["view"].id}
        ),
        decoration_payload(setup),
        format="json",
        **auth(member_token),
    )
    assert response.status_code == HTTP_200_OK, response.content


@pytest.mark.django_db
def test_admin_can_assign_the_viewer_role(api_client, data_fixture, viewer_setup):
    setup = viewer_setup
    member, member_token = data_fixture.create_user_and_token()
    workspace_user = data_fixture.create_user_workspace(
        workspace=setup["table"].database.workspace, user=member, permissions="MEMBER"
    )

    response = api_client.patch(
        reverse(
            "api:workspaces:users:item",
            kwargs={"workspace_user_id": workspace_user.id},
        ),
        {"permissions": "VIEWER"},
        format="json",
        **auth(setup["owner_token"]),
    )
    assert response.status_code == HTTP_200_OK, response.content
    assert response.json()["permissions"] == "VIEWER"

    # The freshly-demoted member is now denied view-configuration writes.
    denied = api_client.post(
        reverse(
            "api:database:views:list_decorations", kwargs={"view_id": setup["view"].id}
        ),
        decoration_payload(setup),
        format="json",
        **auth(member_token),
    )
    assert denied.status_code == HTTP_401_UNAUTHORIZED
    assert denied.json()["error"] == "PERMISSION_DENIED"


@pytest.mark.django_db
def test_viewer_denied_operations_surface_in_permissions_object(viewer_setup):
    setup = viewer_setup
    permissions = CoreHandler().get_permissions(
        setup["viewer"], workspace=setup["table"].database.workspace
    )
    viewer_entry = next(
        (entry for entry in permissions if entry["name"] == "viewer_role"), None
    )
    assert viewer_entry is not None
    assert (
        "database.table.view.create_decoration"
        in (viewer_entry["permissions"]["viewer_denied_operations"])
    )
