from dataclasses import dataclass

from jadawel.core.mcp.models import MCPEndpoint


@dataclass(frozen=True, slots=True)
class MCPProtectionPolicyState:
    """The minimum policy state needed by the generic interception boundary."""

    has_protected_fields: bool


EMPTY_MCP_PROTECTION_POLICY = MCPProtectionPolicyState(has_protected_fields=False)


def get_mcp_protection_policy_state(
    endpoint: MCPEndpoint,
) -> MCPProtectionPolicyState:
    """Return the compatibility state until durable policies land in phase two."""

    return EMPTY_MCP_PROTECTION_POLICY
