import pytest
from rest_framework.exceptions import PermissionDenied

from arabase.mcp.protection.editing import reactivate_mcp_protection_policy
from arabase.mcp.protection.lifecycle import delete_ownerless_suspended_endpoint
from arabase.mcp.protection.models import (
    MCPProtectedField,
    MCPProtectedFieldState,
    MCPProtectionLifecycleAudit,
    MCPProtectionLifecycleStatus,
    MCPProtectionSafeReason,
)
from jadawel.core.models import WORKSPACE_USER_PERMISSION_ADMIN


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
def test_field_rename_preserves_membership_and_invalidates_generation(
    protected_endpoint,
):
    _, _, _, _, field, endpoint = protected_endpoint
    policy = endpoint.arabase_protection_policy
    previous_revision = policy.revision
    previous_generation = policy.access_generation

    field.name = "Renamed sensitive field"
    field.save(update_fields=["name"])

    relation = policy.protected_fields.get()
    policy.refresh_from_db()
    assert relation.field_id == field.id
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.ACTIVE
    assert policy.revision == previous_revision + 1
    assert policy.access_generation == previous_generation + 1


@pytest.mark.django_db
def test_account_reactivation_requires_owner_review_and_new_key(
    protected_endpoint,
):
    user, _, _, _, _, endpoint = protected_endpoint
    policy = endpoint.arabase_protection_policy
    user.is_active = False
    user.save(update_fields=["is_active"])
    policy.refresh_from_db()
    old_key = endpoint.key
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.SUSPENDED
    assert policy.safe_reason_code == MCPProtectionSafeReason.USER_INACTIVE

    user.is_active = True
    user.save(update_fields=["is_active"])
    policy.refresh_from_db()
    endpoint.refresh_from_db()
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.SUSPENDED
    assert policy.safe_reason_code == MCPProtectionSafeReason.USER_INACTIVE
    assert endpoint.key == old_key


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


@pytest.mark.django_db
def test_workspace_admin_can_delete_ownerless_suspended_endpoint(
    protected_endpoint, data_fixture
):
    owner, workspace, _, _, _, endpoint = protected_endpoint
    workspace.workspaceuser_set.get(user=owner).delete()
    policy = endpoint.arabase_protection_policy
    policy.refresh_from_db()
    admin = data_fixture.create_user()
    data_fixture.create_user_workspace(
        user=admin,
        workspace=workspace,
        permissions=WORKSPACE_USER_PERMISSION_ADMIN,
    )

    delete_ownerless_suspended_endpoint(user=admin, endpoint_id=endpoint.id)

    assert not endpoint.__class__.objects.filter(id=endpoint.id).exists()
    audit = MCPProtectionLifecycleAudit.objects.get(event_type="ownerless_admin_delete")
    assert audit.endpoint_id is None
    assert audit.actor_id == admin.id
    assert audit.event_type == "ownerless_admin_delete"
    assert audit.from_lifecycle_status == policy.lifecycle_status
    assert audit.to_lifecycle_status == "deleted"
    assert audit.metadata == {"endpoint_id": endpoint.id}


@pytest.mark.django_db
def test_workspace_admin_cannot_delete_endpoint_with_active_owner(
    protected_endpoint, data_fixture
):
    _owner, workspace, _, _, field, endpoint = protected_endpoint
    field.trashed = True
    field.save(update_fields=["trashed"])
    admin = data_fixture.create_user()
    data_fixture.create_user_workspace(
        user=admin,
        workspace=workspace,
        permissions=WORKSPACE_USER_PERMISSION_ADMIN,
    )

    with pytest.raises(PermissionDenied):
        delete_ownerless_suspended_endpoint(user=admin, endpoint_id=endpoint.id)

    assert endpoint.__class__.objects.filter(id=endpoint.id).exists()
    assert not MCPProtectionLifecycleAudit.objects.filter(
        event_type="ownerless_admin_delete"
    ).exists()
