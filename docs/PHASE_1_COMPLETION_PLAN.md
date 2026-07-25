# Phase 1 Completion Plan — Arabic Locale and RTL

**Status:** In progress  
**Baseline date:** 2026-07-18  
**Scope:** Finish Phase 1 of `IMPLEMENTATION_PLAN.md` and make the complete current
Jadawel interface available in Arabic, with English retained as the secondary locale.

## 1. Outcome and definition of done

Phase 1 is complete only when an Arabic-speaking user can perform every supported
workflow without a layout-breaking RTL defect or an unexplained English fallback.

The release gate is:

1. Every English locale key in the current frontend has a reviewed Arabic counterpart.
2. Arabic and English both work on first render and after a live locale switch.
3. The app shell, database grid, editors, panels, modals, forms, and secondary views are
   usable in RTL without breaking their LTR behavior.
4. Automated locale-parity, unit, end-to-end, and visual-regression checks pass in CI.
5. A native Arabic speaker completes and signs `docs/RTL_REVIEW.md`.
6. `docs/AUDIT.md` is updated with final evidence and has no unresolved Phase 1 S1/S2
   defects.

Phase 2 work—Hijri fields, Arabic search normalization, ICU collation, and import/export
enhancements—is explicitly outside this plan, except where Phase 1 must ensure those
screens are RTL-ready.

## 2. Current baseline

### Implementation status (2026-07-19)

- WP0 migration repair is complete: `database` migration `0209` freezes the
  OSS-only `FormView.mode` choices, and both `makemigrations --check --dry-run`
  and `manage.py check` pass in the dev stack.
- WP1 now has `web-frontend/scripts/check-locale-parity.mjs`, with focused Vitest
  coverage. `yarn locale:check` is the final strict release gate; it fails for every
  missing key and every malformed, blank, unexpected, sentinel, marker,
  interpolation/link/tag/escape mismatch, or unexplained English-identical value.
- CI now runs the strict `yarn locale:check` release gate. The retained baseline limits
  are all zero, so neither command permits a missing Arabic key.
- All seven Arabic locale families now have complete key parity. Automation, Builder,
  Core, Database, Dashboard, Integrations, and the shared locale have no fallback-only
  sections remaining.
- The completed translation set combines reviewed hand translations with a guarded
  machine-generated first pass. It preserves placeholders, linked messages, HTML tags,
  and escapes, but still requires contextual native Arabic review before release.

### Independent verification (2026-07-23)

- `node scripts/check-locale-parity.mjs --strict` re-run on the working tree:
  **3,482/3,482 translated, 0 missing, exit 0** across all seven locale families.
- WP0 confirmed in git history (`a8aa6fc21` — migration `0209` committed).
- The 9 modified backend email templates under `backend/src/baserow/core/templates/`
  are **line-endings-only churn** (empty `git diff --numstat`) — restore rather than
  commit them.
- The WP1/WP2 work (parity tooling, translations, `gridViewDrag.js` + tests, SCSS
  logical-prop conversions, eslint 9 fix, CI parity job) is **not yet committed** —
  it sits in the working tree.
- Vitest suites (`localeParity.spec.js`, `gridViewDrag.spec.js`) not independently
  re-run this session: the dev container was down and Docker Desktop failed to start;
  host has no `node_modules`. Re-verify when the stack is next up.

### Implemented

- Arabic is registered on the backend and frontend and is the configurable default.
- SSR emits `<html lang="ar" dir="rtl">` without an LTR first-paint flash.
- The Jadawel Nuxt module propagates locale direction and loads RTL styles.
- IBM Plex Sans Arabic is self-hosted.
- The app shell and sidebar use logical layout properties.
- Directional icons can flip in RTL, with an opt-out for non-directional icons.
- The grid's frozen section anchors on the right, header/body alignment is fixed, and
  numeric/date/identifier content is kept LTR.
- Column drag coordinates, insertion indicators, and auto-scroll deltas are normalized
  to inline-start, with focused LTR/RTL regression coverage.
- The 50K-row Arabic seed exists and the main grid behavior has been browser-checked.

### Translation inventory

The inventory below compares recursively flattened `en.json` keys with the matching
`ar.json` file. A key counts as translated when the Arabic file contains the same key;
linguistic quality still requires review.

| Locale file | English keys | Matching Arabic keys | Missing | Coverage |
|---|---:|---:|---:|---:|
| `locales` | 640 | 640 | 0 | 100.0% |
| `modules/automation/locales` | 144 | 144 | 0 | 100.0% |
| `modules/builder/locales` | 777 | 777 | 0 | 100.0% |
| `modules/core/locales` | 815 | 815 | 0 | 100.0% |
| `modules/dashboard/locales` | 21 | 21 | 0 | 100.0% |
| `modules/database/locales` | 812 | 812 | 0 | 100.0% |
| `modules/integrations/locales` | 273 | 273 | 0 | 100.0% |
| **Total** | **3,482** | **3,482** | **0** | **100.0%** |

Strict parity passes with no missing, unexpected, blank, sentinel, token-mismatched,
unexplained English-identical, or non-Arabic values. Linguistic and contextual quality
still requires native review.

### Known incomplete RTL behavior

- Top bar and view switcher.
- Live locale switching and persistence verification.
- Teleported modals, dropdowns, context menus, and tooltips.
- Cross-browser verification of wide-grid RTL scrolling and column dragging.
- Cell editor caret, Home/End, Tab/Enter, and visual arrow-key behavior.
- Filter, sort, group-by, and field configuration panels.
- Expanded-row/detail modal and public form view.
- Kanban, calendar, and gallery minimum-usability pass.
- Complete native-language and terminology review.

## 3. Delivery sequence

Each work package should be a focused commit or pull request. Do not start Phase 2 until
all release gates in section 5 pass.

### WP0 — Restore a green Phase 1 baseline

1. Review and cherry-pick commit `ffc7e1f0f` from
   `claude/affectionate-bose-6f330f`. It adds the missing no-op FormView mode migration
   required after removing the premium survey mode.
2. Run `makemigrations --check`, Django checks, fork-hygiene tests, frontend unit tests,
   lint, and both Docker image builds.
3. Fix the local Storybook `.nuxt/types` permission failure so Storybook can be included
   in visual review.
4. Configure a writable Jadawel `origin` remote and push `main` before further work; keep
   `upstream` read-only for Baserow updates.
5. Confirm the repository has no real uncommitted content changes before starting.

**Exit:** migration state is clean, the core dev stack and Storybook start, and the
baseline CI workflow passes.

### WP1 — Add enforceable locale-quality tooling

Create `web-frontend/scripts/check-locale-parity.mjs` and run it in CI. It must:

- recursively compare all English and Arabic locale files;
- fail on missing or unexpected keys;
- fail when interpolation tokens differ (`{name}`, `{count}`, linked keys, plural
  variants, HTML tags, and escaped characters);
- report values that are identical to English for review, with an allowlist for brands,
  protocols, formulas, API tokens, and other intentionally Latin terms;
- detect blank values and temporary `_note`, `TODO`, or machine-translation markers;
- emit per-file and total coverage in CI output.

Add focused tests for locale loading, Arabic fallback behavior, and malformed locale
files.

**Exit:** the checker accurately reports the current 3,351-key gap and cannot silently
regress after translation work begins.

### WP2 — Translate the complete product

Translate in user-journey batches so each batch can be reviewed in the running app.
Use `docs/GLOSSARY_AR.md` as the terminology source of truth. Machine translation may
produce a draft, but no batch is complete until it has contextual review.

#### Batch 2A — Access, onboarding, and workspace shell

- Shared actions, common labels, dates, errors, and permissions.
- Login, signup, password reset, email verification, and two-factor authentication.
- Onboarding, dashboard, workspace creation, invitations, members, settings,
  notifications, trash, templates, and account management.

#### Batch 2B — Database critical path

- Database/table/view creation and context menus.
- Grid toolbar, fields and field forms, rows, search, filters, sorting, grouping,
  aggregation, row height, frozen fields, and view sharing.
- Row detail/edit forms, history, comments/mentions where available, snapshots,
  API-token screens, and database API documentation UI.
- Form, gallery, Kanban, and calendar view labels.

#### Batch 2C — Import, export, and data synchronization UI

- Import source selection, preview, validation errors, progress, and reports.
- CSV/JSON/XML/paste/Airtable/PostgreSQL synchronization screens.
- Export dialogs, formats, progress, sharing, webhook, and synchronization settings.
- Keep encoding and Hijri-specific behavior for Phase 2, but translate and RTL-proof all
  existing controls now.

#### Batch 2D — Application Builder

- Pages, elements, data sources, events/actions, themes, domains, authentication,
  visibility, responsive/device controls, publishing, and guided tours.
- Verify Builder preview canvas direction separately from the editor's own direction;
  user-built pages must be able to choose their intended direction.

#### Batch 2E — Automations and integrations

- Automation graph, nodes, triggers, actions, execution history, simulation, settings,
  errors, and guided tours.
- HTTP, SMTP, AI, Slack, router, iteration, and local-table integration forms.
- Keep provider and protocol names in Latin where required by the glossary/allowlist.

#### Batch 2F — Advanced and lower-frequency namespaces

- Formula functions/types/errors, field documentation, API docs, webhooks, health/admin
  screens, AI configuration, and remaining shared namespaces.
- Remove all `_note` sentinels and resolve every parity-check exception.

For every batch:

1. Preserve interpolation and plural forms exactly.
2. Use neutral Modern Standard Arabic suitable for Saudi enterprise/government users.
3. Keep numbers Western (0–9) by default and technical tokens LTR.
4. Review strings in context; avoid translations that are technically correct but too
   long for buttons, tabs, and narrow grid menus.
5. Add accepted terms to the glossary before using a new translation repeatedly.
6. Capture screenshots of representative desktop and narrow layouts.

**Exit:** locale parity is 3,482/3,482, with zero unexplained English values, missing
keys, placeholder mismatches, blank strings, or sentinel keys.

### WP3 — Complete locale switching and direction propagation

1. Verify Arabic is the default for new users and anonymous/public pages when both
   locale environment variables are `ar`.
2. Verify the language switcher updates Vue i18n, `<html lang>`, and `<html dir>` without
   refresh and persists through the existing user-profile API.
3. Verify logout/login and a new browser session restore the selected language.
4. Verify server rendering and hydration agree, with no direction flash or hydration
   warning.
5. Audit every `Teleport`/portal target and third-party overlay; modals, dropdowns,
   tooltips, date pickers, rich-text menus, and context menus must inherit direction.
6. Add unit and Playwright coverage for Arabic→English→Arabic switching.

**Exit:** locale and direction remain correct across SSR, hydration, live switching,
portals, persistence, and public pages.

> **Status 2026-07-23 (browser-verified):** items 1–2 and 5 verified in the in-app
> browser: anonymous SSR emits `<html lang="ar" dir="rtl">` with no cookie; the
> login-page switcher flips locale/dir live without reload (ar↔en↔fr) and the account
> settings save persists to `profile.language` (checked in the DB) while flipping the
> UI live; Teleported contexts under `<body>` compute `direction: rtl`. Note: for
> anonymous visitors, `detectBrowserLanguage` (Accept-Language) overrides the `ar`
> default and re-sets the cookie — decide whether Arabic-first should win for anon
> visitors. Items 3–4 (fresh-session restore, hydration-flash audit) spot-checked OK
> during the round-trip; item 6 (unit + Playwright coverage) still open → WP6.

### WP4 — Finish the RTL component surfaces

Convert physical positioning one component family at a time, using CSS logical
properties and browser checks after each family.

1. Top bar, breadcrumbs, view switcher, tabs, resize handles, and split panes.
2. Filter, sort, group-by, field configuration, view options, and formula controls.
3. Row detail/expanded record, file/select/date editors, comments/history, and linked-row
   selectors.
4. Public form view, validation, submission confirmation, and shared/public views.
5. Workspace/account/admin settings, import/export dialogs, notification panels, and
   onboarding/guided tours.
6. Builder, Automation, and Integrations editor chrome.
7. Kanban, calendar, and gallery: achieve usable RTL now; record non-blocking polish for
   Phase 5.

Use an explicit icon-direction registry or documented CSS classes. Flip only icons with
directional meaning; search, settings, media controls, and provider logos must not flip.

**Exit:** no Phase 1 screen has clipped Arabic text, reversed controls, misplaced
overlays, or an LTR-only interaction.

> **Status 2026-07-23:** families 1–2 converted and browser-verified: `header.scss`
> (top bar), `context/dropdown/select` (menus + view switcher), `filters/sortings/
> group_bys` (panels), plus `modal/auth/row_modal/toast/tooltip/datepicker` statically
> converted. `Context.vue` positioning made RTL-aware (mirror `horizontal` + negate
> `horizontalOffset`) — fixes the filter-panel viewport overflow and the workspace
> selector refusing to open in RTL. Families 3–7 still open; JS-positioned bits
> (tooltip cursor vars, fixed dropdowns) intentionally stay physical.

### WP5 — Finish grid and editor RTL behavior

1. Add a normalized RTL scroll utility covering negative, positive-descending, and
   positive-ascending browser `scrollLeft` models.
2. Use normalized logical scroll positions in virtualized column calculations, frozen
   boundaries, resize/reorder handles, drag auto-scroll, and programmatic scroll-to-cell.
3. Test narrow and wide tables with no frozen fields, one frozen field, and multiple
   frozen fields.
4. Define and test visual keyboard behavior:
   - Arrow Left/Right moves visually on screen.
   - Tab/Shift+Tab follows the documented logical record-editing order.
   - Enter, Home, End, selection extension, and editor opening/closing are predictable.
5. Verify caret and selection behavior for Arabic, Latin, mixed bidi text, URLs, phone
   numbers, dates, currency, and Eastern/Western digits.
6. Verify field menus, resize handles, drag-to-reorder, row selection, and expanded-row
   opening in both directions.

**Exit:** the wide-grid, keyboard, caret, resize, drag, and virtualization matrix passes
in Chromium, Firefox, and WebKit.

### WP6 — Automated regression suite

Add a Phase 1 Playwright project that runs each scenario in both `ar`/RTL and `en`/LTR:

- anonymous login/signup/password-reset pages;
- authenticated dashboard and sidebar;
- wide seeded grid, cell editing, filters/sorts/groups, and row detail;
- import/export modal;
- public form and shared grid;
- workspace/account settings and overlays;
- Builder, Automation, and Integrations representative screens;
- Kanban, calendar, and gallery smoke checks;
- language switching and persistence.

Store deterministic visual baselines by locale and viewport. Add interaction assertions
alongside screenshots so a visually plausible but functionally reversed control fails.

Add Vitest coverage for direction helpers, icon-flip rules, locale switching, and RTL
scroll normalization. Add accessibility checks for document language, focus order,
labels, and keyboard reachability.

**Exit:** CI runs locale parity, lint, unit tests, Playwright interactions, and visual
comparisons for both directions.

### WP7 — Native review, audit closure, and release candidate

1. Re-run the 50K Arabic seed and complete every row in `docs/AUDIT.md` and
   `docs/RTL_REVIEW.md`.
2. Have at least one native Arabic speaker review every translation batch and the full
   end-to-end workflow. Prefer a second reviewer for terminology used in Saudi
   government/enterprise settings.
3. Record reviewer, date, scope, defects, and resolution in `docs/RTL_REVIEW.md`.
4. Measure initial grid paint, sustained scrolling, sort timing, and API p95. Compare
   against the Phase 1 performance budget.
5. Resolve every Phase 1 S1/S2 issue. Assign S3/S4 polish explicitly to Phase 5 only when
   it does not impair comprehension or task completion.
6. Run the complete CI suite and Docker smoke test from a clean checkout.

**Exit:** native review is signed, audit evidence is complete, CI is green, and the
Phase 1 release candidate is reproducible from a clean checkout.

## 4. Suggested pull-request order

| Order | Pull request | Depends on |
|---:|---|---|
| 1 | Baseline migration/Storybook/CI repair | — |
| 2 | Locale parity and placeholder checker | 1 |
| 3 | Shared + Core Arabic translation | 2 |
| 4 | Database + import/export Arabic translation | 2 |
| 5 | Builder Arabic translation | 2 |
| 6 | Automation + Integrations Arabic translation | 2 |
| 7 | Locale switch/persistence/Teleport tests | 3 |
| 8 | Remaining component RTL conversions | 3–6 |
| 9 | Grid scroll and keyboard RTL | 1 |
| 10 | Cross-browser visual and interaction suite | 7–9 |
| 11 | Native review fixes and audit closure | 10 |

Translation PRs may run in parallel after the parity checker lands, but each must own
disjoint locale files or clearly separated namespaces to avoid merge conflicts.

## 5. Final acceptance checklist

### Locale and translation

- [x] Arabic/English key parity is 100% across all seven locale families.
- [x] Zero missing, unexpected, blank, sentinel, or placeholder-mismatched keys.
- [x] Identical-to-English values are limited to a reviewed technical allowlist.
- [ ] All translation batches have contextual native review.
- [ ] Glossary is updated and terminology is consistent.
- [ ] No unexplained English appears in the automated Arabic UI crawl.

### RTL behavior

- [ ] SSR, hydration, live switching, persistence, and Teleports preserve direction.
- [ ] App shell, top bar, panels, dialogs, settings, and editors pass RTL review.
- [ ] Wide-grid scrolling, frozen columns, resize/drag, keyboard, and caret tests pass.
- [ ] Public form/shared views are polished and usable in Arabic.
- [ ] Kanban, calendar, gallery, Builder, Automation, and Integrations are usable in RTL.
- [ ] English/LTR behavior has no regressions.

### Quality and release

- [ ] `makemigrations --check`, lint, unit tests, backend tests, and Docker builds pass.
- [ ] Playwright interaction and visual suites pass in Chromium, Firefox, and WebKit.
- [ ] Phase 1 performance measurements are recorded and within budget.
- [ ] No unresolved Phase 1 S1/S2 defects remain.
- [ ] Native Arabic sign-off is recorded in `docs/RTL_REVIEW.md`.
- [ ] `docs/AUDIT.md`, `docs/GLOSSARY_AR.md`, and `PATCHES.md` reflect the final state.

Only after every checkbox above is satisfied should Phase 1 be marked complete and
Phase 2 implementation begin.
