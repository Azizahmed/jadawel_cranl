from abc import ABC

from jadawel.core.mcp.object_scopes import MCPEndpointObjectScopeType
from jadawel.core.operations import WorkspaceCoreOperationType
from jadawel.core.registries import OperationType


class CreateMCPEndpointOperationType(WorkspaceCoreOperationType):
    type = "workspace.create_mcp_endpoint"


class MCPEndpointOperationType(OperationType, ABC):
    context_scope_name = MCPEndpointObjectScopeType.type


class ReadMCPEndpointOperationType(MCPEndpointOperationType):
    type = "workspace.mcp_endpoint.read"


class UpdateMCPEndpointOperationType(MCPEndpointOperationType):
    type = "workspace.mcp_endpoint.update"


class DeleteMCPEndpointOperationType(MCPEndpointOperationType):
    type = "workspace.mcp_endpoint.delete"
