import json

from django.core.exceptions import ImproperlyConfigured

import pytest
from asgiref.sync import async_to_sync
from pydantic import BaseModel

from jadawel.core.mcp.registries import MCPTool, MCPToolRegistry, mcp_tool_registry


class EchoInput(BaseModel):
    value: str


class EchoMCPTool(MCPTool):
    type = "test_echo"
    input_schema = EchoInput

    def _sync_call(self, endpoint, args):
        return {"value": args.value}


def test_tool_call_preserves_behavior_without_interceptor(monkeypatch):
    monkeypatch.setattr(mcp_tool_registry, "_call_interceptor", None)

    content = async_to_sync(EchoMCPTool().call)(object(), {"value": "unchanged"})

    assert json.loads(content[0].text) == {"value": "unchanged"}


def test_tool_call_routes_validated_arguments_through_interceptor(monkeypatch):
    endpoint = object()
    observed = {}

    def interceptor(received_endpoint, tool, args, execute):
        observed.update(endpoint=received_endpoint, tool=tool, args=args)
        return {"intercepted": execute()}

    monkeypatch.setattr(
        mcp_tool_registry, "_call_interceptor", interceptor, raising=False
    )

    content = async_to_sync(EchoMCPTool().call)(endpoint, {"value": "validated"})

    assert json.loads(content[0].text) == {"intercepted": {"value": "validated"}}
    assert observed == {
        "endpoint": endpoint,
        "tool": observed["tool"],
        "args": EchoInput(value="validated"),
    }
    assert isinstance(observed["tool"], EchoMCPTool)


def test_tool_registry_rejects_a_second_call_interceptor():
    registry = MCPToolRegistry()
    first = lambda endpoint, tool, args, execute: execute()
    second = lambda endpoint, tool, args, execute: execute()

    registry.register_call_interceptor(first)

    with pytest.raises(ImproperlyConfigured):
        registry.register_call_interceptor(second)
