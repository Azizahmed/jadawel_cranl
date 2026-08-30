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
class MCPProtectedFieldBinding:
    field_id: int
    table_id: int
    field_name: str
    field_type: str


@dataclass(frozen=True, slots=True)
class MCPProtectionPolicyState:
    """The immutable policy snapshot used by one intercepted MCP call."""

    has_protected_fields: bool
    policy_id: int = 0
    revision: int = 0
    access_generation: int = 0
    protected_fields: tuple[MCPProtectedFieldBinding, ...] = ()


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
            or relation.field.trashed
            or relation.field.table.trashed
            or relation.field.table.database.trashed
        ):
            _raise_protection_unavailable()

        if relation.state == MCPProtectedFieldState.SUSPENDED:
            _raise_protection_unavailable()

    bindings = tuple(
        MCPProtectedFieldBinding(
            field_id=relation.field_id,
            table_id=relation.field.table_id,
            field_name=relation.field.name,
            field_type=relation.field.get_type().type,
        )
        for relation in protected_fields
        if relation.state == MCPProtectedFieldState.ACTIVE
    )
    return MCPProtectionPolicyState(
        has_protected_fields=bool(protected_fields),
        policy_id=policy.id,
        revision=policy.revision,
        access_generation=policy.access_generation,
        protected_fields=bindings,
    )


def _raise_protection_unavailable() -> Never:
    raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
