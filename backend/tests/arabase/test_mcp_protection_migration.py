import importlib

from django.apps import apps
from django.db import connection

import pytest

from arabase.mcp.protection.models import MCPProtectionPolicy


@pytest.mark.django_db
def test_mcp_protection_migration_backfills_populated_database(data_fixture):
    endpoints = [data_fixture.create_mcp_endpoint() for _ in range(2)]
    MCPProtectionPolicy.objects.all().delete()
    migration = importlib.import_module("arabase.migrations.0007_mcp_protection_policy")

    migration.backfill_empty_policies(apps, None)
    migration.backfill_empty_policies(apps, None)

    policies = list(MCPProtectionPolicy.objects.order_by("endpoint_id"))
    assert [policy.endpoint_id for policy in policies] == [
        endpoint.id for endpoint in endpoints
    ]
    assert all(policy.revision == 1 for policy in policies)
    assert all(policy.access_generation == 1 for policy in policies)
    assert all(policy.lifecycle_status == "active" for policy in policies)
    assert all(policy.safe_reason_code == "" for policy in policies)


@pytest.mark.once_per_day_in_ci
def test_mcp_protection_schema_migrates_populated_snapshot(migrator):
    old_state = migrator.migrate([("arabase", "0006_html_page_view")])
    User = old_state.apps.get_model("auth", "User")
    Workspace = old_state.apps.get_model("core", "Workspace")
    MCPEndpoint = old_state.apps.get_model("core", "MCPEndpoint")

    user = User.objects.create(username="mcp-policy-migration-owner")
    workspace = Workspace.objects.create(name="Migration workspace")
    endpoints = [
        MCPEndpoint.objects.create(
            name=f"Endpoint {index}",
            key=f"migration-key-{index:02d}",
            user_id=user.id,
            workspace_id=workspace.id,
        )
        for index in range(2)
    ]

    new_state = migrator.migrate([("arabase", "0007_mcp_protection_policy")])
    MCPProtectionPolicy = new_state.apps.get_model("arabase", "MCPProtectionPolicy")
    MCPProtectedField = new_state.apps.get_model("arabase", "MCPProtectedField")

    assert list(
        MCPProtectionPolicy.objects.order_by("endpoint_id").values_list(
            "endpoint_id", flat=True
        )
    ) == [endpoint.id for endpoint in endpoints]
    assert MCPProtectionPolicy._meta.get_field("endpoint").unique is True
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(
            cursor, MCPProtectedField._meta.db_table
        )
    assert constraints["arabase_unique_mcp_policy_field"]["unique"] is True
    assert constraints["ara_mcp_pf_field_state_idx"]["index"] is True
    assert constraints["ara_mcp_pf_policy_state_idx"]["index"] is True
