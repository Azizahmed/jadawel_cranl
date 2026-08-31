import base64
import json

from django.db import transaction
from django.test import override_settings

import fakeredis
import pytest
from asgiref.sync import async_to_sync
from mcp.shared.memory import (
    create_connected_server_and_client_session as client_session,
)

from arabase.mcp.protection.models import MCPProtectedField, MCPProtectionPolicy
from arabase.mcp.protection.vault import (
    MASK_TOKEN_REDIS_PREFIX,
    MaskTokenVaultUnavailable,
    RedisMaskTokenVault,
)
from jadawel.contrib.database.fields.dependencies.models import FieldDependency
from jadawel.core.mcp import JadawelMCPServer, current_key

FINGERPRINT_KEY = base64.b64encode(b"f" * 32).decode()


def _is_mask_token(value):
    return set(value) == {"$jadawelProtected"} and value["$jadawelProtected"]["v"] == 1


def _token_record_count(redis):
    return sum(
        len(key) == len(MASK_TOKEN_REDIS_PREFIX) + 64
        for key in redis.scan_iter(match=f"{MASK_TOKEN_REDIS_PREFIX}*")
    )


@pytest.mark.django_db
@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_list_rows_masks_direct_values_but_preserves_true_empty_values(
    data_fixture, monkeypatch
):
    endpoint = data_fixture.create_mcp_endpoint()
    database = data_fixture.create_database_application(workspace=endpoint.workspace)
    table = data_fixture.create_database_table(database=database)
    secret = data_fixture.create_text_field(name="Secret", table=table, primary=True)
    amount = data_fixture.create_number_field(name="Amount", table=table)
    approved = data_fixture.create_boolean_field(name="Approved", table=table)
    empty = data_fixture.create_text_field(name="Empty", table=table)
    for field in (secret, amount, approved, empty):
        MCPProtectedField.objects.create(
            policy=endpoint.arabase_protection_policy,
            field=field,
        )
    model = table.get_model(attribute_names=True)
    model.objects.create(
        secret="never leave Jadawel", amount=0, approved=False, empty=""
    )

    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    monkeypatch.setattr(
        "arabase.mcp.protection.egress.get_mask_token_vault", lambda: vault
    )
    mcp = JadawelMCPServer()
    key_token = current_key.set(endpoint.key)

    try:

        async def inner():
            async with client_session(mcp._mcp_server) as client:
                return await client.call_tool("list_table_rows", {"table_id": table.id})

        with transaction.atomic():
            result = async_to_sync(inner)()
    finally:
        current_key.reset(key_token)

    assert result.isError is False
    serialized = result.content[0].text
    assert "never leave Jadawel" not in serialized
    row = json.loads(serialized)["results"][0]
    assert _is_mask_token(row["Secret"])
    assert _is_mask_token(row["Amount"])
    assert _is_mask_token(row["Approved"])
    assert row["Empty"] == ""
    assert _token_record_count(redis) == 3


@pytest.mark.django_db
def test_vault_configuration_failure_returns_only_safe_error_and_never_plaintext(
    data_fixture, monkeypatch
):
    endpoint = data_fixture.create_mcp_endpoint()
    database = data_fixture.create_database_application(workspace=endpoint.workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(name="Secret", table=table, primary=True)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=field
    )
    model = table.get_model(attribute_names=True)
    model.objects.create(secret="vault outage canary")

    def unavailable_vault():
        raise MaskTokenVaultUnavailable

    monkeypatch.setattr(
        "arabase.mcp.protection.egress.get_mask_token_vault", unavailable_vault
    )
    mcp = JadawelMCPServer()
    key_token = current_key.set(endpoint.key)
    try:

        async def inner():
            async with client_session(mcp._mcp_server) as client:
                return await client.call_tool("list_table_rows", {"table_id": table.id})

        with transaction.atomic():
            result = async_to_sync(inner)()
    finally:
        current_key.reset(key_token)

    assert result.isError is True
    assert "vault outage canary" not in result.content[0].text
    assert json.loads(result.content[0].text)["error"]["code"] == (
        "PROTECTION_UNAVAILABLE"
    )


@pytest.mark.django_db
@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_policy_revision_change_before_release_discards_complete_response(
    data_fixture, monkeypatch
):
    endpoint = data_fixture.create_mcp_endpoint()
    database = data_fixture.create_database_application(workspace=endpoint.workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(name="Secret", table=table, primary=True)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=field
    )
    model = table.get_model(attribute_names=True)
    model.objects.create(secret="revision race canary")
    redis = fakeredis.FakeRedis(decode_responses=True)

    class RacingVault(RedisMaskTokenVault):
        def issue(self, binding, value):
            issued = super().issue(binding, value)
            MCPProtectionPolicy.objects.filter(endpoint=endpoint).update(revision=2)
            return issued

    vault = RacingVault(redis_client=redis)
    monkeypatch.setattr(
        "arabase.mcp.protection.egress.get_mask_token_vault", lambda: vault
    )
    mcp = JadawelMCPServer()
    key_token = current_key.set(endpoint.key)
    try:

        async def inner():
            async with client_session(mcp._mcp_server) as client:
                return await client.call_tool("list_table_rows", {"table_id": table.id})

        with transaction.atomic():
            result = async_to_sync(inner)()
    finally:
        current_key.reset(key_token)

    assert result.isError is True
    assert "revision race canary" not in result.content[0].text
    assert redis.dbsize() == 0


@pytest.mark.django_db
@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_create_and_update_rows_mask_every_direct_protected_value(
    data_fixture, monkeypatch
):
    endpoint = data_fixture.create_mcp_endpoint()
    database = data_fixture.create_database_application(workspace=endpoint.workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(name="Secret", table=table, primary=True)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=field
    )
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    monkeypatch.setattr(
        "arabase.mcp.protection.egress.get_mask_token_vault", lambda: vault
    )
    mcp = JadawelMCPServer()
    key_token = current_key.set(endpoint.key)

    try:

        async def inner():
            async with client_session(mcp._mcp_server) as client:
                created = await client.call_tool(
                    "create_rows",
                    {"table_id": table.id, "rows": [{"Secret": "created canary"}]},
                )
                created_row = json.loads(created.content[0].text)[0]
                assert created.isError is False
                assert "created canary" not in created.content[0].text
                assert _is_mask_token(created_row["Secret"])

                updated = await client.call_tool(
                    "update_rows",
                    {
                        "table_id": table.id,
                        "rows": [{"id": created_row["id"], "Secret": "updated canary"}],
                    },
                )
                updated_row = json.loads(updated.content[0].text)[0]
                assert updated.isError is False
                assert "updated canary" not in updated.content[0].text
                assert _is_mask_token(updated_row["Secret"])

        with transaction.atomic():
            async_to_sync(inner)()
    finally:
        current_key.reset(key_token)

    assert _token_record_count(redis) == 2


@pytest.mark.django_db
@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_update_accepts_only_a_same_cell_preservation_token(data_fixture, monkeypatch):
    endpoint = data_fixture.create_mcp_endpoint()
    database = data_fixture.create_database_application(workspace=endpoint.workspace)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(name="Secret", table=table, primary=True)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=field
    )
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    monkeypatch.setattr(
        "arabase.mcp.protection.egress.get_mask_token_vault", lambda: vault
    )
    monkeypatch.setattr(
        "arabase.mcp.protection.interceptor.get_mask_token_vault", lambda: vault
    )
    mcp = JadawelMCPServer()
    key_token = current_key.set(endpoint.key)
    try:

        async def inner():
            async with client_session(mcp._mcp_server) as client:
                created = await client.call_tool(
                    "create_rows", {"table_id": table.id, "rows": [{"Secret": "keep"}]}
                )
                created_row = json.loads(created.content[0].text)[0]
                preserved = await client.call_tool(
                    "update_rows",
                    {
                        "table_id": table.id,
                        "rows": [
                            {
                                "id": created_row["id"],
                                "Secret": created_row["Secret"],
                            }
                        ],
                    },
                )
                return created_row, preserved

        with transaction.atomic():
            created_row, preserved = async_to_sync(inner)()
    finally:
        current_key.reset(key_token)

    assert preserved.isError is False
    assert json.loads(preserved.content[0].text)[0]["Secret"] != "keep"
    raw = table.get_model(attribute_names=True).objects.get(id=created_row["id"])
    assert raw.secret == "keep"


@pytest.mark.django_db
def test_protection_on_another_table_leaves_unprotected_search_unchanged(
    data_fixture, monkeypatch
):
    endpoint = data_fixture.create_mcp_endpoint()
    database = data_fixture.create_database_application(workspace=endpoint.workspace)
    protected_table = data_fixture.create_database_table(database=database)
    protected_field = data_fixture.create_text_field(
        name="Secret", table=protected_table, primary=True
    )
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=protected_field
    )
    public_table = data_fixture.create_database_table(database=database)
    data_fixture.create_text_field(name="Name", table=public_table, primary=True)
    public_table.get_model(attribute_names=True).objects.create(name="search canary")

    def vault_must_not_be_used():
        raise AssertionError("unprotected tables do not need the token vault")

    monkeypatch.setattr(
        "arabase.mcp.protection.egress.get_mask_token_vault", vault_must_not_be_used
    )
    mcp = JadawelMCPServer()
    key_token = current_key.set(endpoint.key)
    try:

        async def inner():
            async with client_session(mcp._mcp_server) as client:
                return await client.call_tool(
                    "list_table_rows",
                    {"table_id": public_table.id, "search": "search canary"},
                )

        with transaction.atomic():
            result = async_to_sync(inner)()
    finally:
        current_key.reset(key_token)

    assert result.isError is False
    assert json.loads(result.content[0].text)["results"][0]["Name"] == "search canary"


@pytest.mark.django_db
@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_unrelated_broken_dependency_does_not_block_protected_rows(
    data_fixture, monkeypatch
):
    endpoint = data_fixture.create_mcp_endpoint()
    database = data_fixture.create_database_application(workspace=endpoint.workspace)
    table = data_fixture.create_database_table(database=database)
    protected = data_fixture.create_text_field(
        name="Secret", table=table, primary=True
    )
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=protected
    )

    unrelated_table = data_fixture.create_database_table(database=database)
    unrelated = data_fixture.create_text_field(name="Broken", table=unrelated_table)
    FieldDependency.objects.create(
        dependant=unrelated,
        dependency=None,
        broken_reference_field_name="Missing field",
    )
    table.get_model(attribute_names=True).objects.create(secret="protected canary")

    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    monkeypatch.setattr(
        "arabase.mcp.protection.egress.get_mask_token_vault", lambda: vault
    )
    mcp = JadawelMCPServer()
    key_token = current_key.set(endpoint.key)
    try:

        async def inner():
            async with client_session(mcp._mcp_server) as client:
                return await client.call_tool("list_table_rows", {"table_id": table.id})

        with transaction.atomic():
            result = async_to_sync(inner)()
    finally:
        current_key.reset(key_token)

    assert result.isError is False
    serialized = result.content[0].text
    assert "protected canary" not in serialized
    assert _is_mask_token(json.loads(serialized)["results"][0]["Secret"])


@pytest.mark.django_db
@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_broken_dependency_on_a_protected_field_still_fails_closed(
    data_fixture, monkeypatch
):
    endpoint = data_fixture.create_mcp_endpoint()
    database = data_fixture.create_database_application(workspace=endpoint.workspace)
    table = data_fixture.create_database_table(database=database)
    protected = data_fixture.create_text_field(
        name="Secret", table=table, primary=True
    )
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=protected
    )
    FieldDependency.objects.create(
        dependant=protected,
        dependency=None,
        broken_reference_field_name="Missing field",
    )
    table.get_model(attribute_names=True).objects.create(secret="protected canary")

    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    monkeypatch.setattr(
        "arabase.mcp.protection.egress.get_mask_token_vault", lambda: vault
    )
    mcp = JadawelMCPServer()
    key_token = current_key.set(endpoint.key)
    try:

        async def inner():
            async with client_session(mcp._mcp_server) as client:
                return await client.call_tool("list_table_rows", {"table_id": table.id})

        with transaction.atomic():
            result = async_to_sync(inner)()
    finally:
        current_key.reset(key_token)

    assert result.isError is True
    assert "protected canary" not in result.content[0].text
    assert json.loads(result.content[0].text)["error"]["code"] == (
        "PROTECTION_UNAVAILABLE"
    )
