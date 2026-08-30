---
title: "Choose and validate the mask-token architecture"
labels:
  - "wayfinder:prototype"
status: closed
assignee: codex
parent: ../map.md
blocked_by:
  - "[Establish security constraints for reversible MCP mask tokens](01-establish-token-security-constraints.md)"
  - "[Define mask-token interaction semantics](02-define-mask-token-semantics.md)"
prototype_branch: codex/prototype-mcp-mask-token-architecture
prototype_commit: 0e61115447f9b30641317731fc123507952c39aa
prototype_asset: backend/src/jadawel/core/mcp/mask_token_architecture.prototype.html
---

## Question

Which concrete design—server-side token references, authenticated encrypted tokens,
or another mechanism—best satisfies the agreed interaction semantics and security
constraints, and can a cheap end-to-end spike prove it works with Jadawel's MCP
payload shapes, Redis-backed transport, multiple workers, and key rotation?

## Resolution

Use a shared server-side reference vault, not self-contained authenticated encrypted
tokens. Each protected value occurrence receives a fresh 32-byte random handle encoded
as fixed-length base64url inside this versioned, reserved JSON envelope:

```json
{"$jadawelProtected":{"v":1,"token":"<fixed-length-base64url>"}}
```

The envelope carries no endpoint, row, field, policy, expiry, or value metadata. Treat
the reserved key as a token attempt only in input slots that explicitly support
protected-token redemption, and reject every malformed or misplaced envelope. Store
only the handle's SHA-256 digest as the Redis lookup key; never store the raw handle.

Back the vault with a dedicated Django Redis alias and digest-only namespace. An
optional mask-token Redis URL may default to the existing shared `REDIS_URL`, allowing
production isolation without requiring a new service initially. Give every record a
fixed 24-hour TTL. Redis loss or eviction safely invalidates outstanding tokens; it
must never trigger plaintext fallback.

Bind each vault record to the endpoint, workspace, table, row, field, policy revision,
allowed operation class, observed row state, expiry, and a protected-value fingerprint.
The fingerprint is HMAC-SHA-256 over a versioned canonical typed representation using
a dedicated keyring separate from Django's `SECRET_KEY`. Store its key ID and
canonicalization version, keep previous verification keys for at least 24 hours during
normal rotation, and allow emergency key removal to revoke outstanding tokens. Store
no plaintext, raw token, field name, or MCP payload in the vault.

Do not introduce a per-cell revision solely for this feature. Use the row's observed
`updated_on` together with the keyed value fingerprint. This deliberately permits
conservative invalidation after an unrelated row update while still detecting a
protected-value change that does not advance the row timestamp.

For redemption, acquire row locks and validate every token against current primary
database state before mutation. Keep mutation, response serialization, masking, and
vault issuance inside the database transaction; Redis issuance failure raises and
rolls the mutation back. A vault record issued before a later database rollback is a
safe orphan because redemption rechecks current context and it expires automatically.
For reads, capture the value and row state together and persist the vault record before
releasing the response.

If Redis is unavailable, a required record is missing, or an issuance limit is reached,
fail the entire MCP call with the fixed safe error `PROTECTION_UNAVAILABLE`. Never emit
a partial masked response, commit a partial batch, or return plaintext. Exact capacity
values and load thresholds belong to the follow-up performance decision.

The throwaway logic prototype validated the happy path across two simulated workers,
fresh output-token issuance, atomic wrong-context rejection, stale-value rejection,
expiry, vault outage, and policy-revision invalidation. Prototype context: branch
`codex/prototype-mcp-mask-token-architecture`, commit
`0e61115447f9b30641317731fc123507952c39aa`, asset
`backend/src/jadawel/core/mcp/mask_token_architecture.prototype.html`.
