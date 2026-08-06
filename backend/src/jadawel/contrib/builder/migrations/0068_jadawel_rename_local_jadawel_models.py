from django.db import migrations

# Renames the LocalBaserow* models to LocalJadawel*. Each pair differs only by
# that token, so the rename is 1:1 and RenameModel renames the table in place
# rather than dropping and recreating it.


class Migration(migrations.Migration):
    dependencies = [
        ("builder", "0067_slackwritemessageworkflowaction"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="LocalBaserowCreateRowWorkflowAction",
            new_name="LocalJadawelCreateRowWorkflowAction",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowDeleteRowWorkflowAction",
            new_name="LocalJadawelDeleteRowWorkflowAction",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowUpdateRowWorkflowAction",
            new_name="LocalJadawelUpdateRowWorkflowAction",
        ),
    ]
