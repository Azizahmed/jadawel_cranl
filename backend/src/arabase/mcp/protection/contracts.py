from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured

if TYPE_CHECKING:
    from jadawel.core.mcp.registries import MCPTool


class MCPToolInputContract(StrEnum):
    PUBLIC_METADATA = "public_metadata"
    PROTECTED_QUERY = "protected_query"
    PROTECTED_VALUES = "protected_values"
    PROTECTED_ARTIFACT = "protected_artifact"


class MCPToolOutputContract(StrEnum):
    PROTECTED_STRUCTURED = "protected_structured"
    PUBLIC_METADATA = "public_metadata"
    MUTATION_RECEIPT = "mutation_receipt"


class MCPToolOperationClass(StrEnum):
    """The protection boundary's coarse operation class for one MCP tool."""

    METADATA = "metadata"
    QUERY = "query"
    MUTATION = "mutation"
    ARTIFACT = "artifact"


@dataclass(frozen=True, slots=True)
class MCPToolProtectionContract:
    input: MCPToolInputContract
    output: MCPToolOutputContract
    operation_class: MCPToolOperationClass = MCPToolOperationClass.METADATA


PUBLIC_METADATA = MCPToolProtectionContract(
    MCPToolInputContract.PUBLIC_METADATA,
    MCPToolOutputContract.PUBLIC_METADATA,
    MCPToolOperationClass.METADATA,
)
PROTECTED_QUERY = MCPToolProtectionContract(
    MCPToolInputContract.PROTECTED_QUERY,
    MCPToolOutputContract.PROTECTED_STRUCTURED,
    MCPToolOperationClass.QUERY,
)
PROTECTED_VALUES = MCPToolProtectionContract(
    MCPToolInputContract.PROTECTED_VALUES,
    MCPToolOutputContract.PROTECTED_STRUCTURED,
    MCPToolOperationClass.MUTATION,
)
PROTECTED_ARTIFACT = MCPToolProtectionContract(
    MCPToolInputContract.PROTECTED_ARTIFACT,
    MCPToolOutputContract.PROTECTED_STRUCTURED,
    MCPToolOperationClass.ARTIFACT,
)
MUTATION_RECEIPT = MCPToolProtectionContract(
    MCPToolInputContract.PUBLIC_METADATA,
    MCPToolOutputContract.MUTATION_RECEIPT,
    MCPToolOperationClass.MUTATION,
)


MCP_TOOL_PROTECTION_CONTRACTS = {
    "list_databases": PUBLIC_METADATA,
    "create_database": PUBLIC_METADATA,
    "list_tables": PUBLIC_METADATA,
    "create_table": PUBLIC_METADATA,
    "update_table": PUBLIC_METADATA,
    "delete_table": MUTATION_RECEIPT,
    "get_table_schema": PUBLIC_METADATA,
    "create_fields": PUBLIC_METADATA,
    "update_fields": PUBLIC_METADATA,
    "delete_fields": MUTATION_RECEIPT,
    "list_table_rows": PROTECTED_QUERY,
    "create_rows": PROTECTED_VALUES,
    "update_rows": PROTECTED_VALUES,
    "delete_rows": MUTATION_RECEIPT,
    "list_page_views": PUBLIC_METADATA,
    "get_page_view": PROTECTED_QUERY,
    "create_page_view": PROTECTED_ARTIFACT,
    "update_page_view": PROTECTED_ARTIFACT,
    "list_page_view_revisions": PROTECTED_QUERY,
    "restore_page_view_revision": PROTECTED_ARTIFACT,
}


def get_mcp_tool_protection_contract(tool_name: str) -> MCPToolProtectionContract:
    try:
        return MCP_TOOL_PROTECTION_CONTRACTS[tool_name]
    except KeyError as exc:
        raise ImproperlyConfigured(
            f"MCP tool '{tool_name}' has no protection contract."
        ) from exc


def validate_mcp_tool_protection_contracts(tools: Iterable[MCPTool]) -> None:
    from jadawel.core.mcp.registries import MCPTool

    for tool in tools:
        if tool.__class__.call is not MCPTool.call:
            raise ImproperlyConfigured(
                f"MCP tool '{tool.type}' bypasses the protected call boundary."
            )
        get_mcp_tool_protection_contract(tool.type)
