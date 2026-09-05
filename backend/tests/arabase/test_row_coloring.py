"""Row coloring (#29): background decorator fed by single select colors.

The decoration framework itself (model, CRUD, permissions, undo) lives in
core; what is asserted here is the fork's additive surface: our two types
are registered, the API accepts them end to end on a grid view, the
one-per-view rule holds, and bad configurations are rejected with a 400
instead of leaking in or blowing up.
"""

from django.shortcuts import reverse

import pytest
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from arabase.row_coloring.value_providers import SingleSelectColorValueProviderType
from jadawel.contrib.database.views.models import ViewDecoration
from jadawel.contrib.database.views.registries import (
    decorator_type_registry,
    decorator_value_provider_type_registry,
)


def decorations_url(view):
    return reverse("api:database:views:list_decorations", kwargs={"view_id": view.id})


def decoration_url(decoration):
    return reverse(
        "api:database:views:decoration_item",
        kwargs={"view_decoration_id": decoration.id},
    )


@pytest.fixture
def coloring_setup(data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    view = data_fixture.create_grid_view(table=table)
    status = data_fixture.create_single_select_field(table=table, name="Status")
    data_fixture.create_select_option(field=status, value="Open", color="blue")
    text = data_fixture.create_text_field(table=table, name="Notes")
    other_table = data_fixture.create_database_table(user=user)
    foreign = data_fixture.create_single_select_field(table=other_table, name="Other")
    return {
        "user": user,
        "token": token,
        "table": table,
        "view": view,
        "status": status,
        "text": text,
        "foreign": foreign,
    }


def auth(token):
    return {"HTTP_AUTHORIZATION": f"JWT {token}"}


@pytest.mark.django_db
def test_row_coloring_types_are_registered():
    assert decorator_type_registry.get("background_color").type == "background_color"
    provider = decorator_value_provider_type_registry.get("single_select_color")
    assert isinstance(provider, SingleSelectColorValueProviderType)
    assert provider.decorator_is_compatible(
        decorator_type_registry.get("background_color")
    )


@pytest.mark.django_db
def test_create_background_color_from_single_select(
    api_client, data_fixture, coloring_setup
):
    setup = coloring_setup
    response = api_client.post(
        decorations_url(setup["view"]),
        {
            "type": "background_color",
            "value_provider_type": "single_select_color",
            "value_provider_conf": {"field_id": setup["status"].id},
        },
        format="json",
        **auth(setup["token"]),
    )
    assert response.status_code == HTTP_200_OK, response.content
    body = response.json()
    assert body["type"] == "background_color"
    assert body["value_provider_type"] == "single_select_color"
    assert body["value_provider_conf"] == {"field_id": setup["status"].id}
    assert ViewDecoration.objects.filter(view=setup["view"]).count() == 1


@pytest.mark.django_db
def test_second_background_color_is_rejected(api_client, data_fixture, coloring_setup):
    setup = coloring_setup
    payload = {
        "type": "background_color",
        "value_provider_type": "single_select_color",
        "value_provider_conf": {"field_id": setup["status"].id},
    }
    first = api_client.post(
        decorations_url(setup["view"]), payload, format="json", **auth(setup["token"])
    )
    assert first.status_code == HTTP_200_OK, first.content

    second = api_client.post(
        decorations_url(setup["view"]), payload, format="json", **auth(setup["token"])
    )
    assert second.status_code == HTTP_400_BAD_REQUEST
    assert second.json()["error"] == "ERROR_VIEW_DECORATION_NOT_SUPPORTED"


@pytest.mark.django_db
def test_conf_must_reference_a_field(api_client, data_fixture, coloring_setup):
    setup = coloring_setup
    response = api_client.post(
        decorations_url(setup["view"]),
        {
            "type": "background_color",
            "value_provider_type": "single_select_color",
            "value_provider_conf": {},
        },
        format="json",
        **auth(setup["token"]),
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"


@pytest.mark.django_db
def test_update_conf_shape_is_validated(api_client, data_fixture, coloring_setup):
    setup = coloring_setup
    created = api_client.post(
        decorations_url(setup["view"]),
        {
            "type": "background_color",
            "value_provider_type": "single_select_color",
            "value_provider_conf": {"field_id": setup["status"].id},
        },
        format="json",
        **auth(setup["token"]),
    )
    assert created.status_code == HTTP_200_OK, created.content
    decoration = ViewDecoration.objects.get(pk=created.json()["id"])

    response = api_client.patch(
        decoration_url(decoration),
        {"value_provider_conf": {}},
        format="json",
        **auth(setup["token"]),
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"


@pytest.mark.django_db
def test_type_change_away_from_single_select_cleans_up(data_fixture, coloring_setup):
    from jadawel.contrib.database.fields.handler import FieldHandler

    setup = coloring_setup
    decoration = ViewDecoration.objects.create(
        view=setup["view"],
        type="background_color",
        value_provider_type="single_select_color",
        value_provider_conf={"field_id": setup["status"].id},
        order=1,
    )
    FieldHandler().update_field(
        user=setup["user"],
        table=setup["table"],
        field=setup["status"],
        new_type_name="text",
        name="Status",
    )
    assert not ViewDecoration.objects.filter(pk=decoration.pk).exists()


@pytest.mark.django_db
def test_validate_conf_for_view_rejects_bad_fields(coloring_setup):
    from arabase.row_coloring.value_providers import get_single_select_field_or_raise
    from jadawel.contrib.database.views.exceptions import (
        DecoratorValueProviderTypeNotCompatible,
    )

    setup = coloring_setup
    field = get_single_select_field_or_raise(
        setup["view"], {"field_id": setup["status"].id}
    )
    assert field.id == setup["status"].id
    for bad_conf in (
        {},
        {"field_id": setup["text"].id},
        {"field_id": setup["foreign"].id},
        {"field_id": 999999},
    ):
        with pytest.raises(DecoratorValueProviderTypeNotCompatible):
            get_single_select_field_or_raise(setup["view"], bad_conf)


@pytest.mark.django_db
def test_field_delete_cleans_up_decorations(data_fixture, coloring_setup):
    from jadawel.contrib.database.fields.handler import FieldHandler

    setup = coloring_setup
    decoration = ViewDecoration.objects.create(
        view=setup["view"],
        type="background_color",
        value_provider_type="single_select_color",
        value_provider_conf={"field_id": setup["status"].id},
        order=1,
    )
    FieldHandler().delete_field(setup["user"], setup["status"])
    assert not ViewDecoration.objects.filter(pk=decoration.pk).exists()


@pytest.mark.django_db
def test_import_remaps_field_id(coloring_setup):
    provider = decorator_value_provider_type_registry.get("single_select_color")
    value = {
        "type": "background_color",
        "value_provider_type": "single_select_color",
        "value_provider_conf": {"field_id": 41},
        "order": 1,
    }
    remapped = provider.set_import_serialized_value(
        value, {"database_fields": {41: 77}}
    )
    assert remapped["value_provider_conf"] == {"field_id": 77}

    dropped = provider.set_import_serialized_value(dict(value), {"database_fields": {}})
    assert dropped["value_provider_conf"] == {"field_id": None}
