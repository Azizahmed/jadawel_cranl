from collections.abc import Callable
from typing import Any

from arabase.mcp.protection.contracts import get_mcp_tool_protection_contract
from arabase.mcp.protection.policy_state import get_mcp_protection_policy_state
from jadawel.core.mcp.errors import MCPErrorCode, SafeMCPToolError
from jadawel.core.mcp.models import MCPEndpoint
from jadawel.core.mcp.registries import MCPTool


def intercept_mcp_tool_call(
    endpoint: MCPEndpoint,
    tool: MCPTool,
    args: Any,
    execute: Callable[[], Any],
) -> Any:
    """Apply the declared MCP contract before executing a validated tool call."""

    get_mcp_tool_protection_contract(tool.type)
    policy = get_mcp_protection_policy_state(endpoint)
    if policy.has_protected_fields:
        raise SafeMCPToolError(
            MCPErrorCode.PROTECTION_UNAVAILABLE,
            retryable=False,
        )
    return execute()
