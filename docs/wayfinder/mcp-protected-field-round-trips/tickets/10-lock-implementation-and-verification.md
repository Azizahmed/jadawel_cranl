---
title: "Lock the implementation sequence and verification gates"
labels:
  - "wayfinder:grilling"
status: closed
assignee: codex
parent: ../map.md
blocked_by:
  - "[Choose and validate the mask-token architecture](03-choose-mask-token-architecture.md)"
  - "[Contain protected values and their derivatives across MCP](04-contain-protected-value-propagation.md)"
  - "[Design the endpoint protection-policy experience](05-design-protection-policy-ux.md)"
  - "[Define protected-field and mask-token lifecycle rules](06-define-policy-token-lifecycle.md)"
  - "[Design approval for MCP-authored protected-data exposure](07-design-artifact-approval-boundary.md)"
  - "[Specify safe MCP errors, auditing, and observability](08-specify-safe-observability.md)"
  - "[Choose the fork-safe policy persistence and API model](09-choose-fork-safe-persistence-model.md)"
  - "[Bound token-vault capacity and multi-worker performance](11-bound-token-vault-capacity-and-performance.md)"
---

## Question

Given every closed decision, what is the smallest repository-owned implementation
sequence, migration and rollback path, threat-focused test matrix, Arabic/English UI
verification, performance gate, deployment procedure, and live MCP proof required
before the feature can be called complete?

## Adopted fast-track decisions

The user approved the recommended path and asked to finish the remaining rounds
quickly. The following is the implementation contract; it does not authorize
implementation or deployment during wayfinding.

### Non-negotiable release contract

- Keep all new persistence, APIs, services, lifecycle handling, UI, and tests under
  `arabase` wherever possible. Do not change `MCPEndpoint` or any applied upstream
  migration. Every unavoidable core edit must be a small generic MCP seam and must be
  recorded in `PATCHES.md` with its test.
- A feature flag may control who can create or weaken a policy, but it must never
  bypass enforcement for a policy that is already non-empty, suspended, or blocked.
  Missing policy state, vault unavailability, unknown provenance, and unsupported
  output contracts always fail protected MCP calls closed.
- Ship no shadow mode that emits plaintext and later compares it with masking. The
  safe pre-activation states are schema/backfill only and synthetic tests only.
- Do not expose an endpoint key before its policy commits, do not commit a mutation
  before all output tokens are issued, and do not return a partial protected result.
- Treat the first durable `POLICY_BECAME_NONEMPTY` audit event as the point of no
  return for old code. After it exists, rollback means stopping new policy admission
  and deploying a forward fix; it never means running an image that lacks enforcement.

### Configuration and rollout gates

Use the existing `FEATURE_FLAGS` path so backend and Nuxt receive the same rollout
state without adding another public environment variable:

- no protection flag: policy reads and explicit empty-policy creation remain
  available, but non-empty create/replace commands are rejected and protection UI is
  hidden. Existing non-empty policies are still enforced.
- `mcp-protected-fields-staff`: staff users may create or edit non-empty policies;
  use this for the production canary.
- `mcp-protected-fields`: all otherwise-authorized endpoint owners may use the flow.

Add these private backend settings, following the repository's Django-config skill
when implementation begins:

- `JADAWEL_MCP_PROTECTION_REDIS_URL`: mandatory dedicated Redis URL whenever either
  rollout flag is enabled. Shared `REDIS_URL` is allowed only in tests/development
  when `JADAWEL_MCP_PROTECTION_ALLOW_SHARED_REDIS=true` is explicit.
- `JADAWEL_MCP_PROTECTION_FINGERPRINT_KEYS`: JSON object from short key IDs to
  base64-encoded 32-byte HMAC keys. It is secret and never reaches Nuxt, API output,
  logs, or model configuration.
- `JADAWEL_MCP_PROTECTION_ACTIVE_KEY_ID`: one key present in that keyring. Previous
  verification keys remain configured for at least 24 hours during normal rotation.
- `JADAWEL_MCP_PROTECTION_ALLOW_SHARED_REDIS`: defaults false and is forbidden with
  production settings.

Keep the approved 200-row, 1,000-token, 4 MiB response, 10,000-per-endpoint,
50,000-global, 2-per-endpoint, and 6-global ceilings as hard code constants initially;
do not make unsafe production tuning an environment-only action. The vault readiness
check still derives the lower effective cap from measured record size and Redis
memory.

Propagate and document private settings in
`backend/src/jadawel/config/settings/base.py`, `.env.example`,
`.env.docker-dev.example`, `docker-compose.yml`, `docker-compose.dev.yml`,
`docker-compose.no-caddy.yml`, `deploy/all-in-one/README.md`,
`docs/CONFIGURATION.md`, `docs/DEPLOY_CRANL.md`, and `cranl_fix.md`. No fingerprint
key or Redis credential belongs in checked-in examples beyond placeholders.

### Implementation sequence and owning files

#### 1. Establish the generic MCP safety seam

- Add a single optional synchronous call-interceptor registry in
  `backend/src/jadawel/core/mcp/registries.py`. Invoke it from the base `MCPTool.call`
  after Pydantic validation and before JSON/protocol serialization. It receives the
  endpoint, registered tool, validated arguments, and a callable for `_sync_call`, so
  Arabase can keep mutation and masking in one worker-thread transaction. With no
  interceptor registered it preserves current behavior; Arabase registers exactly
  one protection interceptor. An inventory test must reject any future tool that
  overrides `call` and could bypass this seam.
- In `backend/src/jadawel/core/mcp/__init__.py`, replace caller-visible exception
  strings with fixed MCP errors carrying a correlation ID and `isError=true`. Never
  interpolate exception text, field names, arguments, endpoint keys, or returned
  content.
- Remove raw body, serialized message, session URI, validation object, and tool-result
  logging from `backend/src/jadawel/core/mcp/sse.py`. Keep only allowlisted event,
  correlation, registered tool, outcome, safe reason, and duration fields.
- Record these three generic upstream-core edits in `PATCHES.md`. Do not edit core row
  tools, endpoint models, or their migrations.

Exit gate: existing unprotected MCP tests remain byte-for-byte compatible except for
the newly sanitized error shape; canary strings placed in arguments, results, keys,
and exceptions are absent from captured logs and traces.

#### 2. Add durable policy and audit state

- Create `backend/src/arabase/mcp/protection/` with `models.py`, `enums.py`,
  `exceptions.py`, `policies.py`, `idempotency.py`, `audit.py`, and `lifecycle.py`.
  Import its models from `backend/src/arabase/models.py` so Django registers them
  without a new core app entry.
- Add forward migration
  `backend/src/arabase/migrations/0007_mcp_protection_policy.py`, depending on
  Arabase `0006`, core `0117`, and database `0211`. It creates the one-to-one policy,
  normalized field relations, bounded idempotency records, and append-only audit
  rows, then batch-backfills one active empty policy per existing endpoint.
- Register a synchronous endpoint-created receiver and content-blind replacements for
  the current MCP create/update/delete action types from `ArabaseConfig.ready()`.
  Receiver or audit failure must abort the surrounding transaction.
- Centralize field/table/database/workspace trash, restore, permanent deletion,
  permission, account, endpoint-key, and endpoint lifecycle transitions in
  `lifecycle.py`. Schema mutation and protection revision changes share one database
  transaction; notifications and best-effort cleanup run on commit.
- Add `backend/src/arabase/management/commands/mcp_protection_check.py`. Its strict
  mode proves every endpoint has one policy, relations belong to the same workspace,
  revisions are valid, no forbidden content exists in audit rows, configuration is
  coherent, and the deployment may or may not safely run an old image.

Exit gate: migration tests cover an empty database and a populated snapshot;
backfill count equals endpoint count; missing/duplicate/inconsistent policies fail
strict readiness and MCP calls closed.

#### 3. Implement the plaintext-free token vault

- Add `canonical.py`, `tokens.py`, `vault.py`, `capacity.py`, and `readiness.py` under
  `backend/src/arabase/mcp/protection/`. Generate 32 random bytes per occurrence,
  expose only the fixed version-1 envelope, use SHA-256 digests as Redis keys, and
  HMAC the canonical typed value with the active fingerprint key.
- Configure a dedicated Django Redis alias in `base.py`. Implement atomic Lua
  reservation against per-endpoint and global expiry sorted sets, bounded pipelined
  `SET NX EX`, pipelined `MGET`, cluster-wide 2/6 semaphores, and 250/500 ms
  connection/read-write timeouts. Never use `SCAN` on the call path.
- Add the vault result to authenticated full health, preferably through an Arabase
  health-check registration seam. Public `/api/_health/` remains lightweight and
  independent. The check performs `PING`, a TTL `SET`/`GET`/`DEL` canary,
  `noeviction`, positive `maxmemory`, script/config agreement, memory thresholds,
  and requested-reservation headroom.

Exit gate: cross-process issuance/redemption, NX collision, exact quota race, timeout,
restart, partial pipeline, memory stop, old-key verification, emergency key removal,
and TTL recovery tests all fail closed without plaintext or cap overshoot.

#### 4. Build provenance, typed contracts, and the final egress gateway

- Add `provenance.py`, `contracts.py`, `adapters.py`, `query_guard.py`, `egress.py`,
  and `interceptor.py`. Register the interceptor in `ArabaseConfig.ready()` only
  after all contract/adapters are registered.
- Compute transitive provenance from stable field identities through formula
  dependencies, lookups, rollups, and linked-row display labels. Model semantic
  leaves so public IDs/order may remain while protected labels receive
  `display_only` tokens. Mask `0` and `false`; preserve the field type's truly empty
  representation.
- Give every currently registered tool an explicit input/output contract. Guard
  search, filters, sorting, grouping, count, and membership before querying. A future
  or unknown tool is callable with an empty policy, but fails closed for a non-empty
  policy until it has a reviewed contract.
- Keep one egress gateway immediately before MCP protocol content is created. It
  validates the call's policy revision/access generation again, preflights rows,
  semantic leaves, token capacity, and encoded response size, then masks and issues
  all records. The gateway rejects arbitrary HTML/text token substitution.

Exit gate: every tool has a contract inventory test; broken dependencies, unknown
field types, protected search/order/count, and an unregistered future tool fail before
plaintext is serialized.

#### 5. Integrate all-or-nothing row round trips

- Add protection-aware handlers for `list_table_rows`, `create_rows`, and
  `update_rows` inside Arabase contracts rather than editing their core tool files.
  Enforce the existing 200-row batch ceiling in MCP before work begins.
- On update, parse the reserved envelope only in protected value slots. Omission
  preserves without redemption, a same-cell `preserve_cell` token preserves after
  locked-state validation, a literal replaces, and any `display_only`, malformed,
  stale, expired, foreign, copied, or misplaced token rejects the complete batch.
- Hold row locks while validating every token and current `updated_on`/fingerprint.
  Keep mutation, output serialization, fresh token issuance, and durable audit in one
  database transaction. Redis failure raises and rolls the mutation back; landed
  records are unusable orphans that expire.

Exit gate: create/update of 200 rows times five protected leaves is atomic; one bad
token, revision change, row race, Redis outage, or output-capacity failure leaves the
database unchanged and returns no partial content.

#### 6. Expose additive policy APIs and the Arabic-first UI

- Add `backend/src/arabase/api/mcp_protection/{urls.py,views.py,serializers.py,errors.py}`
  and mount it from `backend/src/arabase/api/urls.py`. Implement composite
  `POST /api/arabase/mcp/endpoints/` plus `GET` and full-set `PUT` at
  `/api/arabase/mcp/endpoints/{id}/protection-policy/`, with `expected_revision` and
  optional `Idempotency-Key`.
- Return only approved IDs, states, counts, revision, lifecycle status, and display
  metadata resolved under current permissions. Never return endpoint access
  generation, audit rows, values, tokens, or keys from the policy endpoint.
- Add `web-frontend/modules/arabase/mcp/` containing
  `components/McpProtectedEndpointSettings.vue`,
  `components/McpProtectedEndpointCard.vue`,
  `components/McpProtectionFlow.vue`,
  `components/McpProtectionFieldSelector.vue`,
  `components/McpProtectionReview.vue`,
  `components/McpProtectionStatus.vue`, `services/protectionPolicy.js`, and
  `settingsTypes.js`. Keep flow state local; do not introduce a global store unless
  implementation proves cross-route persistence is necessary.
- In `web-frontend/modules/arabase/registryPlugin.js`, unregister the core
  `mcp-endpoint` settings type and register the Arabase replacement. The existing core
  components stay untouched. Update Arabase's `HtmlPageOnboarding.vue` to open the
  same flow with workspace/table preselection instead of directly creating a key.
- Add `web-frontend/modules/arabase/assets/scss/mcp_protection.scss`, using BEM and
  logical properties only. Desktop at 960px and above uses a bounded metadata/search
  rail beside the field tree; tablet and mobile use one column. At 599px and below,
  actions are full width, review sections stack, nested indentation uses
  `padding-inline-start`, and the save bar remains reachable without horizontal
  scroll. Technical IDs/tokens alone use `dir="ltr"`.
- Use a semantic tree/list with native checkboxes, tri-state table/database rows,
  visible focus, keyboard expansion/selection, `aria-live` loading and selection
  counts, lazy table loading, and search after two characters. At both 1440x900 and
  390x844, verify Arabic physically places the hierarchy rail and directional icons
  on the right; English mirrors them to the left.

The exact new locale namespace lives in Arabase `ar.json` and `en.json`:

| Key | Arabic | English |
|---|---|---|
| `mcpProtection.title` | حماية بيانات MCP | MCP data protection |
| `mcpProtection.description` | اختر الحقول التي يجب ألا تغادر جداول بقيمها الأصلية عبر نقطة النهاية هذه. | Choose fields whose original values must not leave Jadawel through this endpoint. |
| `mcpProtection.stepDetails` | التفاصيل | Details |
| `mcpProtection.stepFields` | الحقول المحمية | Protected fields |
| `mcpProtection.stepReview` | المراجعة | Review |
| `mcpProtection.searchLabel` | البحث عن حقل | Search fields |
| `mcpProtection.searchPlaceholder` | اكتب حرفين على الأقل | Type at least two characters |
| `mcpProtection.selectedCount` | تم اختيار {count} حقل | {count} fields selected |
| `mcpProtection.protectedCount` | {count} حقل محمي | {count} protected fields |
| `mcpProtection.editPolicy` | تعديل سياسة حماية الحقول | Edit protection policy |
| `mcpProtection.noFields` | المتابعة دون حقول محمية | Continue without protected fields |
| `mcpProtection.noFieldsConfirmTitle` | إنشاء نقطة نهاية دون حماية حقول؟ | Create an endpoint without protected fields? |
| `mcpProtection.noFieldsConfirmBody` | ستتمكن نقطة النهاية من إرجاع القيم المسموح بها كما هي. يمكنك إضافة حقول محمية لاحقًا. | The endpoint may return permitted values as-is. You can add protected fields later. |
| `mcpProtection.databaseScopeTitle` | تحديد كل حقول قاعدة البيانات؟ | Select every field in this database? |
| `mcpProtection.databaseScopeBody` | يشمل هذا {count} حقلًا في جميع الجداول المحمّلة والمتاحة. راجع النطاق قبل المتابعة. | This includes {count} available fields across the loaded tables. Review the scope before continuing. |
| `mcpProtection.derivativeWarning` | قد تحمي جداول أيضًا المشتقات التي تكشف معلومات من هذه الحقول. | Jadawel may also protect derivatives that reveal information from these fields. |
| `mcpProtection.suggestedPersonalData` | قد يحتوي بيانات شخصية | May contain personal data |
| `mcpProtection.loadingFields` | جارٍ تحميل الحقول… | Loading fields… |
| `mcpProtection.loadFailed` | تعذّر تحميل الحقول كاملة. | The complete field list could not be loaded. |
| `mcpProtection.retry` | إعادة المحاولة | Retry |
| `mcpProtection.unavailableField` | حقل غير متاح — سيبقى محميًا | Unavailable field — remains protected |
| `mcpProtection.deletedField` | حقل محذوف — ستُزال حمايته عند الحفظ | Deleted field — protection will be removed on save |
| `mcpProtection.reviewAdded` | حقول ستُحمى | Fields to protect |
| `mcpProtection.reviewRemoved` | حقول ستُزال حمايتها | Fields to unprotect |
| `mcpProtection.reviewUnchanged` | حقول دون تغيير | Unchanged fields |
| `mcpProtection.unprotectTitle` | تأكيد إزالة الحماية | Confirm unprotection |
| `mcpProtection.unprotectBody` | ستصبح القيم متاحة عبر نقطة النهاية، ولا يمكن استرجاع ما سبق كشفه. | Values will become available through the endpoint, and prior disclosures cannot be recalled. |
| `mcpProtection.readOnly` | يمكنك عرض السياسة، لكنك لا تملك صلاحية تعديلها. | You can view this policy but cannot edit it. |
| `mcpProtection.conflictTitle` | تغيرت السياسة في جلسة أخرى | Policy changed in another session |
| `mcpProtection.conflictBody` | أعد التحميل وقارن التغييرات قبل الحفظ. | Reload and compare changes before saving. |
| `mcpProtection.reloadCompare` | إعادة التحميل والمقارنة | Reload and compare |
| `mcpProtection.unsavedTitle` | تجاهل التغييرات؟ | Discard changes? |
| `mcpProtection.unsavedBody` | لم تُحفظ تعديلات سياسة حماية الحقول. | Protection policy changes have not been saved. |
| `mcpProtection.statusActive` | الحماية نشطة | Protection active |
| `mcpProtection.statusSuspended` | نقطة النهاية معلّقة | Endpoint suspended |
| `mcpProtection.statusBlocked` | الحماية متوقفة بأمان | Protection safely blocked |
| `mcpProtection.save` | حفظ السياسة | Save policy |
| `mcpProtection.saved` | تم حفظ سياسة حماية الحقول. | Protection policy saved. |

Keep placeholders and Western digits unchanged. Run strict locale parity and update
`docs/GLOSSARY_AR.md` only if implementation introduces another recurring term; the
four core terms are already present.

#### 7. Add protected-artifact approval

- Add `artifacts/models.py`, `artifacts/services.py`, `artifacts/adapters.py`, and a
  forward `0008_mcp_artifact_approval.py` migration under Arabase. Store draft HTML,
  content/configuration digests, stable manifest field relations, exact approval
  bindings, revocation metadata, and content-blind events—never values or tokens.
- Change Arabase-owned `mcp/page/services.py`, `api/html_page/views.py`, and the page
  source/settings UI so MCP and human edits create drafts. Keep the current approved
  page active until exact authorized approval promotes a replacement.
- Validate approval before querying authenticated or public row feeds and before
  returning the HTML document. Bind it to endpoint, policy/access versions, artifact
  digest, field manifest, view configuration, approver permissions, and private or
  public audience. Any stale binding blocks the whole document and feed.

Exit gate: first publish, replacement, private-to-public change, policy/config change,
permission loss, manual revoke, restore, import/duplicate, and embedded-token attempts
all behave as specified without persisting protected content.

### Threat-focused automated test matrix

Create focused backend suites under `backend/tests/arabase/mcp/protection/`:

| Suite | Required proof |
|---|---|
| `test_policy_api.py` | owner-only full-set replace, cross-workspace rejection, idempotent replay, revision conflict, no key/generation/audit leakage |
| `test_policy_migrations.py` | forward backfill, constraints/indexes, populated snapshot, safe reversibility only before activation |
| `test_lifecycle.py` | rename, supported/unsupported conversion, trash/restore/delete at every hierarchy, permission/account/key changes, atomic rollback |
| `test_token_vault.py` | entropy/envelope, digest-only records, typed HMAC, TTL, key rotation/removal, cross-endpoint/row/field/revision rejection |
| `test_capacity.py` | exact 10k/50k reservation, 2/6 semaphore, 250 ms rejection, partial write, restart, memory thresholds, TTL recovery |
| `test_provenance.py` | multi-level formula, lookup, rollup, link labels, `0`, `false`, `null`, broken cycles/dependencies, unknown adapter |
| `test_query_guard.py` | protected search/filter/sort/group/count/membership rejected before query |
| `test_round_trip.py` | omit/token/literal/empty semantics, display-only rejection, stale/copy/misplacement, 200-row atomic create/update rollback |
| `test_egress.py` | every tool contract, future tool denial, 4 MiB preflight, no partial content, revision recheck before release |
| `test_observability.py` | canaries absent from Django/Loguru/SSE/Sentry/audit/access output; fixed safe errors and unsampled safe audit events |
| `test_artifact_approval.py` | exact draft/manifest/audience approval, runtime checks on both feeds, invalidation/revoke/restore/import behavior |
| `test_readiness.py` | dedicated alias, TTL canary, policy/config/script/memory checks, public liveness independence |

Add narrow compatibility tests to existing
`backend/tests/jadawel/core/mcp/test_mcp_server.py` and transport tests for the generic
hook and log sanitization. Keep all feature behavior in Arabase tests.

Frontend tests belong under `web-frontend/modules/arabase/mcp/__tests__/` and must use
the repository's frontend-test skill. Cover all three entry paths, lazy tree/search,
tri-state selection, duplicate names with full paths, zero-policy confirmation,
database bulk confirmation, add/remove review, unavailable/deleted fields, lost
permission, unsaved changes, 409 reload/compare, key reveal timing, keyboard and ARIA
behavior, and Arabic/English snapshots.

Add `e2e-tests/tests/mcp/protectedFields.spec.ts` plus an MCP test client helper. Run
the settings and page-onboarding flows in Arabic RTL and English LTR at 1440x900 and
390x844, then perform real `list_table_rows` and `update_rows` round trips. Assert
physical RTL placement, no horizontal overflow, no console errors, no plaintext in
MCP payloads, and no partial database change after one invalid token.

### Performance and CI gates

- Add Redis 7 with `maxmemory 128mb` and `maxmemory-policy noeviction` to the focused
  backend CI job. Keep the normal full suites and fork-hygiene tests unchanged.
- Add a release-blocking protection load command that runs at least three backend
  processes and five endpoints. Fifty calls issue 1,000 tokens each across direct,
  formula, lookup, rollup, and linked-label values; call 51 fails closed, memory stays
  near or below the 73 MiB estimate, and redemption works on another worker.
- Run a 12-call simultaneous spike: only six enter and the remainder fail within
  250 ms. Run 200-row create/update with one invalid token and with Redis interrupted;
  both leave zero partial changes.
- Compare protected and unprotected calls on the same data: added p95 is at most
  15 ms for 100 tokens and 75 ms p95 / 150 ms p99 for 1,000; total CranL-class
  protected list p95 is at most 500 ms.
- Required local/CI commands after implementation are:

```bash
cd backend
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run python src/jadawel/manage.py makemigrations --check --dry-run
uv run pytest tests/arabase/mcp/protection tests/arabase/test_html_page_mcp.py -q
uv run pytest tests/jadawel/core/mcp tests/jadawel/contrib/database/mcp -q
uv run pytest tests/arabase -q
uv run pytest tests -q -n 2

cd ../web-frontend
node scripts/check-locale-parity.mjs --strict
yarn lint
yarn test

cd ..
just e2e run
```

The implementation must also add and pass
`uv run python src/jadawel/manage.py mcp_protection_check --strict` and the focused
load command; those do not exist in the planning checkout yet.

### CranL release and rollback sequence

1. Provision a separate 256 MiB Redis service. Set `maxmemory 128mb`,
   `maxmemory-policy noeviction`, authentication/TLS, the protection URL and keyring,
   but leave both rollout flags absent. Reload the CranL app so workers receive the
   configuration; do not activate a policy yet.
2. Publish Release A through **Publish all-in-one image**, pin the returned immutable
   digest in the root `Dockerfile`, redeploy, and wait for migrations. Run the strict
   protection check, confirm one empty policy per endpoint, confirm full health sees
   the vault, and prove existing unprotected MCP behavior is unchanged.
3. Add only `mcp-protected-fields-staff`, reload, and create one disposable staff-owned
   canary endpoint. Protect representative text, number, boolean, formula, lookup,
   rollup, and linked-label fields. Complete the live proof below and observe at least
   one full 24-hour TTL window or an accelerated equivalent in staging before broad
   activation.
4. If every gate passes, publish/pin any canary fixes, add
   `mcp-protected-fields`, reload, and verify one newly created ordinary-user endpoint
   plus one existing empty endpoint. Record image digest, migration state, vault
   configuration fingerprint, test run, and correlation IDs in the deployment note.

Rollback rules are intentionally asymmetric:

- Before `POLICY_BECAME_NONEMPTY` exists, remove rollout flags and redeploy the prior
  pinned digest. Leave additive empty tables in place unless the strict command proves
  migration reversal safe.
- After that audit marker exists, never run an older image. Remove rollout flags to
  block new non-empty policies and policy weakening, keep current enforcement active,
  mark affected endpoints protection-blocked when needed, and deploy a forward fix.
- A Redis outage or unsafe memory state does not roll back the app: ordinary UI and
  public liveness remain available, while protected MCP calls and protected artifact
  feeds fail closed. Do not point protection at the shared application Redis as an
  emergency workaround.
- Never delete the migration tables, fingerprint keys, or previous verification key
  until no live tokens can reference them and the strict check approves retirement.

### Live evidence required before calling the feature complete

- API: create an endpoint and non-empty policy atomically, read it back without secret
  fields, provoke an optimistic revision conflict, and verify lifecycle status/audit.
- MCP read: list representative rows and prove every direct or derived protected
  semantic leaf is a fixed token envelope while schema and proven-public structure
  remain visible. Search/order/count dependent on protection must fail safely.
- MCP write: return a same-cell token to preserve, use a literal to replace, then
  retry a stale, copied, display-only, malformed, foreign-endpoint, and expired token;
  every invalid batch must leave rows unchanged.
- Artifact: submit a protected page draft, prove it cannot render before approval,
  approve privately, then prove configuration, policy, permission, public-audience,
  and revocation changes block both document and row feed until exact reapproval.
- Observability: seed unique canaries as values, tokens, endpoint keys, malformed
  arguments, and exception messages; search app/Caddy logs, Sentry events, traces,
  metrics, action history, and protection audit output and find zero matches.
- Operations: authenticated `/api/_health/full/` reports the dedicated vault ready;
  public `/api/_health/` remains 200 when the vault is deliberately unavailable;
  protected calls return fixed `PROTECTION_UNAVAILABLE` and recover after restoration.
- UI: attach desktop/mobile Arabic and English screenshots, keyboard/ARIA results,
  console output, locale-parity result, and proof that Arabic renders the selector on
  the physical right.
- Performance: attach the exact load report and Redis `INFO MEMORY` evidence for the
  50,000-record boundary, concurrency rejection, latency deltas, and TTL recovery.

## Repository evidence

- MCP execution currently serializes arbitrary tool results in
  `jadawel/core/mcp/registries.py`, catches exceptions in `core/mcp/__init__.py`, and
  logs raw SSE bodies/messages and validation details in `core/mcp/sse.py`. These are
  the smallest unavoidable generic enforcement and observability seams.
- Endpoint persistence and APIs are core-owned, but the frontend settings registry
  and backend registries support unregister/register replacement. Arabase already
  uses those additive patterns in `ArabaseConfig.ready()` and
  `modules/arabase/registryPlugin.js`.
- Page models, MCP page tools, authenticated/public row feeds, onboarding, page
  runtime, and locales are already Arabase-owned, so artifact approval requires no
  new upstream page-model patch.
- Current MCP list rows clamps to the repository's 200-row page limit; MCP create and
  update accept unbounded Pydantic lists. The new interceptor must enforce 200 before
  mutation rather than relying on REST serializers.
- One shared `REDIS_URL` currently backs Celery, RedBeat, results, Channels, and
  caches; the local 256 MiB Redis process has neither `maxmemory` nor `noeviction`.
  Production isolation and readiness cannot be inferred from current configuration.
- CranL deploys a prebuilt `prod-lite` image: pushing source changes nothing. The
  repository's documented release path is publish image, pin its digest in the root
  Dockerfile, redeploy, and verify the live service.

## Resolution

Implement the feature as an additive Arabase protection subsystem behind one generic
core MCP call-interceptor seam. Land content-blind errors/logging, normalized policy
and audit persistence, a dedicated bounded Redis vault, provenance-aware contracts,
all-or-nothing round trips, the shared Arabic-first policy flow, and exact artifact
approval in that dependency order. Keep policy enforcement unconditional once a
policy exists; rollout flags govern admission only.

Release in three operational stages: feature-off schema/backfill, staff canary, then
general admission. Require the complete threat, locale/RTL, cross-worker, capacity,
latency, observability, artifact, and live MCP proofs above. Before the first non-empty
policy, an old digest remains a possible rollback; afterward, only fail-closed
operation and a forward fix are safe.
