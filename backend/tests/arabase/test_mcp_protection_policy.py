from django.db import IntegrityError, transaction
from django.shortcuts import reverse

import pytest
from rest_framework.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from arabase.mcp.protection.models import (
    MCPProtectedField,
    MCPProtectionLifecycleStatus,
    MCPProtectionPolicy,
    MCPProtectionSafeReason,
)
from arabase.mcp.protection.policy_state import get_mcp_protection_policy_state
from arabase.mcp.protection.readiness import check_mcp_protection_policy_readiness
from jadawel.contrib.database.fields.models import Field
from jadawel.core.action.registries import action_type_registry
from jadawel.core.mcp.actions import CreateMCPEndpointActionType
from jadawel.core.mcp.errors import MCPErrorCode, SafeMCPToolError
from jadawel.core.mcp.models import MCPEndpoint
from jadawel.core.models import WORKSPACE_USER_PERMISSION_ADMIN


@pytest.mark.django_db
def test_new_endpoint_gets_one_explicit_empty_policy(data_fixture):
    endpoint = data_fixture.create_mcp_endpoint()

    policy = MCPProtectionPolicy.objects.get(endpoint=endpoint)

    assert policy.revision == 1
    assert policy.access_generation == 1
    assert policy.lifecycle_status == MCPProtectionLifecycleStatus.ACTIVE
    assert policy.safe_reason_code == ""
    assert policy.protected_fields.count() == 0
    assert get_mcp_protection_policy_state(endpoint).has_protected_fields is False


@pytest.mark.django_db
def test_legacy_endpoint_creation_rolls_back_when_policy_creation_fails(
    data_fixture, monkeypatch
):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)

    def fail_policy_creation(**kwargs):
        raise RuntimeError("policy persistence failed")

    monkeypatch.setattr(MCPProtectionPolicy.objects, "create", fail_policy_creation)

    with pytest.raises(RuntimeError, match="policy persistence failed"):
        action_type_registry.get(CreateMCPEndpointActionType.type).do(
            user, workspace, "Must roll back"
        )

    assert MCPEndpoint.objects.filter(name="Must roll back").exists() is False


@pytest.mark.django_db
def test_missing_policy_fails_mcp_closed(data_fixture):
    endpoint = data_fixture.create_mcp_endpoint()
    MCPProtectionPolicy.objects.filter(endpoint=endpoint).delete()

    with pytest.raises(SafeMCPToolError) as exc_info:
        get_mcp_protection_policy_state(endpoint)

    assert exc_info.value.code is MCPErrorCode.PROTECTION_UNAVAILABLE


@pytest.mark.django_db
def test_cross_workspace_field_relation_fails_mcp_closed(data_fixture):
    endpoint = data_fixture.create_mcp_endpoint()
    other_workspace = data_fixture.create_workspace()
    database = data_fixture.create_database_application(workspace=other_workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(table=table)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy,
        field=field,
    )

    with pytest.raises(SafeMCPToolError) as exc_info:
        get_mcp_protection_policy_state(endpoint)

    assert exc_info.value.code is MCPErrorCode.PROTECTION_UNAVAILABLE
    readiness = check_mcp_protection_policy_readiness()
    assert readiness.ready is False
    assert readiness.safe_reason_code == "POLICY_RELATION_INVALID"


@pytest.mark.django_db
def test_policy_constraints_reject_duplicate_field_relations(data_fixture):
    endpoint = data_fixture.create_mcp_endpoint()
    database = data_fixture.create_database_application(workspace=endpoint.workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(table=table)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=field
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        MCPProtectedField.objects.create(
            policy=endpoint.arabase_protection_policy, field=field
        )


@pytest.mark.django_db
def test_policy_constraints_reject_inconsistent_status_and_reason(data_fixture):
    endpoint = data_fixture.create_mcp_endpoint()

    with pytest.raises(IntegrityError), transaction.atomic():
        MCPProtectionPolicy.objects.filter(endpoint=endpoint).update(
            safe_reason_code="POLICY_STATE_INVALID"
        )


@pytest.mark.django_db
def test_policy_readiness_is_content_blind_and_fails_on_missing_policy(data_fixture):
    endpoint = data_fixture.create_mcp_endpoint()
    assert check_mcp_protection_policy_readiness().ready is True

    MCPProtectionPolicy.objects.filter(endpoint=endpoint).delete()

    readiness = check_mcp_protection_policy_readiness()
    assert readiness.ready is False
    assert readiness.safe_reason_code == "POLICY_COUNT_MISMATCH"


@pytest.mark.django_db
def test_owner_reads_safe_policy_metadata(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(
        workspace=workspace, name="Customer records"
    )
    table = data_fixture.create_database_table(database=database, name="Customers")
    field = data_fixture.create_text_field(table=table, name="National ID")
    endpoint = data_fixture.create_mcp_endpoint(user=user, workspace=workspace)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy,
        field=field,
    )
    url = reverse(
        "api:arabase:mcp_protection_policy", kwargs={"endpoint_id": endpoint.id}
    )

    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {token}")

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert body == {
        "endpoint_id": endpoint.id,
        "revision": 1,
        "lifecycle_status": "active",
        "safe_reason_code": "",
        "protected_field_count": 1,
        "fields": [
            {
                "id": field.id,
                "state": "active",
                "safe_reason_code": "",
                "name": "National ID",
                "type": "text",
                "table": {"id": table.id, "name": "Customers"},
                "database": {"id": database.id, "name": "Customer records"},
            }
        ],
        "created_on": body["created_on"],
        "updated_on": body["updated_on"],
    }
    serialized = response.content.decode()
    assert endpoint.key not in serialized
    assert "access_generation" not in body
    assert "token" not in serialized.lower()


@pytest.mark.django_db
def test_policy_metadata_hides_type_when_field_adapter_is_unavailable(
    api_client, data_fixture, monkeypatch
):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(table=table, name="Adapter field")
    endpoint = data_fixture.create_mcp_endpoint(user=user, workspace=workspace)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy,
        field=field,
    )

    def unavailable_adapter(_field):
        raise RuntimeError("adapter unavailable")

    monkeypatch.setattr(Field, "get_type", unavailable_adapter)
    url = reverse(
        "api:arabase:mcp_protection_policy", kwargs={"endpoint_id": endpoint.id}
    )

    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {token}")

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert body["protected_field_count"] == 1
    assert body["fields"][0]["id"] == field.id
    assert body["fields"][0]["name"] == "Adapter field"
    assert body["fields"][0]["type"] is None


@pytest.mark.django_db
def test_policy_metadata_count_excludes_suspended_fields(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(table=table, name="Suspended field")
    endpoint = data_fixture.create_mcp_endpoint(user=user, workspace=workspace)
    relation = MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy,
        field=field,
    )
    relation.state = "suspended"
    relation.safe_reason_code = "WORKSPACE_SUSPENDED"
    relation.save(update_fields=["state", "safe_reason_code", "updated_on"])
    url = reverse(
        "api:arabase:mcp_protection_policy", kwargs={"endpoint_id": endpoint.id}
    )

    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {token}")

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert body["protected_field_count"] == 0
    assert body["fields"][0]["state"] == "suspended"


@pytest.mark.django_db
def test_policy_read_hides_display_metadata_without_current_field_permission(
    api_client, data_fixture, monkeypatch
):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(table=table)
    endpoint = data_fixture.create_mcp_endpoint(user=user, workspace=workspace)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=field
    )
    monkeypatch.setattr(
        "arabase.api.mcp_protection.views._may_display_field_metadata",
        lambda user, field: False,
    )
    url = reverse(
        "api:arabase:mcp_protection_policy", kwargs={"endpoint_id": endpoint.id}
    )

    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {token}")

    protected_field = response.json()["fields"][0]
    assert protected_field["id"] == field.id
    assert protected_field["state"] == "active"
    assert protected_field["name"] is None
    assert protected_field["type"] is None
    assert protected_field["table"] is None
    assert protected_field["database"] is None


@pytest.mark.django_db
def test_policy_read_is_owner_only(api_client, data_fixture):
    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    endpoint = data_fixture.create_mcp_endpoint(user=owner, workspace=workspace)
    other_user, other_token = data_fixture.create_user_and_token()
    data_fixture.create_user_workspace(user=other_user, workspace=workspace)
    url = reverse(
        "api:arabase:mcp_protection_policy", kwargs={"endpoint_id": endpoint.id}
    )

    unauthenticated = api_client.get(url)
    forbidden = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {other_token}")

    assert unauthenticated.status_code == HTTP_401_UNAUTHORIZED
    assert forbidden.status_code == HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_endpoint_summaries_include_safe_policy_status(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    endpoint = data_fixture.create_mcp_endpoint(user=user, workspace=workspace)
    url = reverse("api:arabase:mcp_endpoint_protection_summaries")

    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {token}")

    assert response.status_code == HTTP_200_OK
    assert response.json() == [
        {
            "endpoint_id": endpoint.id,
            "name": endpoint.name,
            "workspace_id": workspace.id,
            "workspace_name": workspace.name,
            "protected_field_count": 0,
            "lifecycle_status": "active",
            "safe_reason_code": "",
        }
    ]
    assert endpoint.key not in response.content.decode()


@pytest.mark.django_db
def test_workspace_admin_summaries_include_blocked_endpoint_without_secrets(
    api_client, data_fixture
):
    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    endpoint = data_fixture.create_mcp_endpoint(user=owner, workspace=workspace)
    policy = endpoint.arabase_protection_policy
    workspace.workspaceuser_set.get(user=owner).delete()
    policy.refresh_from_db()
    policy.lifecycle_status = MCPProtectionLifecycleStatus.PROTECTION_BLOCKED
    policy.safe_reason_code = MCPProtectionSafeReason.CREDENTIAL_ROTATED
    policy.save(update_fields=["lifecycle_status", "safe_reason_code", "updated_on"])

    admin, token = data_fixture.create_user_and_token()
    data_fixture.create_user_workspace(
        user=admin,
        workspace=workspace,
        permissions=WORKSPACE_USER_PERMISSION_ADMIN,
    )

    response = api_client.get(
        reverse("api:arabase:mcp_endpoint_protection_summaries"),
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == [
        {
            "endpoint_id": endpoint.id,
            "name": endpoint.name,
            "workspace_id": workspace.id,
            "workspace_name": workspace.name,
            "protected_field_count": 0,
            "lifecycle_status": "protection_blocked",
            "safe_reason_code": "CREDENTIAL_ROTATED",
        }
    ]
    assert endpoint.key not in response.content.decode()
