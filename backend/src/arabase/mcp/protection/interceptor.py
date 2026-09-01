from collections.abc import Callable
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from arabase.mcp.protection.audit import content_blind_mcp_mutation
from arabase.mcp.protection.contracts import (
    MCPToolOutputContract,
    get_mcp_tool_protection_contract,
)
from arabase.mcp.protection.egress import (
    MAX_ISSUED_OR_REDEEMED_PER_CALL,
    MAX_ROWS_PER_CALL,
    mask_direct_row_output,
    table_has_protected_output,
)
from arabase.mcp.protection.models import (
    MCPProtectedFieldState,
    MCPProtectionLifecycleStatus,
    MCPProtectionPolicy,
    MCPProtectionSafeReason,
)
from arabase.mcp.protection.policy_state import get_mcp_protection_policy_state
from arabase.mcp.protection.tokens import extract_mask_token_handle
from arabase.mcp.protection.vault import (
    MaskTokenBinding,
    MaskTokenVaultUnavailable,
    get_mask_token_vault,
)
from jadawel.contrib.database.api.rows.serializers import serialize_rows_for_response
from jadawel.contrib.database.mcp import services
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

    # Load the durable policy before resolving the contract.  An unprotected
    # endpoint must remain compatible with an additive tool that has not yet
    # opted into the inventory, while a non-empty policy must fail closed with
    # the same fixed protection error rather than leaking a configuration
    # traceback.
    policy = get_mcp_protection_policy_state(endpoint)
    if tool.type == "create_rows":
        # The reserved envelope is never an ordinary user value, even for an
        # endpoint whose policy is currently empty.
        _reject_token_envelopes(args.rows)
    # A mask envelope is an authority-bearing handle, never an ordinary cell
    # value.  Reject it even when the policy is empty or the target table is
    # outside the protected set.  The only supported update path is a
    # same-cell redemption on a table with a direct protected field, which is
    # validated below.
    if (
        tool.type == "update_rows"
        and any(_contains_token_marker(_row_payload(row)) for row in args.rows)
        and (
            not policy.has_protected_fields
            or not any(
                field.table_id == args.table_id for field in policy.protected_fields
            )
        )
    ):
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
    try:
        contract = get_mcp_tool_protection_contract(tool.type)
    except ImproperlyConfigured as exc:
        if not policy.has_protected_fields:
            return execute()
        raise SafeMCPToolError(
            MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False
        ) from exc
    if not policy.has_protected_fields:
        return execute()
    if not policy.protected_fields:
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
    if contract.output in (
        MCPToolOutputContract.PUBLIC_METADATA,
        MCPToolOutputContract.MUTATION_RECEIPT,
    ):
        return execute()
    # Page tools own their artifact draft/approval and runtime projection
    # checks.  They must not be treated as ordinary row tools (which would
    # incorrectly reject every protected page call before the service can
    # return safe metadata or create a draft).
    if tool.type in {
        "get_page_view",
        "create_page_view",
        "update_page_view",
        "list_page_view_revisions",
        "restore_page_view_revision",
    }:
        return execute()
    if tool.type not in ("list_table_rows", "create_rows", "update_rows"):
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
    if tool.type == "list_table_rows" and not table_has_protected_output(
        args.table_id, policy.protected_fields, endpoint.workspace_id
    ):
        return execute()
    if tool.type != "list_table_rows" and not any(
        field.table_id == args.table_id for field in policy.protected_fields
    ):
        return execute()
    if tool.type == "list_table_rows" and args.size > MAX_ROWS_PER_CALL:
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
    if (
        tool.type in ("create_rows", "update_rows")
        and len(args.rows) > MAX_ROWS_PER_CALL
    ):
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
    if tool.type == "list_table_rows" and getattr(args, "search", ""):
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)

    with transaction.atomic():
        _lock_policy_snapshot(endpoint, policy)
        restore = None
        try:
            if tool.type == "create_rows":
                # The global check above also covers unprotected tables.  Keep
                # this local check for clarity if the interceptor is changed to
                # admit another create path later.
                _reject_token_envelopes(args.rows)
            elif tool.type == "update_rows":
                restore = _prepare_update_for_protected_cells(endpoint, args, policy)
            if tool.type in ("create_rows", "update_rows"):
                with content_blind_mcp_mutation(
                    endpoint=endpoint,
                    tool_type=tool.type,
                    table_id=args.table_id,
                    row_count=len(args.rows),
                    policy_revision=policy.revision,
                    access_generation=policy.access_generation,
                    protected_field_ids=tuple(
                        field.field_id
                        for field in policy.protected_fields
                        if field.table_id == args.table_id
                    ),
                ):
                    result = execute()
            else:
                result = execute()
            return mask_direct_row_output(endpoint, args, result, policy)
        finally:
            if restore is not None:
                restore()


def _lock_policy_snapshot(endpoint: MCPEndpoint, snapshot) -> None:
    """Keep policy identity stable through the mutation and response masking."""

    try:
        current = MCPProtectionPolicy.objects.select_for_update().get(
            id=snapshot.policy_id,
            endpoint=endpoint,
            revision=snapshot.revision,
            access_generation=snapshot.access_generation,
            lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE,
            safe_reason_code=MCPProtectionSafeReason.NONE,
        )
    except MCPProtectionPolicy.DoesNotExist:
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
    active_ids = set(
        current.protected_fields.filter(
            state=MCPProtectedFieldState.ACTIVE
        ).values_list("field_id", flat=True)
    )
    if active_ids != {field.field_id for field in snapshot.protected_fields}:
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)


def _reject_token_envelopes(value: Any) -> None:
    """Reject handles on create and in every non-redemption input position."""

    if isinstance(value, dict):
        if "$jadawelProtected" in value:
            raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
        for nested in value.values():
            _reject_token_envelopes(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_token_envelopes(nested)


def _prepare_update_for_protected_cells(endpoint, args, policy):
    """Validate and temporarily redeem same-cell tokens for one whole batch."""

    table = services.get_table(endpoint.user, endpoint.workspace, args.table_id)
    model = table.get_model()
    fields = {
        field.field_name: field
        for field in policy.protected_fields
        if field.table_id == args.table_id
    }
    row_ids = [row.id for row in args.rows]
    if len(set(row_ids)) != len(row_ids):
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
    locked_rows = model.objects.select_for_update().filter(id__in=row_ids)
    locked_by_id = {row.id: row for row in locked_rows}
    if len(locked_by_id) != len(row_ids):
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
    serialized_rows = serialize_rows_for_response(
        list(locked_by_id.values()), model, user_field_names=True
    )
    serialized_by_id = {row["id"]: row for row in serialized_rows}
    vault = None
    originals = []
    redeemed_count = 0
    try:
        for spec in args.rows:
            extras = spec.__pydantic_extra__ or {}
            for name, value in list(extras.items()):
                protected_field = fields.get(name)
                has_marker = _contains_token_marker(value)
                if not has_marker:
                    continue
                if protected_field is None:
                    raise SafeMCPToolError(
                        MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False
                    )
                handle = extract_mask_token_handle(value)
                if handle is None:
                    raise SafeMCPToolError(
                        MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False
                    )
                current = serialized_by_id[spec.id]
                if name not in current:
                    raise SafeMCPToolError(
                        MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False
                    )
                observed_row = locked_by_id[spec.id]
                vault = vault or get_mask_token_vault()
                valid = vault.redeem(
                    handle,
                    MaskTokenBinding(
                        endpoint_id=endpoint.id,
                        workspace_id=endpoint.workspace_id,
                        table_id=args.table_id,
                        row_id=spec.id,
                        field_id=protected_field.field_id,
                        policy_revision=policy.revision,
                        access_generation=policy.access_generation,
                        operation_class="preserve_cell",
                        observed_row_state=observed_row.updated_on.isoformat(),
                        field_type=protected_field.field_type,
                    ),
                    current[name],
                )
                if not valid:
                    raise SafeMCPToolError(
                        MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False
                    )
                redeemed_count += 1
                if redeemed_count > MAX_ISSUED_OR_REDEEMED_PER_CALL:
                    raise SafeMCPToolError(
                        MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False
                    )
                originals.append((spec, name, value))
                spec.__pydantic_extra__[name] = current[name]
    except MaskTokenVaultUnavailable:
        raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)

    def restore() -> None:
        for spec, name, value in originals:
            if spec.__pydantic_extra__ is not None:
                spec.__pydantic_extra__[name] = value

    return restore


def _contains_token_marker(value: Any) -> bool:
    if isinstance(value, dict):
        return "$jadawelProtected" in value or any(
            _contains_token_marker(nested) for nested in value.values()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_token_marker(nested) for nested in value)
    return False


def _row_payload(row: Any) -> Any:
    """Return a row-update payload without trusting arbitrary model objects."""

    extras = getattr(row, "__pydantic_extra__", None)
    if extras is not None:
        return {"id": getattr(row, "id", None), **extras}
    if isinstance(row, dict):
        return row
    return None
