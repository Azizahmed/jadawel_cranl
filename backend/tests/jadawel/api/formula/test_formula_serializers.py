import pytest
from rest_framework.exceptions import ValidationError

from jadawel.core.formula.field import JADAWEL_FORMULA_VERSION_INITIAL
from jadawel.core.formula.serializers import FormulaSerializerField
from jadawel.core.formula.types import JADAWEL_FORMULA_MODE_SIMPLE


@pytest.mark.parametrize("context", [None, {}, {"application_type": None}])
def test_formula_serializer_field_without_context(context):
    with pytest.raises(ValidationError) as exc:
        field = FormulaSerializerField()
        field._context = context
        field.to_internal_value(
            {
                "formula": "get('data_source.123.field_456')",
                "version": JADAWEL_FORMULA_VERSION_INITIAL,
                "mode": JADAWEL_FORMULA_MODE_SIMPLE,
            }
        )
    assert str(exc.value.detail[0]) == (
        "The formula serializer field requires "
        "an application type context to validate the formula arguments."
    )
