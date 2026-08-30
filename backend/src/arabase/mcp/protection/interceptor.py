from collections.abc import Callable
from typing import Any

from django.db import transaction

from arabase.mcp.protection.contracts import (
    MCPToolOutputContract,
    get_mcp_tool_protection_contract,
)
from arabase.mcp.protection.egress import mask_direct_row_output
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

    contract = get_mcp_tool_protection_contract(tool.type)
    policy = get_mcp_protection_policy_state(endpoint)
    if not policy.has_protected_fields:
        return execute()
    if not policy.protected_fields:
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
    if contract.output in (
        MCPToolOutputContract.PUBLIC_METADATA,
        MCPToolOutputContract.MUTATION_RECEIPT,
    ):
        return execute()
    if tool.type not in ("list_table_rows", "create_rows", "update_rows"):
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
    if not any(field.table_id == args.table_id for field in policy.protected_fields):
        return execute()
    if tool.type == "list_table_rows" and getattr(args, "search", ""):
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)

    with transaction.atomic():
        result = execute()
        return mask_direct_row_output(endpoint, args, result, policy)
