import json
import logging
from uuid import uuid4

from asgiref.sync import async_to_sync

from jadawel.core.mcp.sse import DjangoChannelsSseServerTransport


def test_post_message_does_not_log_raw_mcp_content(caplog):
    canary = "PROTECTED-SSE-CANARY"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "list_table_rows",
                "arguments": {"search": canary},
            },
        }
    ).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/mcp/messages/",
        "raw_path": b"/mcp/messages/",
        "query_string": f"session_id={uuid4().hex}".encode(),
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    sent = []
    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    caplog.set_level(logging.DEBUG, logger="jadawel.core.mcp.sse")

    async_to_sync(
        DjangoChannelsSseServerTransport("/mcp/messages/").handle_post_message
    )(scope, receive, send)

    assert any(message.get("status") == 202 for message in sent)
    assert canary not in caplog.text
