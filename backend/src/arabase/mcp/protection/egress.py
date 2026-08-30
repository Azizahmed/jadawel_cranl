from copy import deepcopy
from typing import Any, Never

from arabase.mcp.protection.models import (
    MCPProtectedFieldState,
    MCPProtectionLifecycleStatus,
    MCPProtectionPolicy,
    MCPProtectionSafeReason,
)
from arabase.mcp.protection.policy_state import MCPProtectionPolicyState
from arabase.mcp.protection.vault import (
    MaskTokenBinding,
    MaskTokenVaultUnavailable,
    get_mask_token_vault,
)
from jadawel.contrib.database.table.models import Table
from jadawel.core.mcp.errors import MCPErrorCode, SafeMCPToolError
from jadawel.core.mcp.models import MCPEndpoint


def mask_direct_row_output(
    endpoint: MCPEndpoint,
    args: Any,
    result: Any,
    policy: MCPProtectionPolicyState,
) -> Any:
    """Replace direct protected cells with fresh same-cell mask tokens."""

    table_id = args.table_id
    fields = tuple(
        field for field in policy.protected_fields if field.table_id == table_id
    )
    if not fields:
        return result

    output = deepcopy(result)
    rows = output["results"] if isinstance(output, dict) else output
    if not isinstance(rows, list):
        _raise_protection_unavailable()

    table = Table.objects.get(id=table_id, database__workspace_id=endpoint.workspace_id)
    model = table.get_model()
    row_ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if len(row_ids) != len(rows) or any(row_id is None for row_id in row_ids):
        _raise_protection_unavailable()
    observed_rows = model.objects.in_bulk(row_ids)
    if len(observed_rows) != len(row_ids):
        _raise_protection_unavailable()

    vault = None
    issued_digests: list[str] = []
    try:
        vault = get_mask_token_vault()
        for row in rows:
            observed_row = observed_rows[row["id"]]
            observed_state = observed_row.updated_on.isoformat()
            for field in fields:
                if field.field_name not in row:
                    _raise_protection_unavailable()
                value = row[field.field_name]
                if _is_empty_value(value):
                    continue
                issued = vault.issue(
                    MaskTokenBinding(
                        endpoint_id=endpoint.id,
                        workspace_id=endpoint.workspace_id,
                        table_id=table_id,
                        row_id=row["id"],
                        field_id=field.field_id,
                        policy_revision=policy.revision,
                        access_generation=policy.access_generation,
                        operation_class="preserve_cell",
                        observed_row_state=observed_state,
                        field_type=field.field_type,
                    ),
                    value,
                )
                issued_digests.append(issued.digest)
                row[field.field_name] = issued.envelope
        _assert_policy_unchanged(endpoint, policy)
    except (MaskTokenVaultUnavailable, SafeMCPToolError):
        if vault is not None:
            vault.delete(issued_digests)
        _raise_protection_unavailable()
    return output


def _assert_policy_unchanged(
    endpoint: MCPEndpoint, snapshot: MCPProtectionPolicyState
) -> None:
    try:
        current = MCPProtectionPolicy.objects.get(
            id=snapshot.policy_id,
            endpoint=endpoint,
            revision=snapshot.revision,
            access_generation=snapshot.access_generation,
            lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE,
            safe_reason_code=MCPProtectionSafeReason.NONE,
        )
    except MCPProtectionPolicy.DoesNotExist:
        _raise_protection_unavailable()
    current_field_ids = set(
        current.protected_fields.filter(
            state=MCPProtectedFieldState.ACTIVE
        ).values_list("field_id", flat=True)
    )
    if current_field_ids != {field.field_id for field in snapshot.protected_fields}:
        _raise_protection_unavailable()


def _is_empty_value(value: Any) -> bool:
    return (
        value is None
        or value == ""
        or (isinstance(value, (list, dict, tuple)) and len(value) == 0)
    )


def _raise_protection_unavailable() -> Never:
    raise SafeMCPToolError(MCPErrorCode.PROTECTION_UNAVAILABLE, retryable=False)
