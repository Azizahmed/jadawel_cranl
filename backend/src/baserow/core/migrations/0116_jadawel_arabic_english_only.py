from django.db import migrations, models

SUPPORTED = ("ar", "en")
FALLBACK = "ar"


def strand_removed_languages(apps, schema_editor):
    """Move users off languages this build no longer ships.

    Dropping a language from settings.LANGUAGES only changes validation and the
    field's choices; it does not touch rows that already hold e.g. 'fr'. Such a
    user would keep requesting a locale the frontend can no longer resolve, so
    they are moved to the default. Narrowing to two supported values is the
    whole point of the change, so this is a deliberate, one-way normalisation.
    """

    UserProfile = apps.get_model("core", "UserProfile")
    UserProfile.objects.exclude(language__in=SUPPORTED).update(language=FALLBACK)


def noop_reverse(apps, schema_editor):
    """Reversing restores the choices, not the users' original languages.

    The original values are not recoverable from this migration — they were
    overwritten in place. Reversing is allowed so the schema can be rolled back,
    but anyone who was on a removed language stays on the fallback.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0115_jadawel_add_arabic_language"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="language",
            field=models.TextField(
                choices=[("ar", "Arabic"), ("en", "English")],
                default="ar",
                help_text=(
                    "An ISO 639 language code (with optional variant) "
                    "selected by the user. Ex: en-GB."
                ),
                max_length=10,
            ),
        ),
        migrations.RunPython(strand_removed_languages, noop_reverse),
    ]
