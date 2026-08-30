from dataclasses import dataclass

from django.db.models import F, Q

from arabase.mcp.protection.models import (
    MCPProtectedField,
    MCPProtectedFieldState,
    MCPProtectionLifecycleStatus,
    MCPProtectionPolicy,
    MCPProtectionSafeReason,
)
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
            | ~Q(endpoint_workspace_id=F("field_workspace_id"))
        )
        .exists()
    )
    if invalid_relation_exists:
        return MCPProtectionReadiness(
            False, MCPProtectionSafeReason.POLICY_RELATION_INVALID
        )

    return MCPProtectionReadiness(True, MCPProtectionSafeReason.NONE)
