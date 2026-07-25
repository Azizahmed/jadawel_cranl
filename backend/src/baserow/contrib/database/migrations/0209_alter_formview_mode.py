from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0208_gridview_frozen_column_count"),
    ]

    operations = [
        migrations.AlterField(
            model_name="formview",
            name="mode",
            field=models.TextField(
                choices=[("form", "form")],
                default="form",
                help_text="Configurable mode of the form.",
                max_length=64,
            ),
        ),
    ]
