from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("arabase", "0011_mcp_protection_mutation_audit")]

    operations = [
        migrations.AddField(
            model_name="mcpprotectionmutationaudit",
            name="access_generation",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="mcpprotectionmutationaudit",
            name="policy_revision",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="mcpprotectionmutationaudit",
            name="protected_field_ids",
            field=models.JSONField(default=list),
        ),
    ]
