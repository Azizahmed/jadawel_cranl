from typing import Any, Dict, Union

from rest_framework import serializers

from jadawel.contrib.database.fields.models import Field
from jadawel.contrib.database.fields.registries import field_type_registry
from jadawel.contrib.database.views.exceptions import (
    DecoratorValueProviderTypeNotCompatible,
)
from jadawel.contrib.database.views.models import ViewDecoration
from jadawel.contrib.database.views.registries import DecoratorValueProviderType

SINGLE_SELECT_FIELD_TYPE = "single_select"


class SingleSelectColorConfSerializer(serializers.Serializer):
    field_id = serializers.IntegerField(required=True)


def get_single_select_field_or_raise(view, conf) -> Field:
    """Resolve and validate the configured field for a view.

    Raises the compatibility error (mapped to 400 on both the create and
    update decoration endpoints) when the configuration points at a field
    that does not exist, lives on another table, or is not a single select.
    """
    field_id = (conf or {}).get("field_id")
    try:
        field = Field.objects.select_related("table").get(pk=field_id)
    except (Field.DoesNotExist, TypeError, ValueError):
        raise DecoratorValueProviderTypeNotCompatible(
            "The single select color configuration must reference a field."
        )
    if field.table_id != view.table_id:
        raise DecoratorValueProviderTypeNotCompatible(
            "The coloring field must belong to the view's table."
        )
    if (
        field_type_registry.get_by_model(field.specific_class).type
        != SINGLE_SELECT_FIELD_TYPE
    ):
        raise DecoratorValueProviderTypeNotCompatible(
            "Row coloring by option only supports single select fields."
        )
    return field


class SingleSelectColorValueProviderType(DecoratorValueProviderType):
    """Colors a row from the color of its single select option.

    OSS re-implementation of upstream's premium `single_select_color`
    provider. The configuration is `{"field_id": <id>}` — the same shape
    upstream used (see the Airtable import mapping) — and the color itself
    is resolved client-side from the already-loaded row value, so no extra
    query is needed per row.

    Note: core's create/update hooks receive the view but not the incoming
    configuration, so shape validation lives in the conf serializer above
    while field semantics are enforced when a stored configuration is
    adopted (update) and via the field lifecycle hooks below. A stale
    reference stays inert client-side: rows simply get no color.
    """

    type = "single_select_color"
    compatible_decorator_types = ["background_color"]
    value_provider_conf_serializer_class = SingleSelectColorConfSerializer

    def before_update_decoration(self, view_decoration, user):
        conf = view_decoration.value_provider_conf or {}
        if not conf:
            return
        get_single_select_field_or_raise(view_decoration.view, conf)

    def set_import_serialized_value(
        self, value: Dict[str, Any], id_mapping: Dict[str, Dict[int, Any]]
    ) -> Dict[str, Any]:
        conf = value.get("value_provider_conf") or {}
        old_field_id = conf.get("field_id")
        new_field_id = id_mapping.get("database_fields", {}).get(old_field_id)
        # A field that was not imported must not keep pointing at a stale id
        # that could belong to another field in the target workspace.
        conf["field_id"] = new_field_id
        value["value_provider_conf"] = conf
        return value

    def _delete_decorations_for_field(self, field: Field):
        ViewDecoration.objects.filter(
            value_provider_type=self.type,
            view__table_id=field.table_id,
            value_provider_conf__field_id=field.id,
        ).delete()

    def after_field_delete(self, deleted_field: Field):
        self._delete_decorations_for_field(deleted_field)

    def after_fields_type_change(self, fields):
        for field in fields:
            if (
                field_type_registry.get_by_model(field.specific_class).type
                != SINGLE_SELECT_FIELD_TYPE
            ):
                self._delete_decorations_for_field(field)

    def validate_conf_for_view(self, view, conf) -> Union[Field, None]:
        """Public entry point used by tests and future callers."""
        if not conf:
            return None
        return get_single_select_field_or_raise(view, conf)
