from django.db import connection, migrations

# `RenameModel` renames the table but leaves every dependent Postgres object under
# its original auto-generated name, so a database whose tables now read
# `..._localjadawel...` still carries `..._localbaserow...` primary keys, unique
# constraints, check constraints, indexes and sequences. Those names are not purely
# cosmetic: Postgres quotes the constraint name back in every IntegrityError, so a
# duplicate row would surface `..._localbaserow..._pkey` to the caller.
#
# This is true even of a database migrated from zero, because the history still
# replays `CreateModel(name="LocalBaserow...")` before the rename.
#
# The names are discovered rather than hard-coded: the set differs by Postgres
# version and by which optional indexes exist. `localbaserow` and `localjadawel` are
# both twelve characters, so no name can cross the 63-byte identifier limit.

OLD, NEW = "localbaserow", "localjadawel"


def _rename(from_token, to_token):
    with connection.cursor() as cursor:
        # Constraints first: renaming a PK or unique constraint renames its index too,
        # so doing these first keeps the index pass from touching them twice.
        cursor.execute(
            """
            SELECT c.conname, n.nspname, t.relname
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE c.conname LIKE %s AND n.nspname NOT LIKE 'pg_%%'
            """,
            [f"%{from_token}%"],
        )
        for conname, schema, table in cursor.fetchall():
            cursor.execute(
                f'ALTER TABLE "{schema}"."{table}" '
                f'RENAME CONSTRAINT "{conname}" TO "{conname.replace(from_token, to_token)}"'
            )

        # Remaining indexes: those not backing a constraint.
        cursor.execute(
            """
            SELECT n.nspname, c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'i' AND c.relname LIKE %s AND n.nspname NOT LIKE 'pg_%%'
            """,
            [f"%{from_token}%"],
        )
        for schema, index in cursor.fetchall():
            cursor.execute(
                f'ALTER INDEX "{schema}"."{index}" '
                f'RENAME TO "{index.replace(from_token, to_token)}"'
            )

        # Sequences owned by the renamed identity/serial columns.
        cursor.execute(
            """
            SELECT n.nspname, c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'S' AND c.relname LIKE %s AND n.nspname NOT LIKE 'pg_%%'
            """,
            [f"%{from_token}%"],
        )
        for schema, seq in cursor.fetchall():
            cursor.execute(
                f'ALTER SEQUENCE "{schema}"."{seq}" '
                f'RENAME TO "{seq.replace(from_token, to_token)}"'
            )


def forward(apps, schema_editor):
    _rename(OLD, NEW)


def reverse(apps, schema_editor):
    _rename(NEW, OLD)


class Migration(migrations.Migration):
    # Every app that owns a renamed LocalJadawel model must have finished renaming
    # its tables before the dependent objects are swept.
    dependencies = [
        ("integrations", "0029_alter_localjadaweltableservicefieldmapping_service_and_more"),
        ("automation", "0029_jadawel_rename_local_jadawel_models"),
        ("builder", "0068_jadawel_rename_local_jadawel_models"),
        ("arabase", "0003_jadawel_rename_local_jadawel_models"),
    ]

    operations = [migrations.RunPython(forward, reverse)]
