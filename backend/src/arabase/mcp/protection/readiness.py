import secrets
from dataclasses import dataclass

from django.db.models import F, Q

from redis.exceptions import RedisError

from arabase.mcp.protection.models import (
    MCPProtectedField,
    MCPProtectedFieldState,
    MCPProtectionLifecycleStatus,
    MCPProtectionPolicy,
    MCPProtectionSafeReason,
)
from arabase.mcp.protection.vault import MaskTokenVaultUnavailable, get_mask_token_vault
from jadawel.core.mcp.models import MCPEndpoint


@dataclass(frozen=True, slots=True)
class MCPProtectionReadiness:
    ready: bool
    safe_reason_code: str


def check_mcp_protection_policy_readiness() -> MCPProtectionReadiness:
    """Prove the durable endpoint-policy invariants without reading cell data."""

    endpoint_count = MCPEndpoint.objects.count()
    policy_count = MCPProtectionPolicy.objects.count()
    if endpoint_count != policy_count:
        return MCPProtectionReadiness(
            False, MCPProtectionSafeReason.POLICY_COUNT_MISMATCH
        )

    invalid_policy_exists = MCPProtectionPolicy.objects.filter(
        Q(revision__lt=1)
        | Q(access_generation__lt=1)
        | ~Q(lifecycle_status__in=MCPProtectionLifecycleStatus.values)
        | Q(
            lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE,
            safe_reason_code__gt="",
        )
        | (
            ~Q(lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE)
            & Q(safe_reason_code="")
        )
    ).exists()
    if invalid_policy_exists:
        return MCPProtectionReadiness(
            False, MCPProtectionSafeReason.POLICY_STATE_INVALID
        )

    invalid_relation_exists = (
        MCPProtectedField.objects.annotate(
            endpoint_workspace_id=F("policy__endpoint__workspace_id"),
            field_workspace_id=F("field__table__database__workspace_id"),
        )
        .filter(
            ~Q(state__in=MCPProtectedFieldState.values)
            | Q(state=MCPProtectedFieldState.ACTIVE, safe_reason_code__gt="")
            | Q(state=MCPProtectedFieldState.SUSPENDED, safe_reason_code="")
            | Q(field__trashed=True)
            | Q(field__table__trashed=True)
            | Q(field__table__database__trashed=True)
            | ~Q(endpoint_workspace_id=F("field_workspace_id"))
        )
        .exists()
    )
    if invalid_relation_exists:
        return MCPProtectionReadiness(
            False, MCPProtectionSafeReason.POLICY_RELATION_INVALID
        )

    if MCPProtectedField.objects.filter(
        state=MCPProtectedFieldState.ACTIVE,
        policy__lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE,
    ).exists():
        try:
            vault = get_mask_token_vault()
            redis = vault.redis
            redis.ping()
            config_get = getattr(redis, "config_get", None)
            if config_get is None:
                raise RedisError("Redis configuration cannot be verified")
            memory = config_get("maxmemory")
            policy = config_get("maxmemory-policy")
            maxmemory = int(memory.get("maxmemory", 0))
            if maxmemory <= 0 or policy.get("maxmemory-policy") != "noeviction":
                raise RedisError("Redis is not a bounded noeviction vault")
            info = redis.info("memory")
            used_memory = int(info.get("used_memory", 0))
            if used_memory / maxmemory >= 0.60:
                raise RedisError("Redis memory headroom is below the safety floor")
            canary_key = f"jadawel:mcp-protection:readiness:{secrets.token_hex(8)}"
            if not redis.set(canary_key, "1", ex=5, nx=True):
                raise RedisError("Redis readiness canary could not be written")
            if redis.get(canary_key) != "1":
                raise RedisError("Redis readiness canary could not be read")
            redis.delete(canary_key)
        except (MaskTokenVaultUnavailable, RedisError, OSError, ValueError, TypeError):
            return MCPProtectionReadiness(
                False, MCPProtectionSafeReason.PROTECTION_REDIS_UNAVAILABLE
            )

    return MCPProtectionReadiness(True, MCPProtectionSafeReason.NONE)
