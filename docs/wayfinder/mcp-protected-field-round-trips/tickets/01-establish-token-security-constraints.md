---
title: "Establish security constraints for reversible MCP mask tokens"
labels:
  - "wayfinder:research"
status: closed
assignee: token-security-research-agent
parent: ../map.md
blocked_by: []
research_branch: research/mcp-token-security
research_note: ../research/token-security-constraints.md
---

## Question

What constraints do primary security standards, cryptographic guidance, and the MCP
protocol impose on a reversible opaque token that must not disclose plaintext, must
be bound to one endpoint and protected field, must resist tampering and replay, and
must work across Jadawel's multi-process and multi-worker runtime?

## Resolution

Use fresh, fixed-size, cryptographically random server-side handles backed by a
shared vault, and store only each handle's digest. Bind redemption to the MCP
endpoint, workspace, stable field ID, policy revision, permitted operation, and
bounded lifetime. Resolve only in schema-known protected-field slots; never scan or
replace tokens inside arbitrary text, HTML, formulas, errors, or nested payloads.
Require revocation, source-version checks, quotas, rate limits, and sanitized
fail-closed behavior. A self-contained authenticated-encryption token remains an
inferior fallback because it increases length leakage, revocation, nonce, and
key-ring risk.

Research context: branch `research/mcp-token-security`, commit
`48b3df58b26cd710ff0140892865c5804f9b8496`, note
`docs/wayfinder/mcp-protected-field-round-trips/research/token-security-constraints.md`.
