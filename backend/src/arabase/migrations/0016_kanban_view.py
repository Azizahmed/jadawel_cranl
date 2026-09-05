# Kanban view type (#35): the OSS board grouped by a single select field.
# Auto-generated, then the two pre-existing `safe_reason_code` alters that
# also show up on plain `main` were removed so this migration carries only
# the kanban models.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arabase', '0015_mcp_protection_lifecycle_audit'),
        ('database', '0211_jadawel_rename_table_usage_functions'),
    ]

    operations = [
        migrations.CreateModel(
            name='KanbanView',
            fields=[
                ('view_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='database.view')),
                ('card_cover_image_field', models.ForeignKey(blank=True, help_text='Optional file field whose first image is shown as the card cover.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kanban_view_card_cover_field', to='database.field')),
                ('single_select_field', models.ForeignKey(blank=True, help_text="The single select field whose options become the board's columns.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kanban_view_single_select_field', to='database.field')),
            ],
            options={
                'abstract': False,
            },
            bases=('database.view',),
        ),
        migrations.CreateModel(
            name='KanbanViewFieldOptions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hidden', models.BooleanField(default=True, help_text='Whether the field is shown on the kanban cards.')),
                ('order', models.SmallIntegerField(default=32767, help_text='The order that the field has on the kanban cards. Lower value is first.')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='database.field')),
                ('kanban_view', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='arabase.kanbanview')),
            ],
            options={
                'ordering': ('order', 'field_id'),
                'unique_together': {('kanban_view', 'field')},
            },
        ),
    ]
