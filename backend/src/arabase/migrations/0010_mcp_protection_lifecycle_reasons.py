from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("arabase", "0009_mcp_protection_edit_command")]

    operations = [
        migrations.AlterField(
            model_name="mcpprotectionpolicy",
            name="safe_reason_code",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "None"),
                    ("POLICY_COUNT_MISMATCH", "Policy count mismatch"),
                    ("POLICY_STATE_INVALID", "Policy state invalid"),
                    ("POLICY_RELATION_INVALID", "Policy relation invalid"),
                    ("WORKSPACE_SUSPENDED", "Workspace suspended"),
                    ("MEMBERSHIP_CHANGED", "Membership changed"),
                    ("USER_INACTIVE", "User inactive"),
                    ("CREDENTIAL_ROTATED", "Credential rotated"),
                    ("PROTECTION_REDIS_UNAVAILABLE", "Protection Redis unavailable"),
                ],
                default="",
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="mcpprotectedfield",
            name="safe_reason_code",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "None"),
                    ("POLICY_COUNT_MISMATCH", "Policy count mismatch"),
                    ("POLICY_STATE_INVALID", "Policy state invalid"),
                    ("POLICY_RELATION_INVALID", "Policy relation invalid"),
                    ("WORKSPACE_SUSPENDED", "Workspace suspended"),
                    ("MEMBERSHIP_CHANGED", "Membership changed"),
                    ("USER_INACTIVE", "User inactive"),
                    ("CREDENTIAL_ROTATED", "Credential rotated"),
                    ("PROTECTION_REDIS_UNAVAILABLE", "Protection Redis unavailable"),
                ],
                default="",
                max_length=64,
            ),
        ),
    ]
