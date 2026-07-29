from django.db import migrations

ENGLISH_DEFAULT = "Grid"
ARABIC_DEFAULT = "جدول"


def _user_views_named(apps, name):
    """Views named exactly `name` that live in a real (non-template) workspace.

    Template workspaces are excluded deliberately. Baserow's bundled templates are
    imported from the JSON files in `templates/`, and `sync_templates` recreates
    them verbatim — renaming their views here would be undone on the next sync and
    would meanwhile leave the shipped sample data inconsistent with its source. On
    a seeded instance they are also the large majority of the matches, so without
    this filter the migration looks far more invasive than the fix requires.
    """

    View = apps.get_model("database", "View")
    Template = apps.get_model("core", "Template")

    template_workspace_ids = Template.objects.exclude(workspace_id=None).values_list(
        "workspace_id", flat=True
    )
    return View.objects.filter(name=name).exclude(
        table__database__workspace_id__in=template_workspace_ids
    )


def rename_untranslated_grid_views(apps, schema_editor):
    """Rename default grid views that were created before the `ar` catalogue existed.

    `TableHandler.create_table` names the default view with `_("Grid")` inside a
    `translation.override(user.profile.language)` block, so the name is stored as
    literal text at creation time. Until this release there was no Arabic backend
    catalogue, so Arabic users got the untranslated English fallback and every
    table in the instance carries a view literally named "Grid". Adding the
    catalogue fixes new tables only — existing rows have to be rewritten here.

    Deliberately narrow: only views whose name is *exactly* "Grid" are touched. A
    view the user renamed, or one that merely contains the word, is left alone.
    """

    _user_views_named(apps, ENGLISH_DEFAULT).update(name=ARABIC_DEFAULT)


def restore_english_grid_views(apps, schema_editor):
    """Reverse: put the English default name back.

    Symmetrical with the forward pass — any view named exactly "جدول" returns to
    "Grid". A user who independently named a view "جدول" would be caught by this,
    which is acceptable for a rollback path.
    """

    _user_views_named(apps, ARABIC_DEFAULT).update(name=ENGLISH_DEFAULT)


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0209_alter_formview_mode"),
        # `Template.workspace` is read to skip bundled template workspaces.
        ("core", "0116_jadawel_arabic_english_only"),
    ]

    operations = [
        migrations.RunPython(
            rename_untranslated_grid_views, restore_english_grid_views
        ),
    ]
