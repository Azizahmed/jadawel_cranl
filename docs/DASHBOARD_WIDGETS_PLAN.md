# Dashboard widgets plan — charts + three Jadawel widgets

## Status (2026-08-03)

| Phase | State |
|---|---|
| A — grouped aggregation service | **Implemented and tested** (32 tests green) |
| B — chart widget backend | **Implemented and tested** |
| C — chart widget frontend | **Implemented** (4 variations, settings form, RTL, en+ar); unit tests still to write |
| D1/D2/D3 — the three Jadawel widgets | Not started |

Verified so far:

- `makemigrations --check --dry-run arabase` → *No changes detected*, so the
  hand-written migration matches the models
- `pytest backend/tests/arabase` → **32 passed**
- `ruff check` / `ruff format --check` on the new code → clean
- `prettier --check` and `stylelint` on `modules/arabase` → clean
- `check-locale-parity.mjs --strict` → 3533/3533

Not verified:

- **Frontend unit tests do not exist for the chart widget yet.** The Vue
  templates and imports are gated instead by the production build in the publish
  workflow, which compiles every template — a broken component fails the build
  before anything is deployed. Real unit tests are still owed.
- ESLint could not be run locally (it needs a generated `.nuxt/eslint.config.mjs`);
  prettier and stylelint were run in its place.
- The five failures in `tests/baserow/contrib/dashboard/api/` are **pre-existing**
  — confirmed by running them at the parent commit. They assert English DRF error
  strings that come back in Arabic because the fork defaults `LANGUAGE_CODE` to
  `ar`.

Answers taken for the three open questions at the bottom: the API accepts up to
5 series and the settings UI offers 3; the bucket cap is 100 (`ARABASE_CHART_MAX_BUCKETS`);
no locked tiles are shown.

### Where the code landed

| Piece | Path |
|---|---|
| Grouped aggregation models / service type / serializers | `backend/src/arabase/integrations/local_baserow/` |
| Chart widget model + type | `backend/src/arabase/dashboard/widgets/` |
| Migration (hand-written) | `backend/src/arabase/migrations/0001_chart_widget_and_grouped_aggregation.py` |
| Registry hooks | `backend/src/arabase/apps.py` |
| Backend tests | `backend/tests/arabase/test_grouped_aggregate_rows_service_type.py`, `test_chart_widget_type.py` |
| Frontend widget type / component / settings / form | `web-frontend/modules/arabase/dashboard/` |
| Frontend service type | `web-frontend/modules/arabase/integrations/serviceTypes.js` |
| Registry plugin, locales, tile SVGs, SCSS | `web-frontend/modules/arabase/` |

### Deviations from the plan as written below

1. **No "other" bucket.** Buckets past the cap are dropped after sorting and the
   dispatch result carries `truncated: true`, which the widget surfaces as a
   badge. Rolling the tail into an "other" bucket needs a second query for a
   marginal gain; deferred.
2. **Default sort is the first series descending** when no sort is configured.
   This is what makes the cap safe — without an ordering, a table with more
   distinct values than the cap would show an arbitrary subset.
3. **Sorts are modelled and honoured but have no UI yet.** The API accepts
   `aggregation_sorts`; the settings panel does not expose them.
4. **The grouped service is not offered in the application builder's data source
   picker.** Its frontend type extends `LocalBaserowTableServiceType` rather than
   the data-source mixin, because its only form is dashboard-shaped. Exposing it
   to the builder is a follow-up.
5. **`series_config` supports `color` and `label` only** (no per-series chart type
   for combo charts), and the settings panel does not edit it yet — the chart
   falls back to the palette and the field name.

## Goal

The dashboard's "Add new widget" picker currently offers only **Summary**. The
Bar, Line, Pie and Doughnut tiles shown locked in upstream Baserow are one
premium widget type (`chart`) presented as four *variations* — and this fork
removed `premium/` entirely, so they don't exist here in any form.

This plan implements them natively in Jadawel, plus three new widgets that fit
how Jadawel is actually used (Arabic-first business dashboards):

1. **Chart widget** — bar / line / pie / doughnut (parity with upstream premium)
2. **Records list widget** — latest N rows from a table/view ("أحدث السجلات")
3. **Progress widget** — aggregate vs. a target, as a percent bar/ring
4. **Upcoming dates widget** — agenda of rows whose date field falls in the next N days

## What exists today (verified in this tree)

| Piece | Where | State |
|---|---|---|
| Polymorphic `Widget` base + registry | `backend/src/baserow/contrib/dashboard/widgets/models.py`, `registries.py` | Open registry; `SummaryWidget` is the only registration (`contrib/dashboard/apps.py:72`) |
| Widget CRUD API | `contrib/dashboard/api/widgets/` | Registry-driven, polymorphic — new types need **no new endpoints** |
| Data sources + dispatch | `contrib/dashboard/data_sources/`, frontend `store/dashboardApplication.js` (`dispatchDataSource`) | Generic; any service type wrapped in a data source flows through it |
| Aggregation service | `LocalBaserowAggregateRowsUserServiceType` (`contrib/integrations/local_baserow/service_types.py:1184`) | Single value, **no grouping** — fine for Summary/Progress, insufficient for charts |
| Row-listing service | `LocalBaserowListRowsUserServiceType` | Exists — Records list and Upcoming dates reuse it as-is |
| Frontend widget registry | `web-frontend/modules/dashboard/widgetTypes.js` | `WidgetType.variations` getter already supports the one-type-many-tiles picker UX |
| Chart rendering | `chart.js 3.9.1`, `chartjs-adapter-moment`, `vue-chartjs 5.3.3` in `web-frontend/package.json` | **Already dependencies** (admin dashboard uses them) — zero new packages |
| Fork-specific app | `backend/src/arabase/`, `web-frontend/modules/arabase/` | Exists, currently has no models/migrations |

The only genuinely new machinery is a **grouped aggregation service**:
"group rows by field X (or date bucket), compute aggregation(s) per group."
Everything else is assembly.

## Design decisions

**D1 — New backend code lives in `arabase`, not `contrib/dashboard`.**
New models mean migrations. Upstream keeps adding migrations to
`contrib.dashboard`; fork migrations interleaved there collide on every
upstream merge. `arabase` is fork-owned, so its migration sequence is safe.
Widget models FK to `dashboard.Dashboard` across apps without issue.

**D2 — Keep upstream premium's public type names.**
Widget type `chart`, service type `local_baserow_grouped_aggregate_rows`.
Template/export files reference registry type strings, not app labels — using
upstream's names means upstream dashboard templates containing charts import
instead of being skipped by `sync_templates` (the same skip mechanism we see
today for kanban/timeline views), and our own exports stay portable.

**D3 — One `chart` widget type, four variations.**
Matches upstream UX and the picker's existing `variations` support. The
variation only presets `default_chart_type` on creation; users can switch chart
type in settings afterwards.

**D4 — RTL and Arabic are first-class, not afterthoughts.**
Chart.js supports `rtl: true` and `textDirection` per chart — wire both to the
active locale. Numbers/dates format through the app's existing i18n. Every new
string lands in `en.json` **and** `ar.json` in the same commit: the strict
locale-parity CI gate (`yarn locale:check`) fails the build otherwise.

**D5 — Implementation happens in `Azizahmed/Jadawel`.**
Per `docs/DEPLOY_CRANL.md`: feature work belongs in the main repo, then merges
into `jadawel_cranl`, then a new image is published and pinned. Committing
features straight to the deployment repo diverges the trees.

---

## Phase A — grouped aggregation service (backend)

The foundation; charts are unusable without it.

New in `backend/src/arabase/integrations/` (registered into the existing
`service_type_registry`):

**Models**
- `LocalBaserowGroupedAggregateRows(LocalBaserowViewService)` — table/view ref,
  filters (reuse `LocalBaserowTableServiceFilterableMixin`)
- `LocalBaserowTableServiceAggregationSeries` — FK to service, `field`,
  `aggregation_type`, `order` (start with the aggregation types the existing
  service supports; same `unsupported_aggregation_types` exclusion)
- `LocalBaserowTableServiceAggregationGroupBy` — FK to service, `field`
  (nullable ⇒ no grouping = single-bucket chart). v1: **one** group-by;
  the model still holds them as a list for forward compatibility.
- `LocalBaserowTableServiceAggregationSortBy` — sort on group label or series
  value, asc/desc

**Service type** `local_baserow_grouped_aggregate_rows`
- `dispatch_data`: build the table model queryset, apply view/service filters,
  `.values(group_field).annotate(...)` one annotation per series; cap at
  `ARABASE_CHART_MAX_BUCKETS` (default 100, largest-N-plus-"other" beyond it)
- Group-by on single select resolves option labels (and colors — the frontend
  can color pie slices with the select option colors); on date/datetime fields
  v1 groups by day (date bucketing granularity is a v2 setting)
- `generate_schema` / `get_context_data` following the existing aggregate
  service's pattern
- Export/import serialization (`SerializedDict`, field/id remapping in
  `deserialize_property`) so template import and workspace duplication work

**Tests** `backend/tests/arabase/` (keeps the fork-hygiene suite location):
dispatch with/without grouping, per-aggregation-type results, filters, trashed
field/view handling, export/import round-trip, permission checks via the data
source (already enforced by the dashboard layer).

Estimate: **3–4 days**.

## Phase B — chart widget (backend)

- `ChartWidget(Widget)` in `arabase`: `data_source` FK (PROTECT, mirroring
  `SummaryWidget`), `default_chart_type` (`bar|line|pie|doughnut`),
  `series_config` JSON (per-series color/label overrides)
- `ChartWidgetType(WidgetType)` — clone the `SummaryWidgetType` lifecycle
  (auto-create data source on create, trash/restore/delete cascade,
  serialize/deserialize `data_source_id`), but create the data source with the
  grouped service type
- Register in `arabase/apps.py`; one `arabase` migration
- Tests: CRUD via the widget API, duplication, trash/restore, export/import

Estimate: **1–2 days**.

## Phase C — chart widget (frontend)

New under `web-frontend/modules/arabase/dashboard/` (registered from
`modules/arabase/plugin.js` into the `dashboardWidget` registry):

- `ChartWidgetType` with `variations` returning the four tiles (bar / line /
  pie / doughnut), each passing `default_chart_type` in `params`; four SVG tile
  images matching `summary_widget.svg`'s style
- `ChartWidget.vue` — header/context-menu/misconfigured-badge structure copied
  from `SummaryWidget.vue`; body renders via `vue-chartjs` (`Bar`, `Line`,
  `Pie`, `Doughnut`), `rtl` + `textDirection` from the active locale,
  `maintainAspectRatio: false` so it fills the widget frame
- `ChartWidgetSettings.vue` + `GroupedAggregateRowsDataSourceForm.vue`
  (pattern: `AggregateRowsDataSourceForm.vue`): table/view picker, group-by
  field picker, series editor (field + aggregation, add/remove), chart-type
  switcher, per-series color override
- Colors: default palette from select-option colors when grouping by single
  select, otherwise the app palette
- Locales: `en.json` + `ar.json` together (D4)
- Tests per the `write-frontend-unit-test` skill: widget renders from mocked
  dispatch data; settings form emits correct updates; empty/misconfigured states

Estimate: **4–5 days**. Charts total: **~2 weeks** including review slack.

## Phase D — the three Jadawel widgets

Ordered cheapest-first; each is independently shippable after Phase B's
patterns exist (D1 and D3 don't even need Phase A).

### D1. Records list widget (`records_list`) — ~2–3 days
Latest N rows from a table/view. **Reuses `local_baserow_list_rows` as-is** —
no new service. Model: `data_source` FK + `row_limit` (default 5, max 20) +
displayed-fields selection. Renders a compact RTL-correct list/table; each row
links to the record in its grid view. This is the "recent requests /
أحدث الطلبات" widget every operations dashboard starts with.

### D2. Progress widget (`progress`) — ~2 days
Aggregate vs. target. **Reuses the existing ungrouped
`local_baserow_aggregate_rows`** — no new service. Model: `data_source` FK +
`target_value` (decimal) + display style (`bar|ring`) + optional color
thresholds (red/amber/green). Body: percent toward target. Covers quotas,
collection targets, SLA attainment — the most-requested KPI style in Saudi
business dashboards.

### D3. Upcoming dates widget (`upcoming_dates`) — ~3 days
Agenda of rows whose chosen date field falls within the next N days (7/14/30),
soonest first, overdue flagged. Reuses `local_baserow_list_rows` plus a
date-window filter applied at dispatch (small service subclass or dispatch-time
filter injection — decide during D3). Displays Gregorian dates through the
existing i18n; **Hijri display is explicitly out of scope for v1** (tracked as
a follow-up, since it touches date formatting globally).

A plain **Text/heading widget** (title + markdown body, no data source) costs
about half a day and makes dashboards self-documenting — recommended as a
freebie alongside any phase.

## Rollout

1. Branch from the feature repo's mainline in `Azizahmed/Jadawel` (D5); ship
   phases as separate PRs (A+B together, C, then D widgets individually)
2. Gates per PR: `just b test`, `just f test`, `yarn locale:check`, `just lint`
3. Merge into `jadawel_cranl` `main` → run **Publish all-in-one image** with a
   new tag → bump `ARG JADAWEL_IMAGE` in the root `Dockerfile` → Deploy on
   CranL (per `cranl_fix.md` runbook)
4. After charts ship: re-run `sync_templates` — upstream templates whose
   dashboards contain chart widgets will import them instead of skipping (D2
   naming decision is what makes this work)

## Order and effort summary

| # | Deliverable | Effort | Depends on |
|---|---|---|---|
| A | Grouped aggregation service | 3–4 d | — |
| B | Chart widget backend | 1–2 d | A |
| C | Chart widget frontend (4 variations) | 4–5 d | B |
| D1 | Records list widget | 2–3 d | patterns from B/C |
| D2 | Progress widget | 2 d | patterns from B/C |
| D3 | Upcoming dates widget | 3 d | patterns from B/C |
| — | Text widget (optional freebie) | 0.5 d | — |

Total: roughly **3 weeks** of focused work for everything; the four chart
widgets alone are **~2 weeks** and remove the biggest visible gap with
upstream's paid tier.

## Open questions (decide before Phase A starts)

1. Multiple series in v1, or single series with the model shaped for more?
   (Recommendation: model supports N, settings UI allows up to 3.)
2. Cap `ARABASE_CHART_MAX_BUCKETS` at 100 with "other" bucket — acceptable?
3. Should the picker keep showing locked tiles for anything? (Recommendation:
   no — in a fork with no paid tier, locked tiles are noise.)
