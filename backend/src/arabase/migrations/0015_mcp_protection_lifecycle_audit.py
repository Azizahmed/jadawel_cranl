import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import jadawel.core.fields


class Migration(migrations.Migration):
    dependencies = [
        ("arabase", "0014_htmlpageartifactstate_endpoint"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MCPProtectionLifecycleAudit",
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
                ("event_type", models.CharField(max_length=64)),
                (
                    "from_lifecycle_status",
                    models.CharField(blank=True, default="", max_length=32),
                ),
                (
                    "to_lifecycle_status",
                    models.CharField(blank=True, default="", max_length=32),
                ),
                (
                    "reason_code",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                (
                    "policy_revision",
                    models.PositiveBigIntegerField(blank=True, null=True),
                ),
                (
                    "access_generation",
                    models.PositiveBigIntegerField(blank=True, null=True),
                ),
                ("metadata", models.JSONField(default=dict)),
                (
                    "actor",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mcp_protection_lifecycle_audits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "endpoint",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="protection_lifecycle_audits",
                        to="core.mcpendpoint",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["endpoint", "created_on"],
                name="ara_mcp_lifecycle_created_idx",
                    )
                ]
            },
        )
    ]
