from dataclasses import dataclass
from typing import Never

from arabase.mcp.protection.models import (
    MCPProtectedFieldState,
    MCPProtectionLifecycleStatus,
    MCPProtectionPolicy,
    MCPProtectionSafeReason,
)
from jadawel.core.mcp.errors import MCPErrorCode, SafeMCPToolError
from jadawel.core.mcp.models import MCPEndpoint


@dataclass(frozen=True, slots=True)
class MCPProtectionPolicyState:
    """The minimum policy state needed by the generic interception boundary."""

    has_protected_fields: bool


EMPTY_MCP_PROTECTION_POLICY = MCPProtectionPolicyState(has_protected_fields=False)


def get_mcp_protection_policy_state(
    endpoint: MCPEndpoint,
) -> MCPProtectionPolicyState:
    """Load and validate the endpoint's explicit policy for one MCP call."""

    try:
        policy = MCPProtectionPolicy.objects.prefetch_related(
            "protected_fields__field__table__database"
        ).get(endpoint=endpoint)
    except MCPProtectionPolicy.DoesNotExist:
        _raise_protection_unavailable()

    if (
        policy.revision < 1
        or policy.access_generation < 1
        or policy.lifecycle_status != MCPProtectionLifecycleStatus.ACTIVE
        or policy.safe_reason_code != MCPProtectionSafeReason.NONE
    ):
        _raise_protection_unavailable()

    protected_fields = list(policy.protected_fields.all())
    for relation in protected_fields:
        if (
            relation.state
            not in (MCPProtectedFieldState.ACTIVE, MCPProtectedFieldState.SUSPENDED)
            or (
                relation.state == MCPProtectedFieldState.ACTIVE
                and relation.safe_reason_code != MCPProtectionSafeReason.NONE
            )
            or (
                relation.state == MCPProtectedFieldState.SUSPENDED
                and relation.safe_reason_code == MCPProtectionSafeReason.NONE
            )
            or relation.field.table.database.workspace_id != endpoint.workspace_id
        ):
            _raise_protection_unavailable()

    if not protected_fields:
        return EMPTY_MCP_PROTECTION_POLICY
    return MCPProtectionPolicyState(has_protected_fields=True)


def _raise_protection_unavailable() -> Never:
    raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
