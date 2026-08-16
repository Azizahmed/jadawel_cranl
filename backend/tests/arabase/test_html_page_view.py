"""The HTML page view.

The page renders an untrusted document — written by an AI over MCP, or by
anyone who can edit the view — so most of what is worth asserting here is about
containment rather than about rendering: that the policy handed to the client
never lets the page phone home, that the public feed still respects the view's
password, and that the document survives the paths that quietly drop data
(duplicating a view, exporting a database).
"""

from django.shortcuts import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)

from arabase.views.constants import MAX_HTML_LENGTH, MAX_ROW_LIMIT
from arabase.views.csp import build_page_csp
from arabase.views.models import HtmlPageView, HtmlPageViewFieldOptions
from arabase.views.view_types import HtmlPageViewType
from jadawel.contrib.database.views.handler import ViewHandler
from jadawel.contrib.database.views.registries import view_type_registry
from jadawel.core.registries import ImportExportConfig

SIMPLE_PAGE = "<!doctype html><html><head></head><body><h1>Report</h1></body></html>"


def rows_url(view):
    return reverse("api:database:views:html_page:list", kwargs={"view_id": view.id})


def public_rows_url(view):
    return reverse(
        "api:database:views:html_page:public_rows", kwargs={"slug": view.slug}
    )


def public_info_url(view):
    return reverse("api:database:views:public_info", kwargs={"slug": view.slug})


def create_page_view(data_fixture, user, **kwargs):
    table = kwargs.pop("table", None)
    if table is None:
        workspace = data_fixture.create_workspace(user=user)
        database = data_fixture.create_database_application(workspace=workspace)
        table = data_fixture.create_database_table(database=database)
    return (
        table,
        ViewHandler().create_view(
            user, table, HtmlPageViewType.type, name="Page", **kwargs
        ),
    )


# ---------------------------------------------------------------------------
# Content security policy
# ---------------------------------------------------------------------------


def test_strict_policy_seals_off_the_network():
    csp = build_page_csp(allow_external_resources=False)

    assert "default-src 'none'" in csp
    assert "connect-src 'none'" in csp
    assert "form-action 'none'" in csp
    assert "frame-src 'none'" in csp
    assert "base-uri 'none'" in csp
    # No remote origin of any kind is reachable in the default mode.
    assert "https:" not in csp


def test_relaxed_policy_still_cannot_send_data_out():
    csp = build_page_csp(allow_external_resources=True)

    # The opt-in buys CDN assets...
    assert "https://cdn.jsdelivr.net" in csp
    # ...and never buys a way to POST the rows anywhere. This is the whole
    # reason the toggle is safe enough to offer at all.
    assert "connect-src 'none'" in csp
    assert "form-action 'none'" in csp


def test_external_hosts_are_configurable(monkeypatch):
    monkeypatch.setenv("JADAWEL_PAGE_VIEW_EXTERNAL_HOSTS", "https://cdn.example.com")

    csp = build_page_csp(allow_external_resources=True)

    assert "https://cdn.example.com" in csp
    assert "https://cdn.jsdelivr.net" not in csp


@pytest.mark.django_db
def test_the_policy_travels_with_the_view(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    _, view = create_page_view(data_fixture, user, html=SIMPLE_PAGE)

    response = api_client.get(
        reverse("api:database:views:item", kwargs={"view_id": view.id}),
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert body["html"] == SIMPLE_PAGE
    # The client must not be left to compose the policy itself.
    assert "connect-src 'none'" in body["content_security_policy"]


@pytest.mark.django_db
def test_the_policy_is_not_writable_through_the_api(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    _, view = create_page_view(data_fixture, user)

    response = api_client.patch(
        reverse("api:database:views:item", kwargs={"view_id": view.id}),
        {"content_security_policy": "default-src *"},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )

    assert response.status_code == HTTP_200_OK
    assert "connect-src 'none'" in response.json()["content_security_policy"]


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_oversized_html_is_rejected(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    _, view = create_page_view(data_fixture, user)

    response = api_client.patch(
        reverse("api:database:views:item", kwargs={"view_id": view.id}),
        {"html": "x" * (MAX_HTML_LENGTH + 1)},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_HTML_PAGE_TOO_LARGE"


@pytest.mark.django_db
def test_row_limit_is_clamped_rather_than_rejected(data_fixture):
    user = data_fixture.create_user()
    _, view = create_page_view(data_fixture, user)

    ViewHandler().update_view(user, view, row_limit=99999)
    view.refresh_from_db()
    assert view.row_limit == MAX_ROW_LIMIT

    ViewHandler().update_view(user, view, row_limit=0)
    view.refresh_from_db()
    assert view.row_limit == 1


@pytest.mark.django_db
def test_the_feed_stops_at_the_row_limit(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table, view = create_page_view(data_fixture, user, row_limit=2)
    data_fixture.create_text_field(table=table, name="Name")
    model = table.get_model()
    for index in range(5):
        model.objects.create(order=index)

    response = api_client.get(rows_url(view), **{"HTTP_AUTHORIZATION": f"JWT {token}"})

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert len(body["results"]) == 2
    # The author has to be able to tell a complete page from a partial one.
    assert body["count"] == 5
    assert body["truncated"] is True


# ---------------------------------------------------------------------------
# Fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_new_page_starts_with_every_field_in_the_feed(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    visible = data_fixture.create_text_field(table=table, name="Visible")
    hidden = data_fixture.create_text_field(table=table, name="Hidden")

    _, view = create_page_view(data_fixture, user, table=table)

    view_type = view_type_registry.get(HtmlPageViewType.type)
    assert view_type.get_hidden_fields(view) == set()

    HtmlPageViewFieldOptions.objects.filter(html_page_view=view, field=hidden).update(
        hidden=True
    )

    assert view_type.get_hidden_fields(view) == {hidden.id}
    field_ids = [
        option.field_id for option in view_type.get_visible_field_options_in_order(view)
    ]
    assert visible.id in field_ids
    assert hidden.id not in field_ids


@pytest.mark.django_db
def test_a_field_added_to_a_shared_page_does_not_go_public_on_its_own(data_fixture):
    """Core's caution, kept rather than overridden.

    Unhiding happens once, when the page is created. A column added afterwards
    to an already-shared page stays out of the feed until someone reveals it.
    """

    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    data_fixture.create_text_field(table=table, name="Original")

    _, view = create_page_view(data_fixture, user, table=table)
    ViewHandler().update_view(user, view, public=True)
    view.refresh_from_db()

    added_later = data_fixture.create_text_field(table=table, name="Salary")

    view_type = view_type_registry.get(HtmlPageViewType.type)
    view.get_field_options(create_if_missing=True)
    assert added_later.id in view_type.get_hidden_fields(view)


# ---------------------------------------------------------------------------
# Public sharing
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_shared_page_serves_its_html_and_rows(api_client, data_fixture):
    user = data_fixture.create_user()
    table, view = create_page_view(data_fixture, user, html=SIMPLE_PAGE)
    data_fixture.create_text_field(table=table, name="Name")
    table.get_model().objects.create(order=1)
    ViewHandler().update_view(user, view, public=True)

    info = api_client.get(public_info_url(view))
    assert info.status_code == HTTP_200_OK
    assert info.json()["view"]["html"] == SIMPLE_PAGE

    rows = api_client.get(public_rows_url(view))
    assert rows.status_code == HTTP_200_OK
    assert rows.json()["count"] == 1


@pytest.mark.django_db
def test_a_password_gates_the_public_feed(api_client, data_fixture):
    user = data_fixture.create_user()
    table, view = create_page_view(data_fixture, user, html=SIMPLE_PAGE)
    table.get_model().objects.create(order=1)
    ViewHandler().update_view(user, view, public=True)
    view.set_password("supersecret")
    view.save()

    # Holding the link is not enough on its own.
    assert api_client.get(public_rows_url(view)).status_code == HTTP_401_UNAUTHORIZED
    assert api_client.get(public_info_url(view)).status_code == HTTP_401_UNAUTHORIZED

    token = ViewHandler().encode_public_view_token(view)
    authorized = api_client.get(
        public_rows_url(view),
        **{"HTTP_JADAWEL_VIEW_AUTHORIZATION": f"JWT {token}"},
    )
    assert authorized.status_code == HTTP_200_OK
    assert authorized.json()["count"] == 1


@pytest.mark.django_db
def test_an_unshared_page_is_not_reachable_by_slug(api_client, data_fixture):
    user = data_fixture.create_user()
    _, view = create_page_view(data_fixture, user, html=SIMPLE_PAGE)

    assert api_client.get(public_rows_url(view)).status_code == HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_a_hidden_field_stays_out_of_the_public_feed(api_client, data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    visible = data_fixture.create_text_field(table=table, name="Visible")
    hidden = data_fixture.create_text_field(table=table, name="Hidden")
    _, view = create_page_view(data_fixture, user, table=table, html=SIMPLE_PAGE)

    model = table.get_model()
    model.objects.create(
        order=1,
        **{f"field_{visible.id}": "shown", f"field_{hidden.id}": "secret"},
    )
    HtmlPageViewFieldOptions.objects.filter(html_page_view=view, field=hidden).update(
        hidden=True
    )
    ViewHandler().update_view(user, view, public=True)

    response = api_client.get(public_rows_url(view))

    assert response.status_code == HTTP_200_OK
    row = response.json()["results"][0]
    assert row[f"field_{visible.id}"] == "shown"
    assert f"field_{hidden.id}" not in row


# ---------------------------------------------------------------------------
# Export / import
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_document_survives_an_export_import_round_trip(data_fixture):
    user = data_fixture.create_user()
    table, view = create_page_view(
        data_fixture, user, html=SIMPLE_PAGE, allow_external_resources=True
    )
    field = data_fixture.create_text_field(table=table, name="Name")
    HtmlPageViewFieldOptions.objects.update_or_create(
        html_page_view=view, field=field, defaults={"hidden": True, "order": 3}
    )

    view_type = view_type_registry.get(HtmlPageViewType.type)
    config = ImportExportConfig(include_permission_data=False)
    serialized = view_type.export_serialized(view, config, cache={})

    assert serialized["html"] == SIMPLE_PAGE
    assert serialized["allow_external_resources"] is True

    imported = view_type.import_serialized(
        table,
        serialized,
        config,
        id_mapping={"database_fields": {field.id: field.id}},
        cache={},
    )

    assert imported.html == SIMPLE_PAGE
    assert imported.allow_external_resources is True
    option = HtmlPageViewFieldOptions.objects.get(html_page_view=imported, field=field)
    assert option.hidden is True
    assert option.order == 3


@pytest.mark.django_db
def test_duplicating_a_page_keeps_its_html(data_fixture):
    user = data_fixture.create_user()
    _, view = create_page_view(data_fixture, user, html=SIMPLE_PAGE)

    duplicate = ViewHandler().duplicate_view(user, view)

    assert HtmlPageView.objects.get(id=duplicate.id).html == SIMPLE_PAGE
