from django.db import migrations

# Renames the LocalBaserow* models to LocalJadawel*. Each pair differs only by
# that token, so the rename is 1:1 and RenameModel renames the table in place
# rather than dropping and recreating it.


class Migration(migrations.Migration):
    dependencies = [
        ("automation", "0028_automationworkflowhistory_original_workflow_and_more"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="LocalBaserowAggregateRowsActionNode",
            new_name="LocalJadawelAggregateRowsActionNode",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowCreateRowActionNode",
            new_name="LocalJadawelCreateRowActionNode",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowDeleteRowActionNode",
            new_name="LocalJadawelDeleteRowActionNode",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowGetRowActionNode",
            new_name="LocalJadawelGetRowActionNode",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowListRowsActionNode",
            new_name="LocalJadawelListRowsActionNode",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowRowsCreatedTriggerNode",
            new_name="LocalJadawelRowsCreatedTriggerNode",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowRowsDeletedTriggerNode",
            new_name="LocalJadawelRowsDeletedTriggerNode",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowRowsUpdatedTriggerNode",
            new_name="LocalJadawelRowsUpdatedTriggerNode",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowUpdateRowActionNode",
            new_name="LocalJadawelUpdateRowActionNode",
        ),
    ]
