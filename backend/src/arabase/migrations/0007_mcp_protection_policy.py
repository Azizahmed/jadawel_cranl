import django.db.models.deletion
import jadawel.core.fields
from django.db import migrations, models


def backfill_empty_policies(apps, schema_editor):
    MCPEndpoint = apps.get_model("core", "MCPEndpoint")
    MCPProtectionPolicy = apps.get_model("arabase", "MCPProtectionPolicy")
    existing_endpoint_ids = set(
        MCPProtectionPolicy.objects.values_list("endpoint_id", flat=True)
    )
    policies = (
        MCPProtectionPolicy(endpoint_id=endpoint_id)
        for endpoint_id in MCPEndpoint.objects.exclude(
            id__in=existing_endpoint_ids
        ).values_list("id", flat=True)
    )
    MCPProtectionPolicy.objects.bulk_create(policies, batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [
        ("arabase", "0006_html_page_view"),
        ("core", "0117_jadawel_rename_show_help_request"),
        ("database", "0211_jadawel_rename_table_usage_functions"),
    ]

    operations = [
        migrations.CreateModel(
            name="MCPProtectionPolicy",
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
                ("revision", models.PositiveBigIntegerField(default=1)),
                ("access_generation", models.PositiveBigIntegerField(default=1)),
                (
                    "lifecycle_status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                            ("protection_blocked", "Protection blocked"),
                        ],
                        default="active",
                        max_length=32,
                    ),
                ),
                (
                    "safe_reason_code",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "None"),
                            ("POLICY_COUNT_MISMATCH", "Policy count mismatch"),
                            ("POLICY_STATE_INVALID", "Policy state invalid"),
                            ("POLICY_RELATION_INVALID", "Policy relation invalid"),
                        ],
                        default="",
                        max_length=64,
                    ),
                ),
                (
                    "endpoint",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="arabase_protection_policy",
                        to="core.mcpendpoint",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MCPProtectedField",
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
                (
                    "state",
                    models.CharField(
                        choices=[("active", "Active"), ("suspended", "Suspended")],
                        default="active",
                        max_length=16,
                    ),
                ),
                (
                    "safe_reason_code",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "None"),
                            ("POLICY_COUNT_MISMATCH", "Policy count mismatch"),
                            ("POLICY_STATE_INVALID", "Policy state invalid"),
                            ("POLICY_RELATION_INVALID", "Policy relation invalid"),
                        ],
                        default="",
                        max_length=64,
                    ),
                ),
                (
                    "field",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mcp_protection_relations",
                        to="database.field",
                    ),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="protected_fields",
                        to="arabase.mcpprotectionpolicy",
                    ),
                ),
            ],
            options={"ordering": ("field_id",)},
        ),
        migrations.AddConstraint(
            model_name="mcpprotectionpolicy",
            constraint=models.CheckConstraint(
                condition=models.Q(("revision__gte", 1)),
                name="arabase_mcp_policy_revision_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="mcpprotectionpolicy",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        ("lifecycle_status", "active"), ("safe_reason_code", "")
                    )
                    | (
                        ~models.Q(("lifecycle_status", "active"))
                        & ~models.Q(("safe_reason_code", ""))
                    )
                ),
                name="arabase_mcp_policy_status_reason_consistent",
            ),
        ),
        migrations.AddConstraint(
            model_name="mcpprotectionpolicy",
            constraint=models.CheckConstraint(
                condition=models.Q(("access_generation__gte", 1)),
                name="arabase_mcp_access_generation_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="mcpprotectedfield",
            constraint=models.UniqueConstraint(
                fields=("policy", "field"),
                name="arabase_unique_mcp_policy_field",
            ),
        ),
        migrations.AddConstraint(
            model_name="mcpprotectedfield",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("safe_reason_code", ""), ("state", "active"))
                    | (
                        models.Q(("state", "suspended"))
                        & ~models.Q(("safe_reason_code", ""))
                    )
                ),
                name="arabase_mcp_field_state_reason_consistent",
            ),
        ),
        migrations.AddIndex(
            model_name="mcpprotectedfield",
            index=models.Index(
                fields=["field", "state"], name="ara_mcp_pf_field_state_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="mcpprotectedfield",
            index=models.Index(
                fields=["policy", "state"], name="ara_mcp_pf_policy_state_idx"
            ),
        ),
        migrations.RunPython(backfill_empty_policies, migrations.RunPython.noop),
    ]
