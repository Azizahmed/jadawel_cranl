from enum import StrEnum


class MCPErrorCode(StrEnum):
    ACCESS_DENIED = "MCP_ACCESS_DENIED"
    TOOL_NOT_FOUND = "MCP_TOOL_NOT_FOUND"
    TOOL_FAILED = "MCP_TOOL_FAILED"
    PROTECTION_UNAVAILABLE = "PROTECTION_UNAVAILABLE"


class SafeMCPToolError(Exception):
    """A content-blind MCP failure that is safe to map to the protocol."""

    def __init__(self, code: MCPErrorCode, *, retryable: bool):
        super().__init__(code.value)
        self.code = code
        self.retryable = retryable
