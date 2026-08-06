# Arabic-First Jadawel Fork — Implementation Plan

> **Audience:** Claude Code (agentic execution). Work phase by phase. Do not start a phase until the previous phase's acceptance criteria pass. Commit small, commit often, one concern per PR.

---

## 0. Project Context (read first)

- **Product:** Arabic-first, RTL-native online spreadsheet-database ("lightweight Airtable"), targeting Saudi SMEs and government entities replacing Excel.
- **Base:** Fork of [Baserow](https://github.com/baserow/baserow) — Django 5.x + DRF backend, Nuxt 3 / Vue 3 / TypeScript frontend, PostgreSQL, Redis, Celery, Django Channels (realtime).
- **Strategy decisions (locked):**
  1. Use Jadawel's native backend. **No InsForge.**
  2. **Option B on enterprise features:** rebuild SSO (OIDC first), audit logs, and advanced RBAC ourselves on the MIT core. Nafath integration comes in a later phase.
  3. RTL is implemented **in the frontend fork code** (not runtime hacks), using CSS logical properties + `dir` propagation.
- **Deployment target:** self-hosted in Saudi Arabia (PDPL compliance). Docker Compose first, Helm later.

### ⚠️ Legal guardrail — NON-NEGOTIABLE
- The Jadawel repo is open-core. **Never copy, import, reference, or adapt any code from `premium/` or `enterprise/` directories.** They are proprietary.
- Step 1 of Phase 0 is to **strip these directories from our fork** so they cannot leak into our build.
- All enterprise-equivalent features (SSO, audit logs, RBAC) must be written from scratch in our own apps/modules.

### Repo & branch strategy
- `main` — our product.
- `upstream` remote → `jadawel/jadawel`. Track upstream releases; rebase/merge quarterly.
- Keep our changes isolated to make upstream merges cheap:
  - **Backend:** new Django apps under `backend/src/arabase/` (working codename — replace globally when brand is chosen). Registered via Jadawel's plugin/registry system. Avoid editing core files; when unavoidable, keep a `PATCHES.md` log listing every core file touched and why.
  - **Frontend:** new Nuxt module/layer under `web-frontend/modules/arabase/` for additive code; direct edits to core components (RTL) tracked in `PATCHES.md`.

---

## Phase 0 — Environment, Fork Hygiene, and Arabic Audit (Week 1–2)

### Tasks
1. Fork Jadawel (latest stable 2.x tag). Add `upstream` remote.
2. **Delete `premium/` and `enterprise/` directories.** Remove all references: settings/app registration, frontend module imports, Docker build steps, CI. The build must be green with them gone.
3. Stand up dev environment: `just dc-dev build --parallel && just dc-dev up -d`. Verify grid CRUD, realtime sync between two browser tabs, Celery jobs.
4. Add CI (GitHub Actions): backend pytest, frontend unit tests, ESLint/ruff, Docker image build.
5. **Arabic audit — produce `docs/AUDIT.md`** documenting current behavior with evidence (screenshots/notes) for:
   - Grid rendering with Arabic text (alignment, ellipsis/truncation direction, cursor behavior in cell editors)
   - Mixed bidi content (Arabic sentence containing Latin product codes / numbers)
   - Sorting Arabic text columns (does Postgres collation order match user expectation? test with/without `ar-SA-x-icu` collation)
   - Search: query "مدرسه" should match "مدرسة" (ta marbuta); "احمد" should match "أحمد" (hamza/alef variants) — record current failures
   - CSV import of a **Windows-1256** encoded file, a UTF-8-BOM file, and a plain UTF-8 file
   - XLSX import: Arabic headers, Arabic sheet names, RTL-formatted cells, dates
   - Number/date rendering (must remain LTR/Western digits by default inside RTL rows; Eastern Arabic numerals as a later user toggle)
   - Formula bar / filter UI / view sidebar behavior when text is Arabic
6. Seed script: generate a realistic 50K-row Arabic dataset (names, Iqama numbers, Hijri+Gregorian dates, mixed-language notes) for all future perf/RTL testing.

### Acceptance criteria
- Clean build & CI green with premium/enterprise removed.
- `docs/AUDIT.md` complete with a prioritized defect list feeding Phases 1–2.
- 50K-row seed loads and grid scrolls smoothly (baseline perf numbers recorded).

---

## Phase 1 — RTL Frontend + Arabic Locale (Week 2–6)

> Detailed completion and release-gate plan: `docs/PHASE_1_COMPLETION_PLAN.md`.

Arabic is the **primary** locale; English secondary. RTL must be first-class, not mirrored-as-afterthought.

### 1.1 Locale infrastructure
- Add `ar` locale to the i18n setup (vue-i18n / Nuxt i18n). Arabic is the default locale for new installs (env-configurable: `DEFAULT_LOCALE=ar`).
- Locale switcher persists per-user (backend user profile field + frontend store).
- `<html dir>` and `lang` set from locale at the app shell level; `dir` must propagate into portalled/teleported elements (modals, dropdowns, context menus, tooltips) — audit every `Teleport` target.
- Translation workflow: extract all keys; machine-translate first pass; flag for human review. Keep glossary file `docs/GLOSSARY_AR.md` (e.g., table = جدول, view = عرض, field = حقل, workspace = مساحة عمل) for consistency.

### 1.2 CSS strategy
- Global refactor to **CSS logical properties**: `margin-left → margin-inline-start`, `left → inset-inline-start`, `text-align: left → start`, border/padding equivalents. Do this file-by-file with visual regression checks; do not blind global-regex the SCSS.
- Add stylelint rule (`stylelint-use-logical`) to CI to prevent regressions.
- Icons/chevrons that imply direction (expand arrows, breadcrumb separators, indent icons) flip under `[dir=rtl]`; icons that are universal (search, settings) do not. Maintain an explicit allowlist/denylist.
- Arabic typography: ship a proper Arabic UI font (recommend **IBM Plex Sans Arabic** or **Noto Sans Arabic**), font stack falls back per locale; check line-height (Arabic needs ~1.6+), grid row height token adjustable.

### 1.3 Grid engine RTL (the core work)
Jadawel's grid is custom-virtualized — this is where most effort goes:
- Column layout: in RTL, first column (incl. row-number + primary field, frozen behavior) anchors right; horizontal scroll math inverted. Beware `scrollLeft` browser inconsistencies in RTL (Chrome negative values vs old WebKit) — normalize via a utility.
- Frozen/sticky columns stick to the **inline-start** edge.
- Cell content rules by field type (critical for data legibility):
  - Text fields: `dir=auto` per cell (bidi algorithm decides), align `start`.
  - Number, currency, phone, duration, date fields: **force `dir=ltr`, align `end` visually consistent** so digits never bidi-scramble.
  - URL/email: `dir=ltr`.
- Cell editors: caret behavior, selection, and Enter/Tab navigation direction (Tab moves visually leftward in RTL = next column logically).
- Keyboard navigation: Arrow keys move **visually** (ArrowLeft goes left on screen regardless of dir); document the mapping and test it.
- Context menus, column resize handles, drag-to-reorder columns/rows — all mirrored.
- Row detail modal / expanded record: full RTL layout.

### 1.4 Other views & chrome
- Sidebar, top bar, view switcher, filter/sort/group-by panels: RTL.
- Form view (public forms): RTL + Arabic — this is customer-facing, polish matters.
- Kanban/calendar/gallery: defer full polish to Phase 5, but must not be broken (acceptable = usable, logged issues).

### Acceptance criteria
- Playwright visual-regression suite runs the same scenario set in `ar`/RTL and `en`/LTR; zero layout-breaking diffs in grid, sidebar, modals, form view.
- Bidi test table (from Phase 0 seed) renders correctly: numbers LTR inside RTL rows, mixed text legible.
- Native Arabic speaker review session logged with sign-off checklist in `docs/RTL_REVIEW.md`.

---

## Phase 2 — Arabic Data Layer Plugins (Week 4–8, overlaps Phase 1)

All backend work here as **Jadawel plugins/registries** in `backend/src/arabase/` — no core edits.

### 2.1 Hijri date field type
- New field type `hijri_date` via Jadawel's field-type registry.
- Storage: canonical **Gregorian date in Postgres** + display conversion (use `hijri-converter` (Umm al-Qura calendar) on backend; `@umalqura/core` or equivalent on frontend). Never store Hijri as the source of truth — arithmetic/filtering/sorting stays Gregorian.
- Field options: display calendar (hijri / gregorian / both), format string.
- Filters ("date is", before/after, ranges) accept Hijri input, convert at the API boundary.
- Bonus (flag-gated): dual-display formatter on the standard date field.

### 2.2 Arabic search & sorting
- **Sorting:** enable ICU collation. Migration creates `ar-SA-x-icu` collation; text-field sort uses it when workspace locale = ar (workspace-level setting).
- **Search normalization:** normalization function (Postgres `IMMUTABLE` SQL function + mirrored Python util):
  - Strip tashkeel/diacritics (U+064B–U+0652, U+0670)
  - Normalize alef variants (أ إ آ ٱ → ا), ta marbuta (ة → ه) — make ta-marbuta folding configurable, ya/alef maqsura (ى → ي)
  - Strip tatweel (ـ)
- Apply in Jadawel's search path (`contains` filter + global search): compare `normalize(column) LIKE normalize(query)`; add expression **GIN trigram index on the normalized expression** for perf at 100K+ rows.
- Unit tests: مدرسه↔مدرسة, احمد↔أحمد, قرآن with/without madda, tatweel-padded text.

### 2.3 Import/export hardening
- CSV import: encoding detection (`charset-normalizer`) with explicit support for **Windows-1256**, UTF-8, UTF-8-BOM; user-facing encoding override dropdown in the import UI.
- CSV export: default UTF-8 **with BOM** (so Excel on Windows opens Arabic correctly); option for windows-1256.
- XLSX import: preserve Arabic headers/sheet names; type inference must not mangle Eastern Arabic numerals (٠١٢٣ → parse as numbers, configurable); date columns detect both calendars where possible (heuristic: year < 1500 → likely Hijri, prompt user).
- Import preview screen: show detected encoding + per-column type with ability to override (this screen is the product's first impression — invest in it).

### Acceptance criteria
- Hijri field: create/edit/filter/sort round-trips correctly; converter tested against known Umm al-Qura reference dates.
- Search tests above pass; EXPLAIN shows index usage on 100K-row normalized search.
- The three Phase-0 problem files (win-1256, utf8-bom, utf8) import cleanly end-to-end; exported CSV opens correctly in Excel with Arabic intact.

---

## Phase 3 — Enterprise Features Rebuild (Week 8–14)

Written from scratch (Option B). New Django apps: `arabase.sso`, `arabase.audit`, `arabase.rbac`. **Do not look at Jadawel premium/enterprise code.**

### 3.1 SSO — OIDC first
- OIDC RP via `mozilla-django-oidc` or `authlib`: Azure AD/Entra (most common in Saudi orgs), Google Workspace, generic OIDC.
- Config per-instance via env/admin (multi-tenant IdP config deferred).
- JIT user provisioning + optional domain-restricted auto-join to a workspace.
- SAML: defer unless a pilot customer demands it (OIDC covers Entra).
- **Nafath (Phase 6, design now):** Nafath is an OAuth-style national ID flow requiring registration with the Saudi Digital Government Authority; abstract our auth provider interface so Nafath drops in as another provider later. Document the interface contract in `docs/AUTH_PROVIDERS.md`.

### 3.2 Audit log
- Append-only `audit_event` table: actor, workspace, ip, user-agent, action type, target (table/row/field/view), before/after summary (JSONB, size-capped), timestamp.
- Capture via DRF middleware + signals on Jadawel action registry (Jadawel's action system for undo/redo is a natural hook point — subscribe, don't modify).
- Admin UI (frontend module): filterable log per workspace, CSV export.
- Retention policy setting + Celery purge job. Partition table by month from day one.

### 3.3 RBAC
- Roles beyond Jadawel core's member/admin: `viewer`, `commenter`, `editor`, `builder`, `admin` at workspace level; per-table role overrides.
- Enforce in DRF permission classes wrapping Jadawel's handler layer; deny-by-default for overrides.
- Frontend: role management UI in workspace settings; UI affordances hide/disable actions the role can't perform (server remains source of truth).

### Acceptance criteria
- OIDC login e2e against a test Entra tenant; provisioning + workspace auto-join works.
- Every mutating API action produces exactly one audit event; audit write failure never blocks the action (fail-open with error metric).
- RBAC matrix test suite: role × action grid fully covered; a `viewer` cannot mutate anything via direct API calls.

---

## Phase 4 — Deployment & Compliance (Week 12–16, overlaps)

- Production Docker Compose profile: Postgres 16 (with ICU), Redis, Caddy, backend, frontend, Celery workers/beat.
- Target Saudi hosting (choose: STC Cloud, Oracle Jeddah, or local colo). Document region + data-flow diagram for PDPL (`docs/PDPL.md`): what data, where stored, subprocessors, retention.
- Backups: nightly `pg_dump` + WAL archiving to in-Kingdom object storage; restore drill documented and tested.
- TLS everywhere, security headers, rate limiting at Caddy.
- Observability: Sentry (self-hosted if PDPL requires), Prometheus + Grafana for Postgres/Celery/API latency.
- Smoke-test checklist for release: import 50K rows, realtime sync, OIDC login, audit event flow.

### Acceptance criteria
- One-command production deploy on target infra; restore drill passes; PDPL doc reviewed.

---

## Phase 5 — Product Polish & Pilot (Week 14–18)

- Arabic-first onboarding flow: "Upload your Excel" as the primary CTA.
- Template gallery (Arabic): HR/Iqama expiry tracker (killer template — include expiry-date views + color rules), project tracker, tenders/procurement log, school records.
- Kanban/calendar RTL polish (deferred from Phase 1).
- Landing/marketing site (separate repo), Arabic-first.
- 3–5 pilot customers; feedback loop into backlog.

---

## Phase 6 — Nafath Integration (post-pilot)

- Register with DGA, obtain Nafath API credentials (business process, start paperwork during Phase 3).
- Implement as an auth provider behind the Phase-3 interface: initiate request → push notification → poll/callback with random-number verification UX.
- Map national ID to user identity; decide policy for gov workspaces (Nafath-required flag per workspace).

---

## Working Rules for Claude Code

1. Read `docs/AUDIT.md` and `PATCHES.md` before touching core files.
2. Never read or copy from `premium/`/`enterprise/` (should already be deleted — if any reference resurfaces from upstream merges, strip it).
3. Every core-file edit gets a `PATCHES.md` entry: file, reason, upstream-merge risk.
4. Backend changes: pytest coverage required. Frontend RTL changes: Playwright visual test in both `ar` and `en` before merge.
5. Prefer Jadawel's registries (field types, view types, actions, plugins) over core edits — always check for a registry hook first.
6. All user-facing strings through i18n; no hardcoded text. Arabic string added in the same PR as the English one.
7. Performance budget: grid interactions < 16ms frame on 50K-row seed; API p95 < 300ms on list endpoints. Regressions block merge.
