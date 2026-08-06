import json
from unittest.mock import patch

from django.db import connection

import pytest

from jadawel.core.formula import BaserowFormulaObject
from jadawel.core.formula.field import JADAWEL_FORMULA_VERSION_INITIAL
from jadawel.core.formula.types import (
    JADAWEL_FORMULA_MODE_SIMPLE,
    BaserowFormulaMinified,
)


def get_raw_table_value(field_name, table_name, pk) -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {field_name} FROM {table_name} WHERE service_ptr_id = %s",
            [pk],
        )
        return cursor.fetchone()[0]


@pytest.mark.django_db
@patch("jadawel.core.formula.field.FormulaField.db_type", return_value="text")
def test_create_text_formula_field_value(mock_db_type, data_fixture):
    # Create a service with a raw formula string.
    service = data_fixture.create_core_http_request_service(url="'http://google.com'")
    assert service.url == BaserowFormulaObject(
        formula="'http://google.com'",
        mode=JADAWEL_FORMULA_MODE_SIMPLE,
        version=JADAWEL_FORMULA_VERSION_INITIAL,
    )
    raw_url = get_raw_table_value("url", service._meta.db_table, service.id)
    assert json.loads(raw_url) == BaserowFormulaMinified(
        f="'http://google.com'",
        m=JADAWEL_FORMULA_MODE_SIMPLE,
        v=JADAWEL_FORMULA_VERSION_INITIAL,
    )

    # Create a service with a formula context.
    service = data_fixture.create_core_http_request_service(
        url=BaserowFormulaObject(
            mode=JADAWEL_FORMULA_MODE_SIMPLE,
            version=JADAWEL_FORMULA_VERSION_INITIAL,
            formula="'http://google.com'",
        )
    )
    assert service.url == BaserowFormulaObject(
        formula="'http://google.com'",
        mode=JADAWEL_FORMULA_MODE_SIMPLE,
        version=JADAWEL_FORMULA_VERSION_INITIAL,
    )
    raw_url = get_raw_table_value("url", service._meta.db_table, service.id)
    assert json.loads(raw_url) == BaserowFormulaMinified(
        f="'http://google.com'",
        m=JADAWEL_FORMULA_MODE_SIMPLE,
        v=JADAWEL_FORMULA_VERSION_INITIAL,
    )


@pytest.mark.django_db
@patch("jadawel.core.formula.field.FormulaField.db_type", return_value="text")
def test_update_text_formula_field_value(mock_db_type, data_fixture):
    # Update a service with a raw formula string.
    service = data_fixture.create_core_http_request_service()
    service.url = "'http://google.com'"
    service.save()
    assert service.url == BaserowFormulaObject(
        formula="'http://google.com'",
        mode=JADAWEL_FORMULA_MODE_SIMPLE,
        version=JADAWEL_FORMULA_VERSION_INITIAL,
    )
    raw_url = get_raw_table_value("url", service._meta.db_table, service.id)
    assert json.loads(raw_url) == BaserowFormulaMinified(
        f="'http://google.com'",
        m=JADAWEL_FORMULA_MODE_SIMPLE,
        v=JADAWEL_FORMULA_VERSION_INITIAL,
    )

    # Update a service with a formula context.
    service = data_fixture.create_core_http_request_service()
    service.url = BaserowFormulaObject(
        formula="'http://google.com'",
        mode=JADAWEL_FORMULA_MODE_SIMPLE,
        version=JADAWEL_FORMULA_VERSION_INITIAL,
    )
    service.save()
    assert service.url == BaserowFormulaObject(
        formula="'http://google.com'",
        mode=JADAWEL_FORMULA_MODE_SIMPLE,
        version=JADAWEL_FORMULA_VERSION_INITIAL,
    )
    raw_url = get_raw_table_value("url", service._meta.db_table, service.id)
    assert json.loads(raw_url) == BaserowFormulaMinified(
        f="'http://google.com'",
        m=JADAWEL_FORMULA_MODE_SIMPLE,
        v=JADAWEL_FORMULA_VERSION_INITIAL,
    )
