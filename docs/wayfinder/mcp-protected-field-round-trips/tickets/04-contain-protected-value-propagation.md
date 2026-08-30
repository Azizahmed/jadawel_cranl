---
title: "Contain protected values and their derivatives across MCP"
labels:
  - "wayfinder:prototype"
status: closed
assignee: codex
parent: ../map.md
blocked_by: []
prototype_branch: codex/prototype-mcp-protected-propagation
prototype_commit: 412c4c0744d1d3f0f13327da2bb72f1c559bd74c
prototype_asset: backend/src/arabase/mcp/protection/protected_value_propagation.prototype.html
prototype_verdict: "Use transitive protection provenance, guarded queries, typed output contracts, and one fail-closed egress gateway"
---

## Question

What exact field types, serializers, schemas, row tools, page-view samples, search
paths, linked-row labels, lookups, formulas, errors, and future-tool seams can expose
a protected value or derivative, and what enforceable propagation contract covers
them completely while failing closed?

## Approved decisions

### Protection and propagation contract

- Use one hybrid contract combining protection-provenance tracking, source/query
  guards, a central MCP egress gateway, and fixed safe error mapping. Output-only
  redaction and per-tool masking are insufficient.
- Treat every direct or transitive dependency on a protected field as a protected
  derivative. Version one has no declassification rule for aggregates, booleans,
  hashes, truncation, or other apparently non-invertible transformations.
- Track protection at the smallest semantic leaf that can be classified safely. A
  directly protected field protects its whole cell. A formula, lookup, or rollup
  with protected provenance protects its whole result cell. In an otherwise
  unprotected composite value, preserve public structure while masking only the
  protected semantic leaf; for example, a linked-row id and order may remain visible
  while its label is protected because the related primary field is protected.
- If a value cannot be split or classified with certainty, fail the whole MCP call
  with `PROTECTION_UNAVAILABLE`; never return a partial response or plaintext
  fallback.

### Query-shape disclosure

- Permit stable-id row retrieval while masking protected output values.
- Reject MCP search, filters, sorts, grouping, and aggregates that read a protected
  field or protected derivative, because membership, order, groups, and counts can
  disclose protected information even when returned cells are masked.
- Permit unconditional counts. Reject counts whose population depends on a protected
  predicate.
- The current broad `search_all_fields` MCP path must fail when the table's protection
  closure is non-empty because it cannot prove that it searched only public fields.
  A future search contract may accept an explicit allowlist of unprotected field ids.

### Token classes for protected derivatives

- Use the same external `{"$jadawelProtected":{"v":1,"token":"..."}}`
  envelope for direct protected values and protected derivatives so the envelope
  reveals neither the value type nor its source.
- Issue direct-cell tokens with the internal `preserve_cell` operation class already
  approved for same-cell redemption.
- Issue derivative tokens with an internal `display_only` operation class. Never
  accept these tokens in create-row or update-row inputs. A future approved-artifact
  path may interpret them inside Jadawel, subject to the separate artifact-boundary
  decision.

### Enforceable future-tool contract

- Require every enabled MCP tool to declare exactly one output contract:
  `protected_structured` for provenance-bearing data, `public_metadata` for an
  allowlisted metadata schema, or `mutation_receipt` for a value-free operation
  result.
- Reject tool registration or application startup when an enabled tool has no output
  contract or lacks the adapter required by its contract.
- Route the result of every tool through a final protected-egress gateway even if a
  future tool supplies custom asynchronous execution. A tool override must not be
  able to return `TextContent`, image content, or an embedded resource directly to
  the MCP transport.
- Treat missing or unknown runtime provenance as `PROTECTION_UNAVAILABLE` and fail
  the complete call.

### Unstructured content and HTML

- Do not use content matching or secret scanning to infer whether arbitrary strings
  contain protected values.
- Keep the previously approved field-schema metadata visible through explicit
  metadata schemas. Error strings and strings interpolated from row values are not
  metadata.
- When an endpoint has an active protection policy, the general page-view read path
  may return safe page metadata, field schema, and a provenance-aware masked sample,
  but it must not return raw HTML. Return a fixed blocked status for that property.
- Reading or writing HTML that carries protected tokens requires the separately
  approved artifact contract in ticket 07. Until that contract is available, raw
  HTML remains unavailable through a protected MCP endpoint rather than being
  heuristically sanitized.

### Protection closure and field coverage

- Load the current policy and schema from PostgreSQL at the start of every MCP call;
  do not cache the protection closure across calls initially.
- Build the closure from active protected field ids by traversing reverse
  `FieldDependency` edges across tables for formulas, lookups, and rollups. Add
  explicit semantic edges from linked-row display labels to their related primary
  fields, and query-dependency edges for view filters, sorts, groups, and aggregates.
- Recheck the policy revision and endpoint access generation before releasing a
  response or committing a mutation.
- Cover every currently registered field type, including files, selections,
  relations, collaborators, UUID, autonumber, and computed fields. Every type must
  declare a protection adapter and canonical typed fingerprint representation; no
  field type receives an implicit pass-through default.
- Replace the whole value of a directly protected cell, regardless of field type.
  Preserve `null`, the empty string, and empty collections without issuing tokens.
  Treat `false` and numeric zero as real protected values and mask them.
- Permit a composite adapter to retain proven-public structure while masking a
  protected semantic leaf, such as the `value` label inside an otherwise unprotected
  linked-row object. A newly registered field type without an enforceable protection
  contract must not become MCP-capable.
- If a broken, unknown, or unsupported dependency prevents proving the closure from
  a protected root, mark the endpoint `protection-blocked` and fail every call closed.

### Page-view samples

- Restrict a page-view row sample to the view's visible field ids and apply the same
  provenance-aware serializer used by row tools.
- If the effective view filter, sort, group, or aggregate depends on protected
  provenance, return safe page metadata with a fixed blocked row-data status; omit
  both the sample and its conditional count.
- Permit an unconditional count. Keep raw HTML unavailable until the approved
  artifact contract exists.

## Repository evidence

- Every current MCP tool uses the default `MCPTool.call`, which converts an arbitrary
  Python result to JSON or text before returning `TextContent`. This is the present
  central egress seam, but it has no field provenance and future subclasses may
  override it.
- List, create, and update row tools use the ordinary dynamic REST row serializer;
  create and update return complete rows, including defaults, unchanged fields, and
  computed derivatives.
- `list_rows(search=...)` calls `search_all_fields` without a field allowlist before
  it calculates `count`, exposing a membership and count oracle that late masking
  cannot repair.
- Link-row responses include the related row id, order, and the related table's
  primary-field value as their display label. The ordinary `FieldDependency` graph
  covers formulas, lookups, and rollups but does not itself model this display-label
  edge.
- `get_page_view(include_rows=True)` returns raw HTML plus a row sample serialized
  without restricting it to the page's visible field ids. Its view queryset may also
  embed filter- and sort-dependent disclosure in the sample and count.
- The MCP server currently includes raw exception text in its response, and the SSE
  transport logs inbound and outbound payloads. These paths bypass row serialization
  and must be covered by the already approved safe-observability contract.
- The HTML page runtime's ordinary in-product row delivery is not an MCP transport.
  However, HTML authored through MCP can become a later plaintext sink, so its
  materialization remains governed by the separate artifact-approval boundary.

## Resolution

Use a provenance-aware, deny-by-default containment pipeline. Load the endpoint's
policy and current schema for every call; compute a transitive protection closure
across formula dependencies plus explicit semantic edges; block query shapes whose
membership, order, grouping, or count depends on that closure; serialize direct and
derived values with typed protection adapters; and pass every declared tool result
through one final MCP egress gateway before creating protocol content.

Direct protected cells receive same-cell `preserve_cell` tokens. Protected
derivatives receive externally identical `display_only` tokens that row mutations
must reject. Preserve proven-public structure at the smallest semantic leaf, but
fail the complete call when provenance, a dependency, a field adapter, or an output
contract is unknown. Raw HTML and arbitrary data-bearing text remain outside the
general protected output path and require the artifact-approval contract.

The throwaway logic prototype validated six behaviors: multi-level formula closure;
masking `0` and `false` while preserving empty values; linked-row label masking that
retains public ids and order; pre-query rejection of broad search; fail-closed broken
dependency handling; safe-metadata-only page results for protected filters; and
rejection of a future tool without an output contract. It was also checked at desktop
and 390px mobile widths with no console errors. Prototype context: branch
`codex/prototype-mcp-protected-propagation`, commit
`412c4c0744d1d3f0f13327da2bb72f1c559bd74c`, asset
`backend/src/arabase/mcp/protection/protected_value_propagation.prototype.html`.
