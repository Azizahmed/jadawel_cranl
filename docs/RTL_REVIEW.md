# RTL / Arabic Review & Sign-off — Jadawel (جداول)

Phase 1 acceptance requires a **native Arabic speaker** to review the app in `ar`/RTL and
sign off. This document is the running checklist and the record of each review session.
It complements `docs/AUDIT.md` (which captured the *unmodified baseline*); here we record
the state **after** the RTL/locale work as it lands.

## How to review
1. Bring up the dev stack (Arabic is the default now):
   `env UID=9999 GID=9999 POSTGRES_PORT=5433 docker compose --env-file .env.docker-dev -f docker-compose.yml -f docker-compose.dev.yml up -d`
2. Open http://localhost:3000, sign in as `admin@jadawel.local` / `Password123!`.
3. Confirm the app loads Arabic + RTL by default. Toggle to English via the language
   switcher to compare LTR.
4. Use the seeded **table 3** (workspace 3 → database 3) — it contains the Arabic + bidi
   edge-case rows.
5. Record findings against the checklist; file defects into `docs/AUDIT.md`'s prioritized
   defect list with a `Dn` id.

Verdict scale: ✅ correct · ⚠️ usable but off · ❌ broken · ⬜ not-yet-reviewed.

## Checklist

### A. App shell & chrome
| # | Item | Verdict | Notes |
|---|------|---------|-------|
| A.1 | `<html dir="rtl" lang="ar">` on first paint (no LTR flash) | ✅ | Verified headless via SSR (AUDIT §1.1) and in Chrome. |
| A.2 | Sidebar anchors to the right; icons/chevrons mirrored | ✅ | **Browser-verified 2026-07-04**: sidebar renders on the right, Arabic labels (الرئيسية/الإشعارات/الأعضاء…). |
| A.3 | Top bar / view switcher RTL | ✅ | **Browser-verified 2026-07-23**: `header.scss` converted to logical props; filter items pack from inline-start (first item x=944), search pushed to inline-end (x=10), view-switcher panel opens at its trigger using `select__`/`context__` styles. |
| A.4 | Language switcher: switches live, persists to user profile | ✅ | **Browser-verified 2026-07-23**: login-page switcher flips `<html dir/lang>` live (ar→fr→ar, no reload, cookie tracks); Account settings save persists to DB (`profile.language` checked via backend shell) and flips UI live both directions. |
| A.5 | Modals / dropdowns / context menus inherit RTL (Teleport) | ✅ | **Browser-verified 2026-07-23**: filter/sort/group/view-switcher contexts render under `<body>` (outside `#__nuxt`) with computed `direction: rtl`; settings modal fully Arabic. Context positioning made RTL-aware in `Context.vue` (see below). |
| A.6 | Arabic UI font renders cleanly (weight, line-height ~1.6) | ⚠️ | IBM Plex Sans Arabic self-hosted + wired (400/500/600/700), RTL line-height 1.6. Font file serves 200. **Confirm rendering.** |

### B. Grid
| # | Item | Verdict | Notes |
|---|------|---------|-------|
| B.1 | First/primary column + row numbers anchor right | ✅ | **Browser-verified 2026-07-04**: frozen الاسم column + row numbers render on the right (DOM: x1536–1808). |
| B.2 | Horizontal scroll direction correct (RTL scrollLeft) | ⚠️ | Column-drag coordinates, insertion indicators, and auto-scroll deltas normalized to inline-start via `modules/database/utils/gridViewDrag.js` (handles Chrome negative `scrollLeft`), with LTR/RTL unit tests. **Browser stress-test with overflowing columns still pending.** |
| B.3 | Frozen columns stick to inline-start | ✅ | **Verified**: `.grid-view__left` inset-inline-start:0 → right edge in RTL. |
| B.4 | Header/body column alignment | ✅ | **Verified**: fixed `.grid-view__rows` anchor; header رقم الإقامة sits exactly over its data (both x1620–1820). |
| B.5 | Number/date/phone cells forced LTR, digits never scramble | ✅ | **Browser-verified**: Iqama numbers & Greg/Hijri dates render LTR, aligned; Eastern digits (عبدالله ١٢٣) and bidi `Ali (علي)` legible. |
| B.6 | Cell editor caret / Tab / Enter navigation direction | ⬜ | |
| B.7 | Arrow keys move visually (Left = left on screen) | ⬜ | |
| B.8 | Column / sidebar width resize drags in the right direction | ✅ | **User-reported defect, fixed & browser-verified 2026-07-25**: `HorizontalResize` used a physical pointer delta, so every handle worked in reverse under RTL. Now converts to an inline delta. Verified live: column 167→247px dragging toward inline-end and back; sidebar 240→300px likewise. Unit tests in `test/unit/core/components/horizontalResize.spec.js`. |

### C. Views & forms
| # | Item | Verdict | Notes |
|---|------|---------|-------|
| C.1 | Filter / sort / group-by panels RTL | ✅ | **Browser-verified 2026-07-23**: panels open on-screen anchored inline-start (Context.vue RTL mirror + offset negation); filter row flows حيث→field→condition right-to-left; sortings/group-bys/filters SCSS converted to logical props. |
| C.2 | Row detail / expanded record RTL | ⚠️ | row_modal/row_edit_modal SCSS converted to logical props (2026-07-23 sweep); visual pass pending. |
| C.3 | Public form view RTL + Arabic (customer-facing) | ✅ | **Browser-verified 2026-07-23**: live Arabic form (view 55, table 4) renders RTL, IBM Plex Arabic, required marks, mirrored submit; end-to-end public submit created row 17. |
| C.4 | Kanban / calendar / gallery usable (full polish Phase 5) | ⚠️ | gallery/card SCSS converted to logical props; visual pass pending. |

### D. Language quality
| # | Item | Verdict | Notes |
|---|------|---------|-------|
| D.1 | Terminology matches `docs/GLOSSARY_AR.md` | ⬜ | Needs native review — bulk of the 3,482-key set is a guarded machine first pass. |
| D.2 | No untranslated English leaking in high-traffic screens | ⚠️ | **Key parity complete: 3,482/3,482 across all 7 locale families** (strict `yarn locale:check` gate passes, re-verified 2026-07-23, exit 0). Linguistic/contextual quality still needs native review. |
| D.3 | Interpolation/placeholders intact (`{name}`, counts) | ✅ | Enforced mechanically by the strict parity checker (interpolation/link/tag/escape mismatch = CI failure). |
| D.4 | Tone appropriate for Saudi enterprise/government | ⬜ | |

## Grid engine RTL — DONE (browser-verified 2026-07-04)
The custom-virtualised grid now renders RTL correctly. Fixed in commit 4e5a8cfb8:
frozen section anchors to the inline-start (right) edge; the `.grid-view__rows`
wrapper was re-anchored so body cells line up under the flex header (was the main
visible desync); the 4 inline `left: leftWidth` styles + section CSS use logical
properties. Verified in Chrome against the seeded Arabic table (see B.1/B.3/B.4/B.5).

**Remaining grid item:** horizontal scroll-direction (`scrollLeft`) behaviour when
columns overflow the viewport — Chrome reports negative `scrollLeft` in RTL. Not yet
stress-tested (the test table fit without horizontal scroll). Needs a wide table to
verify/normalise. Tracks plan §1.3.

## Implemented in the 1.2/1.3 headless pass (ready for visual check)
- Arabic font (IBM Plex Sans Arabic) self-hosted, wired into the stack + RTL priority.
- `<html dir/lang>` from locale (SSR, no flash).
- App shell layout + sidebar converted to CSS logical properties.
- Directional icon flip (horizontal arrows/chevrons) with `.rtl-no-flip` opt-out.
- Numeric/date/identifier cell direction pinned LTR.
- `stylelint-use-logical` guard (error for new arabase code, warning backlog for core).

## Sign-off log
| Date | Reviewer | Scope | Result | Follow-ups |
|------|----------|-------|--------|-----------|
| 2026-07-04 | Claude (automated, Chrome) | App shell + grid engine RTL | PASS — sidebar right, grid frozen col + header/body alignment + LTR digits verified | Native-speaker language review still required; toolbar labels + row-modal/form-view polish pending |
| 2026-07-23 | Claude (verification of GPT-assisted work) | Full translation parity + grid drag RTL | Strict locale parity gate PASS (3,482/3,482, 0 defects, exit 0). Drag normalization util + tests added (not yet browser-verified). | Native review of translation quality; browser pass over WP3+ items in `docs/PHASE_1_COMPLETION_PLAN.md` |
| 2026-07-23 | Claude (automated, in-app browser) | WP3 locale switching + WP4.1/4.2 top bar & panels | PASS — anon SSR defaults ar/rtl (browser Accept-Language can override → product decision); live switcher round-trip ar↔en↔fr with no reload; profile persistence verified in DB; top bar/panels/dropdowns/selects converted to logical props and DOM-verified in RTL; Context.vue positioning made RTL-aware (filter panel overflow + workspace-selector never-opening fixed). vitest 8/8 green in container. | B.2 wide-grid scroll stress; B.6/B.7 keyboard matrix; C.2/C.3 row modal & public form; native review (D.1/D.4) |
| 2026-07-23 | Claude (automated, Chrome DOM probes) | Full logical-properties sweep (~300 SCSS files) + freeze-handle RTL fix + public Arabic form | PASS — grid frozen section/header alignment/freeze handle verified at exact coordinates in RTL; public form verified visually + end-to-end submit | B.2 wide-grid scroll stress test; C.2/C.4 visual passes; native-speaker language review |
| _pending native review_ | | | | |
