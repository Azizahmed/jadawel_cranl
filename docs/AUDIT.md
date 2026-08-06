# Arabic / RTL Audit — Baserow 2.2.2 baseline (Jadawel fork)

> **Status:** IN PROGRESS — backend/data/search evidence captured against a live
> 50K-row seed (run 2026-07-03). Visual RTL rows (§1–4, §9) still need a browser +
> native-Arabic eye. This document is the Phase 0 deliverable that produces the
> **prioritized defect list feeding Phases 1–2**.
>
> **Phase 1.1 update (2026-07-03):** the Arabic locale + RTL direction infrastructure
> is now wired (see "Phase 1.1 evidence" below). The `en`/LTR baseline captured here is
> still the reference; re-run the visual rows against the new `ar`/RTL default to record
> before/after.

## Baseline run — 2026-07-03
- Stack: `docker compose` dev (Postgres **14** `pgvector`, Redis, backend/runserver,
  web-frontend/nuxt-dev, celery + celery-beat, caddy). All containers healthy.
- Data: `seed_arabic_data --rows 50000` → **table 3** (workspace 3, database 3),
  50,000 rows inserted in **7.5 s**; per-workspace search table populated.
- Stack verification: grid **CRUD** ok (rows list/read via API on 50K), **realtime**
  ok (`broadcast_to_group`/`broadcast_to_channel_group` celery tasks succeed),
  **Celery** worker + beat healthy and running periodic tasks. No premium/enterprise
  code paths or migrations present.
- ⚠️ **Methodology note:** Arabic query strings sent through **Windows Git-Bash/curl
  get mangled** (all Arabic host-curl searches falsely returned 0). Reliable Arabic
  testing must run **inside the backend container** (Django ORM / manage.py shell) or
  in the **browser** — not host curl. All §5 numbers below are from inside the container.

## Phase 1.1 evidence — Arabic locale + RTL direction (2026-07-03)
The locale infrastructure (task set §1.1 of the plan) is implemented and verified
**headlessly against the live dev stack**:
- **Backend:** `settings.LANGUAGE_CODE == "ar"` and `("ar", "Arabic") in settings.LANGUAGES`
  (container shell). New-user default language reads `LANGUAGE_CODE` live, so
  `JADAWEL_DEFAULT_LOCALE` is honoured per deploy. Core migration
  `0115_jadawel_add_arabic_language` applied; `core` migration state clean.
- **Frontend SSR:** `GET http://localhost:3000/login/` → HTTP 200 emits
  **`<html lang="ar" dir="rtl">`** (single `dir="rtl"`, single `lang="ar"` — set
  server-side by the arabase direction plugin, so there is no LTR→RTL first-paint flash).
- **Translation pipeline:** the translated key `action.signIn` renders as **«تسجيل الدخول»**
  in the login SSR payload, proving `ar.json` files load and merge across module langDirs
  with English fallback for untranslated keys.
- **Direction propagation:** `dir` is set on the root `<html>`, which is what carries RTL
  into Teleported DOM (modals/dropdowns/tooltips mount under `<body>`). This is the
  mechanism that addresses §9.4; still to be confirmed visually in the browser pass.

**Not yet done (needs the browser + native-Arabic pass):** locale switcher round-trip
(persist to user profile + live `<html dir>` flip), and all the visual RTL rows below
(§1–4, §9) now that the default is `ar`/RTL. Formal sign-off in `docs/RTL_REVIEW.md`.

## Why this document exists
Baserow was not built Arabic-first. Before we start the RTL/locale work (Phase 1) and
the Arabic data-layer work (Phase 2), we record **exactly how the unmodified 2.2.2 core
behaves** with Arabic content, with evidence, so we (a) know the real defect surface,
(b) can prioritize, and (c) have before/after references for regression checks.

## How to reproduce (environment)
```bash
# 1. Bring up the dev stack
just dc-dev build --parallel
just dc-dev up -d

# 2. Create an admin user (first run)
just dc-dev exec backend ./baserow createsuperuser

# 3. Seed the Arabic dataset (also creates the bidi/search edge-case rows)
just dc-dev exec backend ./baserow seed_arabic_data --rows 50000
#   → note the printed table id / workspace id

# 4. Open the app (default http://localhost:3000), sign in, open the seeded table.
```
Record the browser + OS + zoom for each screenshot. Put images under
`docs/assets/audit/` and link them from the tables below.

Severity scale: **S1** blocker (data wrong/unusable) · **S2** major (clearly broken UX)
· **S3** minor (cosmetic) · **S4** polish. Verdict: ✅ ok · ⚠️ partial · ❌ broken · ⬜ not-yet-tested.

---

## 1. Grid rendering with Arabic text
| # | Check | Expected (Arabic-first) | Observed | Verdict | Sev | → Phase |
|---|-------|-------------------------|----------|---------|-----|---------|
| 1.1 | Text cell alignment | Aligns to inline-start (right in RTL) | | ⬜ | | 1.3 |
| 1.2 | Ellipsis/truncation direction | Truncates at inline-end, RTL-aware | | ⬜ | | 1.3 |
| 1.3 | Cursor/caret in cell editor | Caret behaves RTL; Home/End correct | | ⬜ | | 1.3 |
| 1.4 | Row height / line-height for Arabic | No clipping of diacritics/descenders (~1.6) | | ⬜ | | 1.2 |
| 1.5 | Primary field + row-number anchoring | Anchors right; frozen col on inline-start | | ⬜ | | 1.3 |

## 2. Mixed bidi content (Arabic + Latin/numbers in one cell)
Use the seeded **Notes** column and the `Ali (علي)` / `عبدالله ١٢٣` edge-case rows.
| # | Check | Expected | Observed | Verdict | Sev | → Phase |
|---|-------|----------|----------|---------|-----|---------|
| 2.1 | Arabic sentence containing `CT-2023-1234` | Latin code stays LTR, not scrambled | | ⬜ | | 1.3 |
| 2.2 | Name `Ali (علي)` in a cell | Legible, parentheses not flipped wrongly | | ⬜ | | 1.3 |
| 2.3 | `dir=auto` per text cell | Direction chosen per cell by bidi algo | | ⬜ | | 1.3 |

## 3. Numbers / dates rendering inside RTL rows
| # | Check | Expected | Observed | Verdict | Sev | → Phase |
|---|-------|----------|----------|---------|-----|---------|
| 3.1 | Iqama (digit string) column | Forced LTR, digits never reorder | | ⬜ | | 1.3 |
| 3.2 | Gregorian date column | Western digits, LTR, consistent | | ⬜ | | 1.3 |
| 3.3 | Eastern Arabic numerals (٠-٩) display | Default Western; Eastern is a later toggle | | ⬜ | | 2/5 |

## 4. Sorting Arabic text columns
Sort the **Name** column ascending/descending.
| # | Check | Expected | Observed | Verdict | Sev | → Phase |
|---|-------|----------|----------|---------|-----|---------|
| 4.1 | Default Postgres collation order | Likely NOT matching Arabic expectation | | ⬜ | | 2.2 |
| 4.2 | With `ar-SA-x-icu` collation | Correct Arabic alphabetical order | | ⬜ | | 2.2 |
| 4.3 | Alef/hamza variants ordering | أ/إ/آ/ا grouped as users expect | | ⬜ | | 2.2 |

## 5. Search (normalization) — TESTED (container-side, 50K seed)
**Good news / baseline:** Baserow full-text search uses Postgres config `simple`, which
tokenises on whitespace/punctuation and **preserves Arabic tokens**. So **exact-form**
Arabic works: `القحطاني`→2349, `أحمد`→1057, `مدرسة`→1, `SKU`(control)→8311. `escape_postgres_query`
does not strip Arabic (`القحطاني` → `$$القحطاني$$:*`). ✅

**The gap = normalization (Phase 2.2):** query variants that a user expects to match do
**not**, because `simple` does no Arabic folding. Verified via ILIKE (`icontains`) and
equally true for full-text (same tokens):

| # | Query | Should match | Observed (baseline) | Verdict | Sev | → Phase |
|---|-------|--------------|----------|---------|-----|---------|
| 5.1 | `مدرسه` (ta-ha) | `مدرسة الأمل` | **0 matches** (exact `مدرسة`=1) | ❌ | S2 | 2.2 |
| 5.2 | `احمد` (no hamza) | `أحمد …` | **0 matches** (exact `أحمد`=1057) | ❌ | S2 | 2.2 |
| 5.4 | `القران` (no madda) | `القرآن الكريم` | **0 matches** (exact `القرآن`=1) | ❌ | S2 | 2.2 |
| 5.5 | `عيسي` (ya vs alef-maqsura) | `عيسى بن مريم` | 0 (to re-confirm) | ⬜ | S2 | 2.2 |
| 5.6 | `محمد` | `محــمــد` (tatweel) | 0 (to re-confirm) | ⬜ | S2 | 2.2 |
| 5.7 | `محمد` | `مُحَمَّد` (diacritics) | 0 (to re-confirm) | ⬜ | S2 | 2.2 |

→ Phase 2.2 must add an `IMMUTABLE` normalize() (strip tashkeel/tatweel; fold alef/hamza/
madda, ta-marbuta, alef-maqsura) applied on both column and query, plus a GIN trigram
index on the normalized expression. Confirms the plan's design.

## 6. CSV import — encodings
Prepare three copies of the same Arabic CSV: **Windows-1256**, **UTF-8-BOM**, **UTF-8**.
| # | File | Expected | Observed | Verdict | Sev | → Phase |
|---|------|----------|----------|---------|-----|---------|
| 6.1 | windows-1256 | Detected/selectable; Arabic intact | | ⬜ | | 2.3 |
| 6.2 | utf-8-bom | BOM handled, no stray characters | | ⬜ | | 2.3 |
| 6.3 | utf-8 | Clean import | | ⬜ | | 2.3 |
| 6.4 | Import preview | Shows encoding + per-column type, overridable | | ⬜ | | 2.3 |

## 7. XLSX import
| # | Check | Expected | Observed | Verdict | Sev | → Phase |
|---|-------|----------|----------|---------|-----|---------|
| 7.1 | Arabic headers | Preserved, not mangled | | ⬜ | | 2.3 |
| 7.2 | Arabic sheet names | Preserved | | ⬜ | | 2.3 |
| 7.3 | Eastern Arabic numerals in cells | Parsed as numbers (configurable) | | ⬜ | | 2.3 |
| 7.4 | Date columns (Hijri vs Gregorian) | Detected/prompted where possible | | ⬜ | | 2.1/2.3 |

## 8. CSV export
| # | Check | Expected | Observed | Verdict | Sev | → Phase |
|---|-------|----------|----------|---------|-----|---------|
| 8.1 | Default export opens in Excel (Windows) | UTF-8 **with BOM**, Arabic intact | | ⬜ | | 2.3 |
| 8.2 | windows-1256 export option | Available | | ⬜ | | 2.3 |

## 9. Chrome / secondary UI
| # | Check | Expected | Observed | Verdict | Sev | → Phase |
|---|-------|----------|----------|---------|-----|---------|
| 9.1 | Formula bar with Arabic | RTL-correct, editable | | ⬜ | | 1.3 |
| 9.2 | Filter / sort / group-by panels | RTL layout | | ⬜ | | 1.4 |
| 9.3 | View sidebar | RTL layout | | ⬜ | | 1.4 |
| 9.4 | Modals/dropdowns/menus (`Teleport`) | `dir` propagates into portalled DOM | | ⬜ | | 1.1 |
| 9.5 | Row detail / expanded record | Full RTL | | ⬜ | | 1.3 |
| 9.6 | Public form view | RTL + Arabic (customer-facing) | | ⬜ | | 1.4 |
| 9.7 | Kanban / calendar / gallery | Must be usable (full polish Phase 5) | | ⬜ | | 5 |

---

## Prioritized defect list (feeds Phases 1–2)
> Fill after running the matrix. One row per confirmed defect, sorted S1 → S4.

| ID | Severity | Area (§) | Summary | Evidence | Target phase |
|----|----------|----------|---------|----------|--------------|
| D-1 | S2 | §5 | Arabic search has no normalization: ta-marbuta/hamza/alef/madda/tatweel/diacritic variants don't match | `مدرسه`/`احمد`/`القران` → 0 vs exact forms match (container test, 50K) | 2.2 |
| _(visual §1–4, §9 defects added after browser pass)_ | | | | | |

## Performance baseline (50K-row seed)
> Record on the seeded table so we can detect regressions against the Phase-1/2 budget
> (grid interaction < 16 ms/frame; list API p95 < 300 ms).

> **Caveat:** numbers below are from the **dev** stack (Django `runserver`, not gunicorn;
> Postgres 14 pgvector). Treat as rough dev baselines; re-measure on the production
> profile (gunicorn + PG16/ICU) for the real budget check.

| Metric | Value (dev) | How measured | Date |
|--------|-------|--------------|------|
| Seed insert 50K rows | 7.5 s total | seed_arabic_data timing | 2026-07-03 |
| List 200 rows (grid page proxy) | ~0.43 s | curl `time_total`, 3 samples (0.44/0.43/0.43) | 2026-07-03 |
| Total row count query | instant | API `count`=50000 | 2026-07-03 |
| Initial grid load (table open → first paint) | | DevTools Performance | |
| Scroll frame time (sustained fast scroll) | | DevTools Performance / FPS | |
| Sort Name column (50K rows) | | Network timing on view request | |
| List rows API p95 (prod gunicorn) | | Repeated calls / k6 | |

## Native-speaker review
Formal RTL sign-off happens in Phase 1 (`docs/RTL_REVIEW.md`). Note here any blocking
Arabic-correctness issues found during this baseline audit that can't wait.
