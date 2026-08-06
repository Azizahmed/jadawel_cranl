from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0116_jadawel_arabic_english_only"),
    ]

    operations = [
        migrations.RenameField(
            model_name="settings",
            old_name="show_baserow_help_request",
            new_name="show_jadawel_help_request",
        ),
    ]
