import dataclasses

from django.contrib.auth.models import AbstractUser

from jadawel.core.action.registries import action_type_registry
from jadawel.core.mcp.actions import (
    CreateMCPEndpointActionType,
    DeleteMCPEndpointActionType,
)
from jadawel.core.mcp.handler import MCPEndpointHandler
from jadawel.core.mcp.models import MCPEndpoint
from jadawel.core.models import Workspace


class ContentBlindCreateMCPEndpointActionType(CreateMCPEndpointActionType):
    """Create an MCP endpoint without persisting its credential in action history."""

    @dataclasses.dataclass
    class Params:
        endpoint_id: int
        endpoint_name: str
        workspace_id: int
        workspace_name: str

    @classmethod
    def do(cls, user: AbstractUser, workspace: Workspace, name: str):
        endpoint = MCPEndpointHandler().create_endpoint(user, workspace, name)
        cls.register_action(
            user,
            cls.Params(endpoint.id, endpoint.name, workspace.id, workspace.name),
            cls.scope(workspace.id),
            workspace,
        )
        return endpoint


class ContentBlindDeleteMCPEndpointActionType(DeleteMCPEndpointActionType):
    """Delete an MCP endpoint without persisting its credential in action history."""

    @dataclasses.dataclass
    class Params:
        endpoint_id: int
        endpoint_name: str
        workspace_id: int
        workspace_name: str

    @classmethod
    def do(cls, user: AbstractUser, endpoint: MCPEndpoint):
        workspace = endpoint.workspace
        endpoint_id = endpoint.id
        endpoint_name = endpoint.name

        MCPEndpointHandler().delete_endpoint(user, endpoint)

        cls.register_action(
            user,
            cls.Params(endpoint_id, endpoint_name, workspace.id, workspace.name),
            cls.scope(workspace.id),
            workspace,
        )


def register_content_blind_mcp_action_types() -> None:
    for action_type in (
        ContentBlindCreateMCPEndpointActionType(),
        ContentBlindDeleteMCPEndpointActionType(),
    ):
        action_type_registry.unregister(action_type.type)
        action_type_registry.register(action_type)
