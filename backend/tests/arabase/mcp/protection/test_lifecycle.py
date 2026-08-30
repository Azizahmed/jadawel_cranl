import pytest

from arabase.mcp.protection.editing import reactivate_mcp_protection_policy
from arabase.mcp.protection.models import (
    MCPProtectedField,
    MCPProtectedFieldState,
    MCPProtectionLifecycleStatus,
    MCPProtectionSafeReason,
)


@pytest.fixture
def protected_endpoint(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(table=table, name="Sensitive")
    endpoint = data_fixture.create_mcp_endpoint(user=user, workspace=workspace)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=field
    )
    return user, workspace, database, table, field, endpoint


@pytest.mark.django_db
def test_field_trash_and_restore_suspends_and_restores_protection(protected_endpoint):
    _, _, _, _, field, endpoint = protected_endpoint
    policy = endpoint.arabase_protection_policy

    field.trashed = True
    field.save(update_fields=["trashed"])
    relation = policy.protected_fields.get()
    policy.refresh_from_db()
    assert relation.state == MCPProtectedFieldState.SUSPENDED
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.PROTECTION_BLOCKED
    assert policy.safe_reason_code == MCPProtectionSafeReason.POLICY_RELATION_INVALID

    field.trashed = False
    field.save(update_fields=["trashed"])
    relation.refresh_from_db()
    policy.refresh_from_db()
    assert relation.state == MCPProtectedFieldState.ACTIVE
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.ACTIVE
    assert policy.safe_reason_code == MCPProtectionSafeReason.NONE


@pytest.mark.django_db
def test_table_and_database_trash_never_leave_an_active_relation(protected_endpoint):
    _, _, database, table, _, endpoint = protected_endpoint
    policy = endpoint.arabase_protection_policy

    table.trashed = True
    table.save(update_fields=["trashed"])
    policy.refresh_from_db()
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.PROTECTION_BLOCKED
    assert policy.protected_fields.get().state == MCPProtectedFieldState.SUSPENDED

    table.trashed = False
    table.save(update_fields=["trashed"])
    policy.refresh_from_db()
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.ACTIVE
    assert policy.protected_fields.get().state == MCPProtectedFieldState.ACTIVE

    database.trashed = True
    database.save(update_fields=["trashed"])
    policy.refresh_from_db()
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.PROTECTION_BLOCKED
    assert policy.protected_fields.get().state == MCPProtectedFieldState.SUSPENDED

    database.trashed = False
    database.save(update_fields=["trashed"])
    policy.refresh_from_db()
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.ACTIVE
    assert policy.protected_fields.get().state == MCPProtectedFieldState.ACTIVE


@pytest.mark.django_db
def test_membership_loss_requires_explicit_reactivation(
    protected_endpoint, data_fixture
):
    user, workspace, _, _, _, endpoint = protected_endpoint
    policy = endpoint.arabase_protection_policy
    workspace.workspaceuser_set.get(user=user).delete()
    policy.refresh_from_db()
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.SUSPENDED
    assert policy.safe_reason_code == MCPProtectionSafeReason.MEMBERSHIP_CHANGED

    data_fixture.create_user_workspace(user=user, workspace=workspace)
    policy.refresh_from_db()
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.SUSPENDED

    reactivated = reactivate_mcp_protection_policy(
        user=user, endpoint_id=endpoint.id, expected_revision=policy.revision
    )
    assert reactivated.lifecycle_status == MCPProtectionLifecycleStatus.ACTIVE
    assert reactivated.safe_reason_code == MCPProtectionSafeReason.NONE


@pytest.mark.django_db
def test_key_rotation_blocks_until_reactivation_issues_new_key(protected_endpoint):
    user, _, _, _, _, endpoint = protected_endpoint
    policy = endpoint.arabase_protection_policy
    old_key = endpoint.key
    endpoint.key = "x" * 32
    endpoint.save(update_fields=["key"])
    policy.refresh_from_db()
    assert endpoint.key != old_key
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.PROTECTION_BLOCKED
    assert policy.safe_reason_code == MCPProtectionSafeReason.CREDENTIAL_ROTATED

    reactivated = reactivate_mcp_protection_policy(
        user=user, endpoint_id=endpoint.id, expected_revision=policy.revision
    )
    endpoint.refresh_from_db()
    assert reactivated.lifecycle_status == MCPProtectionLifecycleStatus.ACTIVE
    assert endpoint.key != "x" * 32
