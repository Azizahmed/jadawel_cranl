import django.db.models.deletion
import jadawel.core.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("arabase", "0010_mcp_protection_lifecycle_reasons"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MCPProtectionMutationAudit",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                (
                    "updated_on",
                    jadawel.core.fields.SyncedDateTimeField(auto_now=True),
                ),
                ("tool_type", models.CharField(max_length=64)),
                ("table_id", models.PositiveBigIntegerField()),
                ("row_count", models.PositiveIntegerField()),
                ("outcome", models.CharField(default="success", max_length=24)),
                (
                    "actor",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mcp_protection_mutation_audits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "endpoint",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="protection_mutation_audits",
                        to="core.mcpendpoint",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["endpoint", "created_on"],
                        name="ara_mcp_audit_ep_created_idx",
                    )
                ]
            },
        )
    ]
