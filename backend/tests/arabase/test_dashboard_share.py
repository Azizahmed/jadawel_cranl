"""Public link sharing for dashboards.

Mirrors the guarantees a shared form view gives: only someone who can edit the
application can create, rotate or revoke the link; anyone with the link can read
the dashboard; a password turns the link into a two-step flow; and the link
never becomes a way to reach a *different* dashboard's data.
"""

from django.shortcuts import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)

from arabase.dashboard.share.handler import DashboardShareHandler
from arabase.dashboard.share.models import DashboardShare


def share_url(dashboard):
    return reverse("api:arabase:dashboard_share", kwargs={"dashboard_id": dashboard.id})


def rotate_url(dashboard):
    return reverse(
        "api:arabase:dashboard_share_rotate_slug", kwargs={"dashboard_id": dashboard.id}
    )


def password_url(dashboard):
    return reverse(
        "api:arabase:dashboard_share_password", kwargs={"dashboard_id": dashboard.id}
    )


def public_url(slug):
    return reverse("api:arabase:public_dashboard", kwargs={"slug": slug})


def public_auth_url(slug):
    return reverse("api:arabase:public_dashboard_auth", kwargs={"slug": slug})


def dispatch_url(slug, data_source_id):
    return reverse(
        "api:arabase:public_dashboard_dispatch",
        kwargs={"slug": slug, "data_source_id": data_source_id},
    )


@pytest.mark.django_db
def test_create_share_returns_a_slug_and_is_idempotent(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)

    response = api_client.post(
        share_url(dashboard), **{"HTTP_AUTHORIZATION": f"JWT {token}"}
    )
    assert response.status_code == HTTP_200_OK
    first = response.json()
    assert first["dashboard_id"] == dashboard.id
    assert first["slug"]
    assert first["has_password"] is False

    response = api_client.post(
        share_url(dashboard), **{"HTTP_AUTHORIZATION": f"JWT {token}"}
    )
    assert response.status_code == HTTP_200_OK
    assert response.json()["slug"] == first["slug"]
    assert DashboardShare.objects.filter(dashboard=dashboard).count() == 1


@pytest.mark.django_db
def test_get_share_is_404_until_the_dashboard_is_shared(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)

    response = api_client.get(
        share_url(dashboard), **{"HTTP_AUTHORIZATION": f"JWT {token}"}
    )
    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()["error"] == "ERROR_DASHBOARD_SHARE_DOES_NOT_EXIST"

    DashboardShareHandler().create_share(dashboard)

    response = api_client.get(
        share_url(dashboard), **{"HTTP_AUTHORIZATION": f"JWT {token}"}
    )
    assert response.status_code == HTTP_200_OK


@pytest.mark.django_db
def test_a_workspace_member_can_share(api_client, data_fixture):
    # `application.update` — the same bar a shared view uses — is granted to
    # every member of the workspace, not only to admins.
    admin = data_fixture.create_user()
    member, member_token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=admin)
    data_fixture.create_user_workspace(
        workspace=workspace, user=member, permissions="MEMBER"
    )
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)

    response = api_client.post(
        share_url(dashboard), **{"HTTP_AUTHORIZATION": f"JWT {member_token}"}
    )
    assert response.status_code == HTTP_200_OK
    assert DashboardShare.objects.filter(dashboard=dashboard).exists()


@pytest.mark.django_db
def test_a_user_outside_the_workspace_cannot_share(api_client, data_fixture):
    data_fixture.create_user()
    outsider, outsider_token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application()

    response = api_client.post(
        share_url(dashboard), **{"HTTP_AUTHORIZATION": f"JWT {outsider_token}"}
    )
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_rotating_the_slug_invalidates_the_previous_url(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    share = DashboardShareHandler().create_share(dashboard)
    old_slug = share.slug

    response = api_client.post(
        rotate_url(dashboard), **{"HTTP_AUTHORIZATION": f"JWT {token}"}
    )
    assert response.status_code == HTTP_200_OK
    new_slug = response.json()["slug"]
    assert new_slug != old_slug

    assert api_client.get(public_url(old_slug)).status_code == HTTP_404_NOT_FOUND
    assert api_client.get(public_url(new_slug)).status_code == HTTP_200_OK


@pytest.mark.django_db
def test_deleting_the_share_revokes_the_link(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    slug = DashboardShareHandler().create_share(dashboard).slug

    response = api_client.delete(
        share_url(dashboard), **{"HTTP_AUTHORIZATION": f"JWT {token}"}
    )
    assert response.status_code == HTTP_204_NO_CONTENT
    assert api_client.get(public_url(slug)).status_code == HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_public_info_returns_the_dashboard_widgets_and_data_sources(
    api_client, data_fixture
):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(
        workspace=workspace, name="Sales", description="Numbers"
    )
    data_source = (
        data_fixture.create_dashboard_local_jadawel_aggregate_rows_data_source(
            dashboard=dashboard
        )
    )
    widget = data_fixture.create_summary_widget(
        dashboard=dashboard, data_source=data_source, title="Total"
    )
    slug = DashboardShareHandler().create_share(dashboard).slug

    # No credentials at all: this is the anonymous visitor path.
    response = api_client.get(public_url(slug))
    assert response.status_code == HTTP_200_OK
    body = response.json()

    assert body["dashboard"] == {
        "id": dashboard.id,
        "name": "Sales",
        "description": "Numbers",
    }
    assert [w["id"] for w in body["widgets"]] == [widget.id]
    assert body["widgets"][0]["title"] == "Total"
    assert [d["id"] for d in body["data_sources"]] == [data_source.id]


@pytest.mark.django_db
def test_public_info_does_not_leak_the_workspace(api_client, data_fixture):
    dashboard = data_fixture.create_dashboard_application()
    slug = DashboardShareHandler().create_share(dashboard).slug

    body = api_client.get(public_url(slug)).json()

    assert set(body["dashboard"]) == {"id", "name", "description"}


@pytest.mark.django_db
def test_a_trashed_dashboard_is_not_publicly_reachable(api_client, data_fixture):
    dashboard = data_fixture.create_dashboard_application()
    slug = DashboardShareHandler().create_share(dashboard).slug

    dashboard.trashed = True
    dashboard.save()

    assert api_client.get(public_url(slug)).status_code == HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_password_protected_link_needs_a_token(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    slug = DashboardShareHandler().create_share(dashboard).slug

    response = api_client.patch(
        password_url(dashboard),
        {"password": "letmein"},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_200_OK
    assert response.json()["has_password"] is True

    response = api_client.get(public_url(slug))
    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert (
        response.json()["error"]
        == "ERROR_NO_AUTHORIZATION_TO_PUBLICLY_SHARED_DASHBOARD"
    )

    response = api_client.post(
        public_auth_url(slug), {"password": "wrong"}, format="json"
    )
    assert response.status_code == HTTP_401_UNAUTHORIZED

    response = api_client.post(
        public_auth_url(slug), {"password": "letmein"}, format="json"
    )
    assert response.status_code == HTTP_200_OK
    access_token = response.json()["access_token"]

    response = api_client.get(
        public_url(slug),
        **{"HTTP_JADAWEL_VIEW_AUTHORIZATION": f"JWT {access_token}"},
    )
    assert response.status_code == HTTP_200_OK


@pytest.mark.django_db
def test_removing_the_password_reopens_the_link(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    handler = DashboardShareHandler()
    share = handler.set_password(handler.create_share(dashboard), "letmein")

    response = api_client.patch(
        password_url(dashboard),
        {"password": None},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_200_OK
    assert response.json()["has_password"] is False
    assert api_client.get(public_url(share.slug)).status_code == HTTP_200_OK


@pytest.mark.django_db
def test_rotating_the_slug_invalidates_an_issued_password_token(
    api_client, data_fixture
):
    dashboard = data_fixture.create_dashboard_application()
    handler = DashboardShareHandler()
    share = handler.set_password(handler.create_share(dashboard), "letmein")
    access_token = handler.encode_token(share)

    handler.rotate_slug(share)

    response = api_client.get(
        public_url(share.slug),
        **{"HTTP_JADAWEL_VIEW_AUTHORIZATION": f"JWT {access_token}"},
    )
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_the_password_applies_to_the_owner_too(api_client, data_fixture):
    # A shared view lets a workspace member through on their session alone. A
    # dashboard must not: the owner would open their own protected link, never
    # be asked, and conclude the password does not work. Members still reach
    # the dashboard at /dashboard/<id> without a password.
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    handler = DashboardShareHandler()
    share = handler.set_password(handler.create_share(dashboard), "letmein")

    response = api_client.get(
        public_url(share.slug), **{"HTTP_AUTHORIZATION": f"JWT {token}"}
    )
    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert (
        response.json()["error"]
        == "ERROR_NO_AUTHORIZATION_TO_PUBLICLY_SHARED_DASHBOARD"
    )

    # ... and the token issued for that password still lets them in.
    access_token = handler.encode_token(share)
    response = api_client.get(
        public_url(share.slug),
        **{
            "HTTP_AUTHORIZATION": f"JWT {token}",
            "HTTP_JADAWEL_VIEW_AUTHORIZATION": f"JWT {access_token}",
        },
    )
    assert response.status_code == HTTP_200_OK


@pytest.mark.django_db
def test_password_change_is_rejected_when_the_dashboard_is_not_shared(
    api_client, data_fixture
):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)

    response = api_client.patch(
        password_url(dashboard),
        {"password": "letmein"},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()["error"] == "ERROR_DASHBOARD_SHARE_DOES_NOT_EXIST"


@pytest.mark.django_db
def test_password_body_must_be_present(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    DashboardShareHandler().create_share(dashboard)

    response = api_client.patch(
        password_url(dashboard),
        {},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"


@pytest.mark.django_db
def test_dispatch_refuses_a_data_source_from_another_dashboard(
    api_client, data_fixture
):
    shared = data_fixture.create_dashboard_application()
    other = data_fixture.create_dashboard_application()
    foreign_data_source = (
        data_fixture.create_dashboard_local_jadawel_aggregate_rows_data_source(
            dashboard=other
        )
    )
    slug = DashboardShareHandler().create_share(shared).slug

    response = api_client.post(dispatch_url(slug, foreign_data_source.id))

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()["error"] == "ERROR_DASHBOARD_DATA_SOURCE_DOES_NOT_EXIST"


@pytest.mark.django_db
def test_dispatch_returns_the_aggregation_for_an_anonymous_visitor(
    api_client, data_fixture
):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_number_field(table=table, name="Amount")
    model = table.get_model()
    model.objects.create(**{f"field_{field.id}": 10})
    model.objects.create(**{f"field_{field.id}": 32})

    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    integration = data_fixture.create_local_jadawel_integration(
        application=dashboard, user=user
    )
    data_source = (
        data_fixture.create_dashboard_local_jadawel_aggregate_rows_data_source(
            dashboard=dashboard,
            integration=integration,
            table=table,
            field=field,
            aggregation_type="sum",
        )
    )
    slug = DashboardShareHandler().create_share(dashboard).slug

    response = api_client.post(dispatch_url(slug, data_source.id))

    assert response.status_code == HTTP_200_OK
    # `sum` over a number field comes back as a decimal string.
    assert response.json()["result"] == "42"


@pytest.mark.django_db
def test_dispatch_on_a_password_protected_link_needs_the_token(
    api_client, data_fixture
):
    dashboard = data_fixture.create_dashboard_application()
    data_source = (
        data_fixture.create_dashboard_local_jadawel_aggregate_rows_data_source(
            dashboard=dashboard
        )
    )
    handler = DashboardShareHandler()
    share = handler.set_password(handler.create_share(dashboard), "letmein")

    response = api_client.post(dispatch_url(share.slug, data_source.id))

    assert response.status_code == HTTP_401_UNAUTHORIZED
