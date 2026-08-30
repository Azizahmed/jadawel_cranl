---
title: "Design approval for MCP-authored protected-data exposure"
labels:
  - "wayfinder:prototype"
status: closed
assignee: codex
parent: ../map.md
blocked_by:
  - "[Contain protected values and their derivatives across MCP](04-contain-protected-value-propagation.md)"
  - "[Design the endpoint protection-policy experience](05-design-protection-policy-ux.md)"
prototype_branch: codex/prototype-mcp-artifact-approval
prototype_commit: 5708cd0231fe0f982ebc7b6abf98505ab94d14f1
prototype_asset: backend/src/arabase/mcp/protection/artifact_approval_boundary.prototype.html
prototype_verdict: "Keep protected plaintext out of stored artifacts and require an exact revision-and-audience-bound human approval before runtime projection"
---

## Question

How should Jadawel detect, present, record, revoke, and enforce a human approval when
an MCP-authored page or future persistent artifact would cause protected plaintext
to be materialized outside the MCP response path?

## Adopted fast-track decisions

The user authorized the recommended path and requested consolidated rounds. Apply
the following as one approval-boundary contract, subject to the logic prototype.

### Draft and publication model

- An MCP tool never writes protected plaintext or mask tokens into persistent HTML.
  Reject the reserved mask-token envelope anywhere inside arbitrary HTML or other
  untyped artifact content.
- Replace direct MCP publication with submission of a protected artifact draft. The
  draft stores candidate HTML, a content digest, its endpoint and target view, and an
  explicit artifact exposure manifest of stable protected field ids. It stores no
  plaintext values or token handles.
- Keep the currently approved page active while a replacement draft awaits review.
  A first draft for an empty page remains non-renderable until approved.
- Do not infer the manifest through JavaScript or text scanning. The MCP caller
  declares requested fields, the server validates their identities and transitive
  provenance, and the runtime enforces the approved projection independently of what
  the HTML attempts to read.

### Human review and approval

- Require the endpoint owner to be an active workspace member who can currently
  manage the endpoint, update the page, and read every requested protected field.
  Workspace administration alone does not grant approval authority.
- Present a content-blind Arabic-first review showing the page, database/table/field
  paths, direct versus derived use, row limit, visible fields, external-resource
  state, view filters/sorts, and audience. Never show protected samples or tokens in
  the approval screen.
- Offer separate authenticated and public audience scopes. Authenticated approval
  permits only viewers already authorized for the view's row feed. Public exposure,
  including password-protected share links, requires a distinct stronger
  confirmation. Private approval never silently expands to public.
- Approval atomically snapshots the previous active HTML, promotes the exact draft,
  records an append-only content-blind audit event, and creates an approval bound to
  the artifact digest, manifest, endpoint, policy revision, access generation, view
  configuration, and audience fingerprint.

### Runtime materialization

- Stored HTML remains a template and never receives substituted plaintext. At each
  render, the backend validates the approval binding and projects only its approved
  protected fields into the existing sandboxed iframe data feed.
- If no protected fields are requested, the ordinary safe page path remains
  available without an exposure approval. If any protected field or derivative is
  requested, a missing, stale, or revoked approval blocks the entire page document
  and row feed with a fixed in-product state; do not render a partial page.
- Apply the same check to authenticated and public row-feed endpoints. Public share
  status or a password does not substitute for artifact approval.

### Invalidation, revocation, and recovery

- Invalidate approval on any change to HTML, requested protected fields, visible
  fields, filters, sorts, groups, row limit, external-resource setting, table/view
  identity, public/password audience state, endpoint policy revision, endpoint
  access generation, requested field lifecycle, or approver permission.
- Policy/access changes block immediately through durable revision checks; no scan of
  stored approvals or Redis is required for correctness.
- Manual revocation blocks the protected artifact immediately but retains its HTML,
  manifest, approval history, and audit record. Reactivation always requires a new
  explicit approval.
- Restoring an HTML revision creates a new draft and never resurrects its former
  approval automatically, even when its digest matches an old approved revision.
- A direct human source edit uses the same review boundary: saving creates a draft,
  and the editor may review and approve it in one explicit in-product flow if they
  satisfy the approval authority.

### Additive persistence seam

- Keep draft, manifest relations, approvals, and audit records in
  `arabase.mcp.protection`, related to existing endpoint, view, field, and user rows.
  Do not add approval columns to the upstream `HtmlPageView` model.
- Implement one generic artifact-approval service contract, with an HTML-page adapter
  first. Future persistent artifact types must provide their own digest,
  configuration fingerprint, manifest validation, preview, promotion, and runtime
  enforcement adapter before they can request protected plaintext.

Use the following first HTML-page adapter records:

- `HtmlPageArtifactState`, one-to-one with the view, holds the active approval pointer
  and a target generation.
- `ArtifactDraft` holds endpoint, target view, candidate HTML, content digest,
  configuration fingerprint, status, nonce, submitter, and timestamps.
- `ArtifactManifestField` holds the draft, a nullable field relation, a retained
  stable field-id snapshot, and direct/derived provenance. A missing relation or
  manifest count/hash mismatch fails closed rather than shrinking the manifest.
- `ArtifactApproval` holds the exact binding tuple and approval/revocation metadata.
- `ArtifactAuditEvent` is append-only and content-blind. Do not put candidate HTML in
  the generic undoable view action stream.

Recompute the configuration fingerprint at render time. It includes visible field
ids/order/hidden state, filters and filter groups, sorts, groups, row limit, external
resources, and public/password audience state. It excludes row values. Use signals
only for UI invalidation hints; runtime correctness must not depend on signal
delivery. Increment the target generation across trash/restore so a restored view
cannot revive an old approval. Imports and duplicates start with no manifest or
approval.

## Repository evidence

- Current MCP create, update, and revision restore write `HtmlPageView.html` directly
  through `ViewHandler`, so there is no draft boundary today.
- The general REST create/PATCH path and undo/redo actions can also write HTML
  directly. The existing update action retains complete original and replacement
  HTML, so the production design must replace that path with a content-blind artifact
  command instead of fixing only MCP tools.
- `HtmlPageViewRevision` stores only prior HTML and author and is trimmed to a small
  history; it cannot serve as a durable approval or audit record.
- Both authenticated and public row-feed endpoints build their query, count, and
  serializers without an artifact approval check. Public view information also
  returns the raw HTML document before the row feed is requested.
- The frontend builds `srcdoc` from `view.html` and posts serialized rows into the
  sandboxed iframe. Its opaque-origin and `event.source` checks are sound, but field
  projection is currently frontend-visible and therefore cannot enforce approval.
- Import and duplicate copy HTML directly, while trash/restore can revive the same
  view identity. Both paths require explicit generation and approval handling.

## Resolution

Introduce an additive, server-enforced draft-to-approval boundary. MCP and direct
human edits submit HTML templates plus stable protected-field manifests without
tokens or plaintext. Only an authorized endpoint owner can approve the exact
candidate for the current private or public audience. Approval atomically promotes
the draft and records a durable content-blind binding and audit event.

At every document and row-feed request, validate the complete durable binding before
querying rows or returning HTML, then project only approved protected fields into the
sandboxed runtime. Any stale, missing, revoked, or unprovable binding blocks the whole
artifact. HTML source, mask tokens, and protected values never become part of the
approval or audit records.

The throwaway state-machine prototype validated first publication, a replacement
draft that leaves the current approved revision active, separate public reapproval,
policy/configuration/permission invalidation, manual revocation, non-resurrecting
revision restore, and rejection of a mask token embedded in HTML. It passed desktop
and 390px RTL checks with no horizontal overflow or console errors. Prototype
context: branch `codex/prototype-mcp-artifact-approval`, commit
`5708cd0231fe0f982ebc7b6abf98505ab94d14f1`, asset
`backend/src/arabase/mcp/protection/artifact_approval_boundary.prototype.html`.
