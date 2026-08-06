from django.db import connection, migrations

# Renames the three Postgres functions introduced in 0151 from get_baserow_* to
# get_jadawel_*. They are plain functions with no dependent objects, so each is
# recreated under the new name and the old one dropped.
#
# 0151's reverse() drops "get_baserow_table_file_uniques", a name it never
# created (it creates "get_distinct_baserow_table_file_uniques"). That
# historical file is left as written; the names below are the ones that are
# actually in the database.

ROW_COUNT = """
CREATE OR REPLACE FUNCTION get_jadawel_table_row_count(table_id INT) RETURNS BIGINT AS $$
DECLARE
    row_count BIGINT;
BEGIN
    BEGIN
        EXECUTE 'SELECT COUNT(*) FROM database_table_' || table_id || ' WHERE trashed=false;' INTO row_count;
        RETURN row_count;
    EXCEPTION WHEN OTHERS THEN
        return null;
    END;
end;
$$
LANGUAGE plpgsql;
"""

FILE_UNIQUES_QUERY = """
CREATE OR REPLACE FUNCTION _get_jadawel_table_file_uniques(table__id INT) RETURNS TABLE(file_unique TEXT, field_id INT, table_id INT) AS $$
DECLARE
    field RECORD;
    filename TEXT;
BEGIN
FOR field IN EXECUTE 'SELECT * FROM database_field JOIN database_filefield ON id=field_ptr_id WHERE trashed=false AND table_id=' || table__id || ';'
LOOP
    BEGIN
        RETURN QUERY EXECUTE 'SELECT SPLIT_PART(JSONB_ARRAY_ELEMENTS(field_' || field.id || ') ->> ''name'', ''_'', 1), ' || field.id || ', ' || field.table_id || ' FROM database_table_' || field.table_id;
    EXCEPTION
        WHEN undefined_table THEN
            RAISE NOTICE 'Could not find database_table_%', field.table_id;
        WHEN undefined_column THEN
            RAISE NOTICE 'Could not find field_% in database_table_%', field.id, field.table_id;
    END;
END LOOP;
END;
$$
LANGUAGE plpgsql;
"""

FILE_UNIQUES = """
CREATE OR REPLACE FUNCTION get_distinct_jadawel_table_file_uniques(table_id INT) RETURNS TEXT[] AS $$
DECLARE
    file_uniques TEXT[];
BEGIN
    BEGIN
        EXECUTE 'SELECT array_agg(distinct file_unique) from _get_jadawel_table_file_uniques(' || table_id || ');' into file_uniques;
        return file_uniques;
    EXCEPTION WHEN OTHERS THEN
        return null;
    END;
END;
$$
LANGUAGE plpgsql;
"""

DROP_OLD = [
    "DROP FUNCTION IF EXISTS get_baserow_table_row_count(INT)",
    "DROP FUNCTION IF EXISTS get_distinct_baserow_table_file_uniques(INT)",
    "DROP FUNCTION IF EXISTS _get_baserow_table_file_uniques(INT)",
]
DROP_NEW = [
    "DROP FUNCTION IF EXISTS get_jadawel_table_row_count(INT)",
    "DROP FUNCTION IF EXISTS get_distinct_jadawel_table_file_uniques(INT)",
    "DROP FUNCTION IF EXISTS _get_jadawel_table_file_uniques(INT)",
]


def forward(apps, schema_editor):
    with connection.cursor() as cursor:
        for statement in (ROW_COUNT, FILE_UNIQUES_QUERY, FILE_UNIQUES):
            cursor.execute(statement)
        for statement in DROP_OLD:
            cursor.execute(statement)


def reverse(apps, schema_editor):
    old_row_count = ROW_COUNT.replace(
        "get_jadawel_table_row_count", "get_baserow_table_row_count"
    )
    old_query = FILE_UNIQUES_QUERY.replace(
        "_get_jadawel_table_file_uniques", "_get_baserow_table_file_uniques"
    )
    old_uniques = FILE_UNIQUES.replace(
        "get_distinct_jadawel_table_file_uniques",
        "get_distinct_baserow_table_file_uniques",
    ).replace("_get_jadawel_table_file_uniques", "_get_baserow_table_file_uniques")
    with connection.cursor() as cursor:
        for statement in (old_row_count, old_query, old_uniques):
            cursor.execute(statement)
        for statement in DROP_NEW:
            cursor.execute(statement)


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0210_jadawel_rename_default_grid_views"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
