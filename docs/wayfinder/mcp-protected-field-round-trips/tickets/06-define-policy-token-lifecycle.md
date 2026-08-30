---
title: "Define protected-field and mask-token lifecycle rules"
labels:
  - "wayfinder:grilling"
status: closed
assignee: codex
parent: ../map.md
blocked_by:
  - "[Define mask-token interaction semantics](02-define-mask-token-semantics.md)"
  - "[Choose and validate the mask-token architecture](03-choose-mask-token-architecture.md)"
---

## Question

What happens to policies and outstanding tokens when a field is renamed, deleted,
converted, newly protected, or unprotected; an endpoint key is rotated or endpoint
deleted; workspace membership changes; or a protected cell changes concurrently?

## Resolution

- Bind policy entries to stable field IDs. Renaming a field updates display metadata
  without changing policy membership, raising the policy revision, or invalidating
  otherwise valid tokens.
- Preserve protection across a supported field-type conversion, but raise the policy
  revision and invalidate all existing endpoint tokens. Block conversion to a type
  that the protected-value propagation contract cannot safely cover until the field
  is explicitly unprotected or that type is supported.
- When a protected field is trashed, retain a suspended protection entry and
  invalidate all endpoint tokens. Restoring that same field ID automatically
  reactivates protection before MCP access resumes. Permanent deletion removes the
  suspended entry but preserves its audit history.
- Apply each protection-policy edit atomically, increment its endpoint-wide revision
  once, and invalidate every outstanding token for that endpoint without a grace
  period. A concurrent MCP call must recheck the revision and fail completely with a
  fixed safe retryable error rather than using mixed policy state.
- Rotating an endpoint key preserves its policy but immediately invalidates the old
  key, active connections, and every outstanding mask token. Deleting the endpoint
  invalidates all of them permanently; orphaned vault records remain unusable and
  expire through their existing TTL.
- If the endpoint owner loses workspace membership, suspend the endpoint immediately,
  invalidate its tokens, and retain its policy. Regaining membership does not
  reactivate it automatically; the owner must explicitly reactivate after recovering
  sufficient permissions. A workspace administrator may delete a suspended endpoint,
  but ownership is never transferred implicitly.
- Make protection and unprotection effective atomically at policy commit. A call that
  began on an older revision must fail before response release or mutation commit.
  Future calls mask newly protected fields and expose explicitly unprotected fields;
  unprotection requires a path-specific confirmation and a warning that already
  disclosed plaintext cannot be recalled.
- Increment the endpoint access generation and invalidate outstanding tokens whenever
  the owner's effective workspace permissions change. Keep the endpoint active while
  the owner remains an active member, but re-evaluate every tool against current
  permissions. Suspending or marking the account for deletion suspends the endpoint;
  permanent account deletion removes its endpoints and policies.
- Never inherit protection by name or by copied data. Duplicated fields, tables, and
  databases have new identities and start unprotected. Trashing a table or database
  suspends all contained protection entries; restoring those same identities
  reactivates them before MCP access. Permanent hierarchy deletion removes the
  entries, and workspace deletion removes its endpoints and policies.
- Enforce bulk revocation by checking durable policy revision and endpoint access
  generation, not by synchronously scanning Redis. Vault-record deletion is
  best-effort cleanup; any remaining records stay unusable and expire by TTL.
- On token redemption, lock the row and recheck its `updated_on` and protected-value
  fingerprint. Any concurrent change, including an unrelated field change, makes the
  token stale and rejects the whole batch without automatic retry; the caller must
  reread and retry with fresh tokens.
- Reactivating a suspended endpoint requires the restored owner to review the policy
  and explicitly reactivate with sufficient current permissions. Reactivation always
  issues a new endpoint key and increments the access generation; an old key never
  becomes valid again.
- Retain suspended endpoints and their policies without automatic expiry. They remain
  until explicitly deleted by the restored owner or a workspace administrator, or
  until the owner account or workspace is permanently deleted.
- Apply every schema lifecycle event atomically across all endpoint policies that
  protect the affected field. If any policy entry cannot be suspended, restored, or
  revisioned, roll back the schema mutation rather than leaving endpoints on mixed
  protection state.
- Do not block ordinary data restoration merely because protection validation fails.
  Keep the affected entry suspended and mark every affected endpoint as
  protection-blocked; all MCP calls fail closed with a fixed safe error until
  validation succeeds or the owner explicitly repairs the policy.
- Emit one content-blind audit event for each policy change, suspension, reactivation,
  key rotation, deletion, or protection-relevant schema change. Notify the owner in
  Jadawel when an endpoint is suspended, protection-blocked, or key-rotated, and
  notify workspace administrators when an endpoint is suspended without an effective
  owner. Never create per-token revocation notifications or include values, tokens,
  keys, or field names in lifecycle telemetry.
