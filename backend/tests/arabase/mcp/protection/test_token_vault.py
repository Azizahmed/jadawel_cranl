import base64
import hashlib
import json
from dataclasses import replace

from django.test import override_settings

import fakeredis
import pytest

import arabase.mcp.protection.vault as vault_module
from arabase.mcp.protection.tokens import extract_mask_token_handle
from arabase.mcp.protection.vault import (
    MASK_TOKEN_ENDPOINT_INDEX_PREFIX,
    MASK_TOKEN_EXPIRY_INDEX,
    MASK_TOKEN_TTL_SECONDS,
    MaskTokenBinding,
    MaskTokenVaultUnavailable,
    RedisMaskTokenVault,
)

FINGERPRINT_KEY = base64.b64encode(b"k" * 32).decode()


@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_vault_issues_fresh_digest_only_tokens_with_fixed_ttl():
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    binding = MaskTokenBinding(
        endpoint_id=7,
        workspace_id=11,
        table_id=13,
        row_id=17,
        field_id=19,
        policy_revision=2,
        access_generation=3,
        operation_class="preserve_cell",
        observed_row_state="2026-08-30T12:00:00+00:00",
        field_type="text",
    )

    first = vault.issue(binding, "Saudi national identifier")
    second = vault.issue(binding, "Saudi national identifier")

    assert first.envelope != second.envelope
    assert first.envelope == {"$jadawelProtected": {"v": 1, "token": first.raw_handle}}
    assert len(base64.urlsafe_b64decode(first.raw_handle + "=")) == 32

    digest = hashlib.sha256(first.raw_handle.encode()).hexdigest()
    stored = redis.get(f"jadawel:mcp-protection:v1:{digest}")
    assert stored is not None
    record = json.loads(stored)
    assert first.raw_handle not in stored
    assert "Saudi national identifier" not in stored
    assert record["field_id"] == 19
    assert record["operation_class"] == "preserve_cell"
    assert record["fingerprint_key_id"] == "current"
    assert len(record["value_fingerprint"]) == 64
    assert redis.ttl(f"jadawel:mcp-protection:v1:{digest}") == MASK_TOKEN_TTL_SECONDS


@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_vault_issues_one_atomic_batch_with_one_redis_script(monkeypatch):
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    binding = MaskTokenBinding(
        endpoint_id=7,
        workspace_id=11,
        table_id=13,
        row_id=17,
        field_id=19,
        policy_revision=2,
        access_generation=3,
        operation_class="preserve_cell",
        observed_row_state="2026-08-30T12:00:00+00:00",
        field_type="text",
    )
    script_calls = 0
    original_register_script = redis.register_script

    def register_counted_script(script):
        registered = original_register_script(script)

        def run_script(*args, **kwargs):
            nonlocal script_calls
            script_calls += 1
            return registered(*args, **kwargs)

        return run_script

    monkeypatch.setattr(redis, "register_script", register_counted_script)

    issued = vault.issue_many(
        [
            (binding, "first batch value"),
            (replace(binding, row_id=18), "second batch value"),
        ]
    )

    assert len(issued) == 2
    assert script_calls == 1
    assert issued[0].envelope != issued[1].envelope
    assert all(
        redis.exists(f"jadawel:mcp-protection:v1:{token.digest}") for token in issued
    )


@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_vault_rejects_an_over_capacity_batch_without_partial_records(monkeypatch):
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    monkeypatch.setattr(vault_module, "MAX_GLOBAL_TOKENS", 1)
    binding = MaskTokenBinding(
        endpoint_id=7,
        workspace_id=11,
        table_id=13,
        row_id=17,
        field_id=19,
        policy_revision=2,
        access_generation=3,
        operation_class="preserve_cell",
        observed_row_state="2026-08-30T12:00:00+00:00",
        field_type="text",
    )

    with pytest.raises(MaskTokenVaultUnavailable):
        vault.issue_many(
            [
                (binding, "first batch value"),
                (replace(binding, row_id=18), "second batch value"),
            ]
        )

    assert not list(redis.scan_iter(match="jadawel:mcp-protection:v1:" + "?" * 64))


@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_vault_collision_does_not_overwrite_or_release_the_existing_token(monkeypatch):
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    binding = MaskTokenBinding(
        endpoint_id=7,
        workspace_id=11,
        table_id=13,
        row_id=17,
        field_id=19,
        policy_revision=2,
        access_generation=3,
        operation_class="preserve_cell",
        observed_row_state="2026-08-30T12:00:00+00:00",
        field_type="text",
    )
    first = vault.issue(binding, "first value")
    key = f"jadawel:mcp-protection:v1:{first.digest}"
    original_record = redis.get(key)

    monkeypatch.setattr(
        vault_module,
        "generate_mask_token",
        lambda: vault_module.GeneratedMaskToken(first.raw_handle, first.digest),
    )

    with pytest.raises(MaskTokenVaultUnavailable):
        vault.issue(replace(binding, row_id=18), "second value")

    assert redis.get(key) == original_record
    assert redis.zcard(MASK_TOKEN_EXPIRY_INDEX) == 1
    assert redis.zcard(f"{MASK_TOKEN_ENDPOINT_INDEX_PREFIX}7") == 1


@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_vault_redeems_only_the_same_cell_and_current_value():
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    binding = MaskTokenBinding(
        endpoint_id=7,
        workspace_id=11,
        table_id=13,
        row_id=17,
        field_id=19,
        policy_revision=2,
        access_generation=3,
        operation_class="preserve_cell",
        observed_row_state="2026-08-30T12:00:00+00:00",
        field_type="text",
    )
    issued = vault.issue(binding, "same cell")
    handle = extract_mask_token_handle(issued.envelope)

    assert handle == issued.raw_handle
    assert vault.redeem(None, binding, "same cell") is False
    assert vault.redeem(handle, binding, "same cell") is True
    assert vault.redeem(handle, binding, "changed value") is False
    assert (
        vault.redeem(
            handle,
            replace(binding, row_id=18),
            "same cell",
        )
        is False
    )


@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
@pytest.mark.parametrize(
    "variant",
    [
        {"endpoint_id": 8},
        {"workspace_id": 12},
        {"table_id": 14},
        {"field_id": 20},
        {"policy_revision": 3},
        {"access_generation": 4},
        {"operation_class": "display_only"},
    ],
)
def test_vault_rejects_foreign_stale_and_display_only_bindings(variant):
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    binding = MaskTokenBinding(
        endpoint_id=7,
        workspace_id=11,
        table_id=13,
        row_id=17,
        field_id=19,
        policy_revision=2,
        access_generation=3,
        operation_class="preserve_cell",
        observed_row_state="2026-08-30T12:00:00+00:00",
        field_type="text",
    )
    issued = vault.issue(binding, "same cell")

    assert (
        vault.redeem(
            issued.raw_handle,
            replace(binding, **variant),
            "same cell",
        )
        is False
    )


@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_vault_expiry_revokes_a_token_without_plaintext_fallback():
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    binding = MaskTokenBinding(
        endpoint_id=7,
        workspace_id=11,
        table_id=13,
        row_id=17,
        field_id=19,
        policy_revision=2,
        access_generation=3,
        operation_class="preserve_cell",
        observed_row_state="2026-08-30T12:00:00+00:00",
        field_type="text",
    )
    issued = vault.issue(binding, "same cell")
    digest_key = f"jadawel:mcp-protection:v1:{issued.digest}"
    redis.expire(digest_key, -1)

    assert vault.redeem(issued.raw_handle, binding, "same cell") is False


@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_vault_capacity_is_reserved_atomically_and_released_on_cleanup(monkeypatch):
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    monkeypatch.setattr(vault_module, "MAX_GLOBAL_TOKENS", 1)
    binding = MaskTokenBinding(
        endpoint_id=7,
        workspace_id=11,
        table_id=13,
        row_id=17,
        field_id=19,
        policy_revision=2,
        access_generation=3,
        operation_class="preserve_cell",
        observed_row_state="2026-08-30T12:00:00+00:00",
        field_type="text",
    )

    first = vault.issue(binding, "first")
    with pytest.raises(MaskTokenVaultUnavailable):
        vault.issue(binding, "second")

    vault.delete([first.digest])
    second = vault.issue(binding, "second")
    assert second.digest != first.digest


@override_settings(
    MCP_PROTECTION_FINGERPRINT_KEYS={"current": FINGERPRINT_KEY},
    MCP_PROTECTION_ACTIVE_KEY_ID="current",
)
def test_production_vault_stops_issuance_at_memory_safety_floor(monkeypatch):
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    vault._enforce_memory_headroom = True
    monkeypatch.setattr(
        redis,
        "config_get",
        lambda name: (
            {"maxmemory": "100"}
            if name == "maxmemory"
            else {"maxmemory-policy": "noeviction"}
        ),
    )
    monkeypatch.setattr(redis, "info", lambda section: {"used_memory": 60})
    with pytest.raises(MaskTokenVaultUnavailable):
        vault.issue(
            MaskTokenBinding(
                endpoint_id=7,
                workspace_id=11,
                table_id=13,
                row_id=17,
                field_id=19,
                policy_revision=2,
                access_generation=3,
                operation_class="preserve_cell",
                observed_row_state="2026-08-30T12:00:00+00:00",
                field_type="text",
            ),
            "blocked at floor",
        )
