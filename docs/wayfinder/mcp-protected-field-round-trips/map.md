---
title: "Map secure MCP protected-field round trips"
labels:
  - "wayfinder:map"
status: closed
tracker: local-markdown
---

## Destination

Reach an approved, implementation-ready security specification and repository-mapped
execution plan for endpoint-specific protected fields whose plaintext stays inside
Jadawel while MCP clients round-trip opaque mask tokens safely.

## Notes

- Planning only: this map resolves decisions and does not implement or deploy the
  feature.
- Consult `wayfinder`, `grilling`, and `domain-modeling` in every decision session;
  use `research` or `prototype` when the ticket type requires it.
- The MCP endpoint is the enforcement boundary for every present and future MCP
  caller. Direct, non-MCP AI-provider calls are outside this effort.
- Each endpoint may protect zero or more fields across its workspace, and its policy
  remains editable. Existing endpoints start with an empty policy.
- Field schema remains visible, but every non-empty protected value and protected
  derivative must stay plaintext only inside Jadawel.
- Exact valid mask tokens may round-trip; new literal values remain valid writes;
  malformed, foreign, or misplaced tokens fail closed.
- Every endpoint-creation path must expose the same optional protected-field step.
- MCP-authored artifacts require explicit in-Jadawel approval before materializing
  protected plaintext.
- Raw MCP payloads must not enter logs, traces, metrics, or audit descriptions.
- The repository has no `docs/agents/issue-tracker.md`; this map therefore uses the
  Wayfinder local-Markdown fallback. Child tickets live under `tickets/`, and their
  `blocked_by` metadata is the fallback dependency relationship.

## Decisions so far

<!-- Resolution links are appended here only when child tickets close. -->

- [Establish security constraints for reversible MCP mask tokens](tickets/01-establish-token-security-constraints.md): use endpoint- and field-bound random server-side handles with digest lookup, bounded lifetime, typed redemption, revocation, and fail-closed validation.
- [Define mask-token interaction semantics](tickets/02-define-mask-token-semantics.md): use fresh 24-hour, version-bound, same-cell preservation references; omit to preserve, use literals to replace, and reject invalid tokens atomically.
- [Choose and validate the mask-token architecture](tickets/03-choose-mask-token-architecture.md): use versioned random handles backed by a shared, plaintext-free Redis vault with row-state and keyed-value validation, transaction-safe issuance, and fail-closed outage behavior.
- [Specify safe MCP errors, auditing, and observability](tickets/08-specify-safe-observability.md): keep all diagnostic sinks content-blind, expose only fixed safe errors, and retain an unsampled allowlisted audit trail with canary leakage tests.
- [Design the endpoint protection-policy experience](tickets/05-design-protection-policy-ux.md): use one Arabic-first guided database/table/field selector across creation and editing, augmented by lazy workspace-wide search, explicit zero-policy and bulk confirmations, atomic diff review, and fail-visible loading, permission, deletion, and conflict states.
- [Define protected-field and mask-token lifecycle rules](tickets/06-define-policy-token-lifecycle.md): bind policies to stable field IDs; use policy revisions and endpoint access generations for immediate revocation; suspend and safely restore trashed identities; fail closed across schema, permission, account, key, endpoint, workspace, and concurrent-row transitions.
- [Choose the fork-safe policy persistence and API model](tickets/09-choose-fork-safe-persistence-model.md): keep an explicit Arabase one-to-one policy header and normalized field relations, expose atomic companion APIs with revision and idempotency checks, backfill every endpoint, persist a content-blind audit trail, and fail closed on missing or inconsistent policy state.
- [Contain protected values and their derivatives across MCP](tickets/04-contain-protected-value-propagation.md): compute transitive protection provenance, guard query-shape disclosure before execution, use typed field and tool-output contracts, distinguish same-cell and display-only tokens, and enforce one fail-closed final egress gateway.
- [Design approval for MCP-authored protected-data exposure](tickets/07-design-artifact-approval-boundary.md): keep plaintext and tokens out of stored artifacts, require exact revision-and-audience-bound human approval, and enforce the binding before returning HTML or querying protected row feeds.
- [Bound token-vault capacity and multi-worker performance](tickets/11-bound-token-vault-capacity-and-performance.md): cap each call at 200 rows and 1,000 tokens, reserve exact live records at 10,000 per endpoint and 50,000 globally, isolate a noeviction Redis vault, and fail issuance closed at conservative memory, concurrency, and latency boundaries.
- [Lock the implementation sequence and verification gates](tickets/10-lock-implementation-and-verification.md): land one generic core interception seam plus additive Arabase policy, vault, containment, UX, and artifact layers; release feature-off, then staff canary, then general admission, with irreversible fail-closed enforcement after first activation.

## Not yet specified

Nothing remains unspecified before implementation. New findings during execution
must be handled as implementation defects or a new decision map, not silently change
this approved security contract.

## Out of scope

- Protecting direct AI-provider integrations that do not call an MCP endpoint.
- Encrypting or masking Jadawel data at rest or in the ordinary authenticated UI.
- A global workspace-wide field-classification policy shared by every endpoint.
- Client- or harness-specific masking implementations; enforcement belongs to the
  Jadawel MCP boundary.
- Implementing, migrating, deploying, or enabling the feature during wayfinding.
- A general MCP capability for copying or moving protected values between cells;
  that requires a separate explicit, audited product decision.
