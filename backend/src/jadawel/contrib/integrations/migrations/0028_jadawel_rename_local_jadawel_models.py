from django.db import migrations

# Renames the LocalBaserow* models to LocalJadawel*. Each pair differs only by
# that token, so the rename is 1:1 and RenameModel renames the table in place
# rather than dropping and recreating it.


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0027_coresmtpemailservice_use_instance_smtp_settings"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="LocalBaserowAggregateRows",
            new_name="LocalJadawelAggregateRows",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowDeleteRow",
            new_name="LocalJadawelDeleteRow",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowGetRow",
            new_name="LocalJadawelGetRow",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowIntegration",
            new_name="LocalJadawelIntegration",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowListRows",
            new_name="LocalJadawelListRows",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowRowsCreated",
            new_name="LocalJadawelRowsCreated",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowRowsDeleted",
            new_name="LocalJadawelRowsDeleted",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowRowsUpdated",
            new_name="LocalJadawelRowsUpdated",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowTableServiceFieldMapping",
            new_name="LocalJadawelTableServiceFieldMapping",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowTableServiceFilter",
            new_name="LocalJadawelTableServiceFilter",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowTableServiceSort",
            new_name="LocalJadawelTableServiceSort",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowUpsertRow",
            new_name="LocalJadawelUpsertRow",
        ),
    ]
