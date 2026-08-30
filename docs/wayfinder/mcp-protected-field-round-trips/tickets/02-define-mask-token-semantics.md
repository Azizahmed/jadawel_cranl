---
title: "Define mask-token interaction semantics"
labels:
  - "wayfinder:grilling"
status: closed
assignee: codex
parent: ../map.md
blocked_by: []
---

## Question

Should a mask token represent a value snapshot or a live cell reference; where may
an agent copy or move it; how stable should it remain across calls; what should
happen after the source value changes; and what expiration behavior gives users a
safe but workable round trip?

## Resolution

A mask token is a version-bound preservation reference for one observed protected
cell value, not an immutable secret snapshot and not a live pointer whose meaning
can change silently. It is bound to the original endpoint, workspace, field, row,
policy revision, and source-value version. If any of that context changes, the token
becomes stale and redemption fails closed.

Issue a fresh random token for every protected value occurrence and every response,
even when the same cell or equal plaintext is returned more than once. Tokens have
a fixed, non-sliding 24-hour lifetime that survives transport reconnects and normal
retries. A token may be reused during that lifetime only for its original cell; it
does not authorize copying or moving the protected value elsewhere.

Protected-field update intent is unambiguous:

- omitting the field preserves it without token redemption;
- returning a valid token to its original cell explicitly preserves the observed
  value after a version check;
- a normal literal replaces the protected value;
- null or empty input follows the field type's existing clear/empty semantics; and
- token envelopes are rejected in row creation, another row or field, search,
  formulas, HTML, arbitrary text, and every input slot that does not explicitly
  declare protected-token support.

Every create or update response masks each non-empty protected value with a newly
issued token rather than echoing an input token. In a batch, all tokens are
validated before mutation; one stale, expired, malformed, foreign, or misplaced
token rejects the entire batch with one sanitized error and no partial writes.
