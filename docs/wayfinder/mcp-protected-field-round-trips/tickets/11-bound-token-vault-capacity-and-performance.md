---
title: "Bound token-vault capacity and multi-worker performance"
labels:
  - "wayfinder:prototype"
status: closed
assignee: codex
parent: ../map.md
blocked_by:
  - "[Choose and validate the mask-token architecture](03-choose-mask-token-architecture.md)"
  - "[Contain protected values and their derivatives across MCP](04-contain-protected-value-propagation.md)"
prototype_branch: codex/prototype-mcp-token-vault-capacity
prototype_commit: c37df5668b612dfe9623e86b1ba7ab37464602dd
prototype_asset: backend/src/arabase/mcp/protection/token_vault_capacity.prototype.html
prototype_verdict: "Use exact live-record reservations, a dedicated noeviction Redis vault, and conservative hard limits that fail closed before row locks"
---

## Question

What per-call, per-endpoint, and deployment-wide issuance limits; Redis memory budget
and eviction policy; bulk-read behavior; latency budget; concurrency controls; and
multi-worker load gates keep the shared 24-hour token vault bounded without weakening
fail-closed protection, and what representative spike proves those limits against
Jadawel's actual MCP payload and protected-derivative shapes?

## Adopted fast-track decisions

### Default issuance and payload limits

- Limit one MCP call to 1,000 newly issued tokens, 1,000 redeemed tokens, no more
  than 200 rows for list/create/update, and a 4 MiB encoded protected response.
  Preflight the exact non-empty protected semantic leaves, row count, and response
  size before creating handles or modifying rows. MCP actions must enforce the row
  limit themselves; their current Pydantic list inputs do not inherit the REST
  serializers' batch limit.
- Limit each endpoint to 10,000 live issued-token records across the rolling 24-hour
  lifetime window and a dedicated deployment vault to 50,000. These are availability
  limits, not billing quotas, and apply equally to direct and `display_only`
  derivative tokens.
- A request exceeding a deterministic per-call limit fails completely with fixed
  `PROTECTION_UNAVAILABLE` and `retryable: false`. Transient concurrency, store, or
  endpoint/deployment budget pressure uses the same fixed code with
  `retryable: true`. Do not reveal counters or remaining capacity to the MCP caller.
- Do not silently shrink page size, omit fields, reuse tokens, shorten TTL, or return
  a partial result to fit a budget. The caller must make an explicit narrower request.

### Redis memory and deployment isolation

- Budget each live record conservatively at 1.5 KiB: roughly 609 bytes of compact
  key/metadata plus Redis object, dictionary, expiry-index, and fragmentation
  overhead. Replace this assumption only when a production-like p99 measurement is
  higher. At 50,000 records this reserves about 73.24 MiB.
- Require a dedicated mask-token Redis service of at least 256 MiB, configured with
  `maxmemory 128mb`, `maxmemory-policy noeviction`, TLS/authentication where
  supported, and no correctness dependency on AOF or snapshots. Token loss on
  restart is a safe revocation; competing with Celery, Channels, caches, or RedBeat
  is not an acceptable production dependency.
- Permit shared `REDIS_URL` only as a development/test/bootstrap fallback, capped at
  16,000 live records (about 23.44 MiB), and only after runtime checks prove
  `maxmemory > 0` and `noeviction`. The repository's current shared Redis setup does
  not prove either property, so it cannot activate protected production policies.
- Warn operators before the stop boundary at 50% of configured `maxmemory`. At 60%
  or unsafe Redis latency, stop new issuance and fail protected calls closed while
  continuing redemption and cleanup where Redis remains readable. At 70%, mark
  protection readiness not ready and alert. Never make ordinary app liveness depend
  on the vault, and never cross the atomic record limits.

### Distributed reservations and bulk operations

- Maintain global and per-endpoint sorted-set expiry indexes keyed by token digest.
  One Redis Lua admission script uses server time to remove expired members, checks
  both `ZCARD` values, and atomically reserves all requested digests before token
  records are written. This counts exact live records rather than approximate hourly
  buckets and avoids `SCAN` in the hot path.
- Do not decrement a reservation after an uncertain Redis/network result, database
  rollback, or worker crash. A crash or partial write may conservatively hold capacity
  until TTL, but can neither overrun the cap nor expose plaintext.
- Permit at most two active issuing calls per endpoint and six deployment-wide with
  a cluster-wide semaphore. Wait no more than 250 ms; then return retryable
  `PROTECTION_UNAVAILABLE`. Acquire the semaphore and reserve capacity before row
  locks so a saturated vault does not hold database locks.
- Issue records in one bounded pipeline after one atomic reservation. Do not release
  the MCP response or commit a mutation until every record write succeeds. A partial
  pipeline result fails the entire call; any records that did land are safe orphans.
- Redeem up to 1,000 unique digests with one pipelined `MGET`, then validate every
  binding and fingerprint against locked primary rows. One missing or invalid record
  rejects the whole mutation. Redemption does not consume a token because the
  approved interaction semantics permit same-cell reuse during its fixed lifetime.

### Readiness, latency, and load gates

- Expose a content-blind protection-readiness check that performs `PING` plus a
  TTL-bound `SET`/`GET`/`DEL` canary, verifies `noeviction`, `maxmemory > 0`,
  configuration/script agreement across workers, `used_memory / maxmemory < 60%`,
  and enough space for the requested reservation. Use 250 ms connect and 500 ms
  read/write timeouts. Full internal health reports the vault alias; public health
  stays lightweight, and ordinary application liveness may remain green.
- Against the equivalent unprotected call, require added p95 latency of at most
  15 ms for 100 tokens and 75 ms p95 / 150 ms p99 for 1,000 tokens. On a CranL-class
  deployment, total protected `list_rows` latency must remain at or below 500 ms p95.
- Run the representative spike on at least three backend processes with five
  endpoints and 50 calls of 1,000 tokens each: 200 rows times five protected or
  derived semantic leaves spanning direct, formula, lookup, rollup, and link-label
  values including `0`, `false`, and `null`. The 50th call fills 50,000 records at
  about 73 MiB; call 51 must fail closed without partial response or telemetry leak,
  and redemption must work across workers.
- Gate create/update separately at 200 rows times five tokens: one invalid token must
  roll back every database write. With 12 concurrent issuing calls, only six may
  enter and the rest must fail within 250 ms. Redis outage during mutation must roll
  back, and a short-TTL test must prove records, exact quota, and readiness recover.
- Add chaos cases for Redis timeout/restart, `maxmemory`, partial pipeline failure,
  worker death after reservation, database rollback, policy revision, and key
  rotation. Fail on plaintext or token in telemetry, quota overshoot, partial MCP
  response, committed mutation without complete output tokens, or latency/memory
  threshold breach.

## Repository evidence

- `ROW_PAGE_SIZE_LIMIT` and `BATCH_ROWS_SIZE_LIMIT` both default to 200. MCP
  `list_table_rows` defaults to 100 and clamps to the page limit, but MCP create and
  update schemas accept unbounded lists and their services call row actions without
  enforcing the batch limit. The protection boundary must add that preflight before
  token work or row mutation.
- One `REDIS_URL` currently backs the Celery broker, RedBeat, result backend,
  Channels, and Django caches. The local container has a 256 MiB process limit but
  starts Redis without `maxmemory` or a `maxmemory-policy`; CranL documentation names
  one managed Redis but does not establish its capacity or eviction policy.
- The production entrypoint defaults to three Gunicorn/Uvicorn workers, so an
  in-process counter cannot enforce endpoint or deployment limits. The exact quota
  and concurrency controls must be Redis-atomic and exercised across workers.
- A compact plaintext-free record plus its digest key is about 609 bytes before
  Redis structures. Allowing for object/SDS/dictionary overhead, two expiry indexes,
  and fragmentation yields the adopted 1.5 KiB budget. That makes 10,000 records
  about 14.65 MiB, 50,000 about 73.24 MiB, and the 16,000 shared fallback about
  23.44 MiB.

## Resolution

Bound every protected MCP path before it touches rows: no more than 200 rows,
1,000 issued or redeemed tokens, or a 4 MiB protected response per call. Reserve
exact live token digests atomically in per-endpoint and global expiry indexes, capped
at 10,000 and 50,000 records, then write all records in one bounded pipeline. Admit
only two issuing calls per endpoint and six deployment-wide; wait at most 250 ms.
Any deterministic oversize request fails non-retryably, while transient capacity or
vault health failures use the same content-blind retryable error.

Production uses a dedicated 256 MiB Redis service with `maxmemory 128mb` and
`noeviction`; the shared Redis fallback is non-production and capped at 16,000 only
when its runtime configuration is proven safe. Stop issuance at 60% memory while
preserving readable redemption, and mark protection readiness unavailable at 70%.
The full readiness probe validates connectivity, a TTL canary, configuration,
script agreement, memory, latency, and reservation headroom without affecting the
ordinary application liveness endpoint.

The throwaway prototype validated the 1,000-token success path, deterministic
oversize rejection, endpoint-boundary rejection, an atomic two-worker race at the
50,000 global cap, redemption under issuance pressure, all-or-nothing rejection for
a missing record, and TTL recovery. It passed 1280px and 390px RTL checks without
horizontal overflow or console errors. Prototype context: branch
`codex/prototype-mcp-token-vault-capacity`, commit
`c37df5668b612dfe9623e86b1ba7ab37464602dd`, asset
`backend/src/arabase/mcp/protection/token_vault_capacity.prototype.html`.
