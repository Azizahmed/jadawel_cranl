"""
Test the RatingCollectionFieldType class.
"""

import pytest

from jadawel.contrib.builder.elements.registries import element_type_registry
from jadawel.contrib.builder.pages.service import PageService
from jadawel.core.formula import JadawelFormulaObject
from jadawel.core.formula.field import JADAWEL_FORMULA_VERSION_INITIAL
from jadawel.core.formula.types import JADAWEL_FORMULA_MODE_SIMPLE


@pytest.mark.django_db
def test_import_export_rating_collection_field_type(data_fixture):
    """
    Ensure that the RatingCollectionField's formulas are exported correctly
    with the updated Data Sources.
    """

    user, _ = data_fixture.create_user_and_token()
    page = data_fixture.create_builder_page(user=user)
    table, fields, _ = data_fixture.build_table(
        user=user,
        columns=[
            ("Rating", "rating"),
        ],
        rows=[
            [3],
        ],
    )
    rating_field = fields[0]
    data_source = data_fixture.create_builder_local_baserow_list_rows_data_source(
        table=table, page=page
    )
    table_element = data_fixture.create_builder_table_element(
        page=page,
        data_source=data_source,
        fields=[
            {
                "name": "Rating Field",
                "type": "rating",
                "config": {
                    "value": JadawelFormulaObject(
                        formula=f"get('data_source.{data_source.id}.0.{rating_field.db_column}')",
                        version=JADAWEL_FORMULA_VERSION_INITIAL,
                        mode=JADAWEL_FORMULA_MODE_SIMPLE,
                    ),
                    "max_value": 5,
                    "rating_style": "star",
                    "color": "",
                },
            },
        ],
    )

    # Create a duplicate page to get a new data source
    duplicated_page = PageService().duplicate_page(user, page)
    data_source2 = duplicated_page.datasource_set.first()

    # Create ID mapping for the data sources
    id_mapping = {"builder_data_sources": {data_source.id: data_source2.id}}

    # Export the element
    serialized = element_type_registry.get_by_model(table_element).export_serialized(
        table_element
    )

    # Delete the element
    table_element.delete()

    # Import it back
    imported_element = element_type_registry.get_by_model(
        table_element
    ).import_serialized(
        page,
        serialized,
        id_mapping,
        None,
    )

    # The imported element should have the same field configuration
    # with updated data source ID
    imported_field = imported_element.fields.get(name="Rating Field")
    assert imported_field.config == {
        "value": JadawelFormulaObject(
            formula=f"get('data_source.{data_source2.id}.0.{rating_field.db_column}')",
            version=JADAWEL_FORMULA_VERSION_INITIAL,
            mode=JADAWEL_FORMULA_MODE_SIMPLE,
        ),
        "max_value": 5,
        "rating_style": "star",
        "color": "",
    }
