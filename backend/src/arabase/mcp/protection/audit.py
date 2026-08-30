from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator

from arabase.mcp.protection.models import MCPProtectionMutationAudit


@dataclass(frozen=True, slots=True)
class MCPMutationAuditContext:
    endpoint_id: int
    actor_id: int
    tool_type: str
    table_id: int
    row_count: int
    policy_revision: int
    access_generation: int
    protected_field_ids: tuple[int, ...]


_active_context: ContextVar[MCPMutationAuditContext | None] = ContextVar(
    "mcp_protection_audit_context", default=None
)


def is_content_blind_mcp_mutation() -> bool:
    return _active_context.get() is not None


@contextmanager
def content_blind_mcp_mutation(
    *,
    endpoint,
    tool_type: str,
    table_id: int,
    row_count: int,
    policy_revision: int,
    access_generation: int,
    protected_field_ids: tuple[int, ...],
) -> Iterator[None]:
    context = MCPMutationAuditContext(
        endpoint_id=endpoint.id,
        actor_id=endpoint.user_id,
        tool_type=tool_type,
        table_id=table_id,
        row_count=row_count,
        policy_revision=policy_revision,
        access_generation=access_generation,
        protected_field_ids=protected_field_ids,
    )
    token = _active_context.set(context)
    try:
        yield
    except Exception:
        raise
    else:
        MCPProtectionMutationAudit.objects.create(
            endpoint_id=context.endpoint_id,
            actor_id=context.actor_id,
            tool_type=context.tool_type,
            table_id=context.table_id,
            row_count=context.row_count,
            outcome="success",
            policy_revision=context.policy_revision,
            access_generation=context.access_generation,
            protected_field_ids=list(context.protected_field_ids),
        )
    finally:
        _active_context.reset(token)
