---
title: "Design the endpoint protection-policy experience"
labels:
  - "wayfinder:prototype"
status: closed
assignee: codex
parent: ../map.md
blocked_by: []
prototype_branch: codex/prototype-mcp-protection-policy-ux
prototype_commit: 6a0968e3982e08bc161faba4e0e355f231d4747e
prototype_asset: web-frontend/modules/core/components/settings/mcp_protection_policy_ux.prototype.html
prototype_verdict: "Use guided hierarchy A, augmented with B's workspace-wide search"
---

## Question

What Arabic-first, RTL-native interaction lets a user select and understand zero or
more protected fields across large workspaces during every endpoint-creation path,
then review and edit that policy later without implying that unselected derivatives
are automatically safe?

## Resolution

- Describe the feature as selecting **protected fields** for the MCP endpoint
  boundary, not as encrypting columns.
- Use the guided database → table → field hierarchy from variant A, augmented by
  variant B's workspace-wide field search.
- Reuse one three-step flow for every creation path: details, protected fields,
  then review. Page onboarding may preselect the workspace and current table, but
  it must not skip the protection step.
- Never select fields automatically. Signals such as “likely personal data” are
  suggestions only.
- Permit a zero-field policy only through an explicit action followed by a second
  confirmation during review.
- If the workspace changes before creation, require confirmation and clear all
  selections. Never map selections by field name.
- Keep the workspace immutable after creation. Moving to another workspace requires
  a new endpoint.
- Show the protected-field count and a clear “edit protection policy” action on the
  existing endpoint card. Reuse the selector and review added and removed fields
  before saving.
- Scale the selector through lazy field loading per expanded table, retained
  in-session selections, and paginated workspace-wide search after two typed
  characters. Search only metadata the current user may access.
- Display the full database / table / field path and field type wherever duplicate
  names could be ambiguous. Use tri-state database and table checkboxes. Selecting a
  whole table is immediate and undoable; selecting a whole database requires an
  additional scope confirmation.
- Treat suggested personal-data and derivative markers as non-authoritative review
  aids. Keep the derivative warning visible and never claim that an unselected field
  or derivative is safe.
- Never silently discard a saved selection. Show per-table loading and retry states,
  retain unavailable fields visibly in the policy summary, block saving when the
  policy cannot be loaded completely, and switch to read-only when edit permission
  is lost. A field confirmed as deleted appears explicitly as removed in review.
- Review changes as added, removed, and unchanged fields. Save the policy atomically,
  warn before abandoning dirty edits, and surface a reload-and-compare flow instead
  of overwriting a newer policy revision.
- Implement the selector as an Arabic-first, RTL-native semantic tree/list with
  native checkbox behavior, visible focus, keyboard access, announced selection and
  loading states, CSS logical properties, and a single-column mobile layout. Ship
  equivalent English copy and locale keys with the production implementation.

The approved throwaway prototype uses guided hierarchy variant A plus variant B's
workspace-wide search. It covers settings creation, page-context creation with
preselection, and later policy editing on branch
`codex/prototype-mcp-protection-policy-ux`, commit
`6a0968e3982e08bc161faba4e0e355f231d4747e`, asset
`web-frontend/modules/core/components/settings/mcp_protection_policy_ux.prototype.html`.
