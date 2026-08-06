from typing import Dict, List, Type, Union

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from jadawel.core.exceptions import InstanceTypeDoesNotExist
from jadawel.core.formula.field import JADAWEL_FORMULA_VERSION_INITIAL
from jadawel.core.formula.parser.exceptions import (
    InvalidNumberOfArguments,
    JadawelFormulaSyntaxError,
)
from jadawel.core.formula.parser.formula_validation_visitor import (
    JadawelFormulaValidationVisitor,
)
from jadawel.core.formula.parser.parser import get_parse_tree_for_formula
from jadawel.core.formula.registries import formula_runtime_function_registry
from jadawel.core.formula.types import (
    JADAWEL_FORMULA_MODE_ADVANCED,
    JADAWEL_FORMULA_MODE_RAW,
    JADAWEL_FORMULA_MODE_SIMPLE,
    JadawelFormulaObject,
)
from jadawel.core.registry import Registry


def collect_json_formula_field_properties(registry: Type[Registry]) -> List[str]:
    """
    Returns a list of all the properties in the serializers of the given registry that
    are of type FormulaSerializerField. This is used by the `JSONFormulaField` to
    know which properties to parse for formulas when writing or reading to/from the
    database.

    :param registry: The registry to get the serializers from.
    :return: A list of property names. If a property is nested, it will be in the
        format "property.child", otherwise just "property".
    """

    properties: List[str] = []
    for instance in registry.get_all():
        serializer = instance.get_serializer_class()
        for field_name, field in serializer().get_fields().items():
            child = getattr(field, "child", None)
            if isinstance(field, FormulaSerializerField):
                properties.append(field_name)
            elif child is not None:
                for child_name, child_field in child.get_fields().items():
                    if isinstance(child_field, FormulaSerializerField):
                        properties.append(f"{field_name}.{child_name}")

    return list(set(properties))


class JadawelFormulaObjectSerializer(serializers.Serializer):
    formula = serializers.CharField(required=True, allow_blank=True)
    version = serializers.CharField(
        required=False, default=JADAWEL_FORMULA_VERSION_INITIAL
    )
    mode = serializers.ChoiceField(
        required=False,
        default=JADAWEL_FORMULA_MODE_SIMPLE,
        choices=[
            JADAWEL_FORMULA_MODE_SIMPLE,
            JADAWEL_FORMULA_MODE_ADVANCED,
            JADAWEL_FORMULA_MODE_RAW,
        ],
    )


@extend_schema_field(OpenApiTypes.OBJECT)
class FormulaSerializerField(serializers.JSONField):
    """
    This field can be used to store a formula in the database.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.required = False
        self.default = JadawelFormulaObject(
            formula="",
            version=JADAWEL_FORMULA_VERSION_INITIAL,
            mode=JADAWEL_FORMULA_MODE_SIMPLE,
        )

    def to_internal_value(self, data: Union[str, Dict[str, str]]):
        data = super().to_internal_value(data)

        # The formula serializer does not require a value, but if this
        # value is a blank string or object, we need to construct the
        # default value.
        if not data:
            data = self.default

        # For compatibility reasons: we have a value, but if it's not
        # a dict, we expect it to be a string. For example: if we receive
        # a `row_id` formula of 5, an integer, we need to convert it to
        # a string.
        if not isinstance(data, dict):
            data = str(data)
        else:
            # It's a dictionary, so validate its structure.
            bfo_serializer = JadawelFormulaObjectSerializer(data=data)
            bfo_serializer.is_valid(raise_exception=True)
            data = bfo_serializer.validated_data

        # For compatibility reasons: if we receive a string, we will
        # construct a JadawelFormulaObject with it, and assume the
        # mode is 'simple', and the version is the initial version.
        # TODO: we should infer the `mode` differently, once we know
        #   what an advanced/raw formula looks like. Or: just force the
        #   user to tell us?
        if isinstance(data, str):
            data = JadawelFormulaObject(
                formula=data,
                version=JADAWEL_FORMULA_VERSION_INITIAL,
                mode=JADAWEL_FORMULA_MODE_SIMPLE,
            )

        if not data["formula"] or data["mode"] == JADAWEL_FORMULA_MODE_RAW:
            return data

        # Inspect the `context` for an `ApplicationType`, we'll need to
        # determine what this application type's data provider registry is,
        # so we can validate the formula
        context = self.context or {}
        if context.get("application_type") is None:
            raise ValidationError(
                "The formula serializer field requires an application type "
                "context to validate the formula arguments.",
                code="missing_context",
            )

        try:
            tree = get_parse_tree_for_formula(data["formula"])
            try:
                JadawelFormulaValidationVisitor(
                    formula_runtime_function_registry,
                    data_provider_type_registry=self.context.get(
                        "application_type"
                    )().data_provider_type_registry,
                ).visit(tree)
            except (
                JadawelFormulaSyntaxError,
                InvalidNumberOfArguments,
                InstanceTypeDoesNotExist,
            ) as exc:
                raise ValidationError(
                    exc.args[0],
                    code="invalid_formula_argument",
                ) from exc
            return data
        except JadawelFormulaSyntaxError as e:
            raise ValidationError(f"The formula is invalid: {e}", code="invalid")
