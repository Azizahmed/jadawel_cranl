---
title: "Choose the fork-safe policy persistence and API model"
labels:
  - "wayfinder:prototype"
status: closed
assignee: codex
parent: ../map.md
blocked_by:
  - "[Choose and validate the mask-token architecture](03-choose-mask-token-architecture.md)"
  - "[Design the endpoint protection-policy experience](05-design-protection-policy-ux.md)"
  - "[Define protected-field and mask-token lifecycle rules](06-define-policy-token-lifecycle.md)"
prototype_branch: codex/prototype-mcp-policy-persistence
prototype_commit: 45813829178c004a3ab0a5ca2dc8d14857271545
prototype_asset: backend/src/arabase/mcp/protection/policy_persistence.prototype.html
prototype_verdict: "Use an explicit Arabase one-to-one policy header with normalized protected-field rows"
---

## Question

Which model, ownership boundary, API shape, migration strategy, and action/audit
integration preserve stable field identity and lifecycle behavior while respecting
Jadawel's additive `arabase` fork boundary and minimizing upstream core edits?

## Resolution

- Keep persistence, services, lifecycle handling, migrations, and companion APIs in
  `arabase.mcp.protection`. Do not add policy fields or relations to the upstream
  `MCPEndpoint` model. Add only the smallest generic core enforcement or lifecycle
  hook that a later containment prototype proves unavoidable, and record any such
  patch in `PATCHES.md`.
- Store one explicit Arabase policy row per endpoint using a one-to-one relation, with
  policy revision, endpoint access generation, lifecycle status, safe reason code,
  and timestamps. Store protected fields as normalized relation rows with policy and
  stable `database.Field` foreign keys, active/suspended state, safe reason code, a
  unique `(policy, field)` constraint, and reverse-lookup indexes. Never persist field
  names, paths, or a JSON list of IDs in the policy.
- Backfill every existing endpoint with an explicit active empty policy and initial
  revision/access generation in a new forward-only Arabase migration. Every creation
  path, including the legacy core API when protection fields are omitted, must create
  an explicit empty row. After rollout, a missing policy row is an integrity failure
  and every MCP call fails closed; absence never means an empty policy.
- The throwaway logic prototype confirmed atomic endpoint/policy creation rollback,
  cross-workspace field rejection, full-set optimistic revision checks, retained
  suspended relations through trash/restore, stale in-flight call rejection, and
  fail-closed handling of a missing policy row without modifying production code.
- Add an Arabase composite create endpoint at `/api/arabase/mcp/endpoints/` and
  companion read/replace endpoints at
  `/api/arabase/mcp/endpoints/{id}/protection-policy/`. Keep the existing core create
  payload compatible, but ensure it also creates an explicit empty policy. Never
  expose a newly valid endpoint key before its requested policy commits in the same
  transaction.
- Replace a policy only through a full-set `PUT` carrying `expected_revision`. Lock
  the endpoint and policy, require an exact unique set of existing, active, supported
  field IDs from the endpoint workspace, replace relation rows, and increment the
  revision once. Return `409 POLICY_REVISION_CONFLICT` on stale input and never apply
  a partial set.
- Centralize persistent lifecycle changes in one Arabase service. Wire field, table,
  database, and workspace lifecycle hooks because bulk hierarchy trash does not emit
  one field-deletion signal per field. Keep schema and policy changes in one database
  transaction; defer notifications and best-effort vault cleanup with
  `transaction.on_commit`.
- Create a new forward-only Arabase migration depending on the then-current Arabase,
  core, and database migration heads. Add schema and indexes, then batch-backfill an
  active empty policy with initial revision/access generation for every endpoint.
  Gate MCP readiness on complete backfill. Before feature activation the new tables
  may be reversed; after a non-empty policy exists, operational rollback must retain
  the schema and fail MCP closed rather than run code that cannot enforce protection.
- Do not treat the current non-undoable `ActionType` stream as the durable audit log.
  Add an append-only Arabase protection-audit model written in the same transaction,
  containing only approved identifiers, revisions, outcomes, and safe reason codes.
  Replace the registry entries for existing MCP actions with content-blind variants,
  and never make policy weakening automatically undoable.
- Keep normal policy management owner-only: the owner may read or replace the policy,
  rotate the key, reactivate, and delete the endpoint subject to current permissions.
  A workspace administrator may see only safe status/reason/count metadata and delete
  a suspended or protection-blocked endpoint with no effective owner; an administrator
  may not edit, reactivate, rotate, read its key, or take ownership.
- Return endpoint/workspace IDs, policy revision, lifecycle status, safe reason, and
  selected field IDs/states from policy reads. Resolve current field name, path, and
  type only for display. Never return cell values, mask tokens, endpoint access
  generation, audit rows, or the endpoint key from the policy API.
- Load the policy header and indexed field relations from PostgreSQL for every MCP
  operation and retain that snapshot only within the call. Do not add cross-call
  policy caching initially; any future cache must be measurement-driven and bound to
  both policy revision and endpoint access generation.
- Accept a client-generated `Idempotency-Key` for composite creation and policy-change
  commands. Store the bounded command result by actor and request fingerprint; replay
  of the same command returns its original result, while reuse for a different payload
  conflicts. Keep the existing core API compatible without making the header required.
- Roll back the entire transaction if permission or field validation, endpoint/key
  creation, policy persistence, revision increment, or durable audit append fails.
  After commit, notification delivery, Redis cleanup, and UI broadcast are retryable
  side effects and cannot reverse or weaken the durable security decision.

The chosen model is fully additive: Arabase owns the one-to-one policy header,
normalized protected-field rows, command idempotency records, and append-only audit
events. The core endpoint model and its applied migrations remain unchanged. A
synchronous Arabase endpoint-created receiver materializes the default empty policy,
and registry replacements make current MCP actions content-blind. The composite
Arabase service still creates a requested non-empty policy explicitly in the same
transaction. Any missing policy after backfill remains a fail-closed integrity fault.
