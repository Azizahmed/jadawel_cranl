# PATCHES.md — Core-file edits log

This file tracks every edit we make to **upstream Baserow core files** (i.e. files
that also exist upstream, outside our additive `backend/src/arabase/` and
`web-frontend/modules/arabase/` code). Each entry records the file, the reason, and
the upstream-merge risk, so quarterly `upstream` rebases/merges are cheap and auditable.

Additive files we create (e.g. under `arabase/`, `docs/`, new CI workflows) are **not**
logged here — only modifications to files that came from upstream.

Legend for **Merge risk**: `low` = isolated/unlikely to conflict · `med` = may conflict
on upstream refactor · `high` = frequently-touched upstream file, expect conflicts.

---

## Phase 0 — Strip proprietary `premium/` and `enterprise/` (2026-07-03)

**Context:** The Baserow repo is open-core. Per the non-negotiable legal guardrail, the
`premium/` and `enterprise/` directories are proprietary and were **deleted** from the
fork. Baserow already supports an OSS-only mode (`BASEROW_OSS_ONLY`), so most of core is
designed to run without these plugins; the edits below remove the remaining build/config
references and one runtime dependency on a setting the enterprise plugin used to inject.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `backend/src/baserow/config/settings/base.py` | Force `BASEROW_OSS_ONLY = True` and `BASEROW_BUILT_IN_PLUGINS = []`; removed `baserow_premium_*`/`baserow_enterprise_*` table names from the CACHALOT lists; added a default for `BASEROW_ENTERPRISE_USER_SOURCE_COUNTING_TASK_INTERVAL_MINUTES` | Stop loading the deleted plugins; keep cache config referencing only existing tables; provide the setting core still reads (see below) | high |
| `backend/pyproject.toml` | Removed `[tool.uv.workspace] members` (premium/enterprise backends), their pytest `pythonpath` entries; set isort `known-first-party = ["baserow", "arabase"]` | Workspace members no longer exist | med |
| `backend/uv.lock` | Regenerated with `uv lock` — dropped `baserow-premium` and `baserow-enterprise` | Keep lock consistent with pyproject so `uv sync --frozen` works | med |
| `backend/Dockerfile` | Removed all premium/enterprise `COPY`/`--mount`/`PYTHONPATH`/`mkdir` refs across builder-prod-base, builder-ci, builder-prod, ci, dev, local stages | Those paths/files no longer exist; build would fail | high |
| `web-frontend/Dockerfile` | Removed premium/enterprise `mkdir`/`COPY`/symlink refs across builder-ci, builder-prod, ci, dev stages | Same | high |
| `web-frontend/config/nuxt.config.base.ts` | Removed `premiumBase`/`enterpriseBase` params and the block pushing the two plugin `module.js` files | Modules deleted | high |
| `web-frontend/package.json` | `test`/`eslint`/`stylelint`/`prettier` scripts no longer reference `../premium`/`../enterprise`; removed `test:premium`/`test:enterprise` | Paths gone | med |
| `eslint.config.mjs` | Removed premium/enterprise file globs | Paths gone | low |
| `e2e-tests/package.json` | Removed `test-enterprise-only` script | Enterprise e2e specs gone | low |
| `deploy/all-in-one/Dockerfile` | Removed premium/enterprise `COPY` + `PYTHONPATH` | Paths gone | med |
| `deploy/all-in-one/supervisor/default_baserow_env.sh` | `PYTHONPATH` trimmed to `backend/src` | Paths gone | low |
| `docker-compose.dev.yml` | Removed the premium/enterprise backend & web-frontend bind-mount volume lines (7 services) | Dirs gone; bind mounts would create empty dirs / error | med |
| `.github/workflows/ci.yml` | Removed premium/enterprise from `paths-filter` and from the `ruff check`/`format` args | Paths gone (CI is reworked in Task 4) | med |
| `config/vscode/.vscode/launch.json`, `settings.json` | Removed premium/enterprise test paths and mypy/analysis extra paths | Dev-editor convenience only | low |

### Known remaining upstream references (intentionally left)
- `backend/src/baserow/core/generative_ai/generative_ai_model_types.py` and
  `.../registries.py` import `baserow_premium.fields.ai_file.AIFile` **only under
  `if TYPE_CHECKING:`**. These are never evaluated at runtime and copy no proprietary
  code (name reference only). Left untouched to minimise core-file churn; will be
  revisited if/when we run `mypy` in CI. **Do not** re-add the `baserow_premium` package.
- `.github/dependabot.yml`, `backend/src/baserow/test_utils/pytest_conftest.py`,
  `backend/src/baserow/contrib/database/mcp/services.py`: comment-only mentions. Harmless.

## Phase 0 — Register the `arabase` app / module (2026-07-03)

Additive scaffolding lives in `backend/src/arabase/` and
`web-frontend/modules/arabase/` (not logged individually — they're our files). The
two core files below are edited only to *register* that additive code:

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `backend/src/baserow/config/settings/base.py` | Appended `"arabase"` to `INSTALLED_APPS` | Load our Django app | med |
| `web-frontend/config/nuxt.config.base.ts` | Appended `./modules/arabase/module.js` to `baseModules` | Load our Nuxt module | med |

## Phase 0 — CI (2026-07-03)

Added `.github/workflows/jadawel-ci.yml` (our own, self-contained, secret-free CI:
ruff, Django check + fork-hygiene tests on a Postgres service, eslint, vitest, and
backend+web-frontend Docker image builds). The upstream Baserow workflows are kept
for reference / cheap merges but their auto-triggers are disabled (set to
`workflow_dispatch` only) because they publish to Baserow's own registry/SaaS/project
infra and need their secrets:

| File | Change | Merge risk |
|------|--------|------------|
| `.github/workflows/ci.yml` | `on:` → `workflow_dispatch` only | med |
| `.github/workflows/publish-release-images.yml` | `on:` → `workflow_dispatch` only | low |
| `.github/workflows/trigger-helm-chart-upload.yml` | `on:` → `workflow_dispatch` only | low |
| `.github/workflows/database-projects-issues-workflow.yml` | `on:` → `workflow_dispatch` only | low |
| `.github/workflows/database-projects-pr-workflow.yml` | `on:` → `workflow_dispatch` only | low |

## Phase 0 — Windows-safe i18n locales (2026-07-03)

Upstream ships `web-frontend/i18n/locales` as a **git symlink → `../locales/`** to
satisfy `@nuxtjs/i18n`'s default `restructureDir: 'i18n'` while keeping the real
translation files in `web-frontend/locales/`. On a Windows checkout
(`core.symlinks=false`) that symlink materialises as an 11-byte text file, so the
Nuxt build (and the bind-mounted dev server) fails with
`ENOTDIR … i18n/locales/en.json`.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/i18n/locales` (symlink) | Removed from git | Non-portable; breaks Windows checkouts / bind-mount dev | med |
| `web-frontend/config/nuxt.config.base.ts` | `langDir: 'locales'` → `'../locales'` | Point i18n straight at the real `web-frontend/locales/`, no symlink needed on any OS | med |

> Note: `.claude/skills` is also a symlink checked out as a file on Windows, but it's
> outside the build/runtime path, so it's left alone.

### Runtime note
`baserow.core.user_sources.handler.update_user_count_...` reads
`settings.BASEROW_ENTERPRISE_USER_SOURCE_COUNTING_TASK_INTERVAL_MINUTES`, which the
enterprise plugin used to inject. The periodic task that calls it was scheduled by the
enterprise plugin (not core), so this path is effectively dormant in the OSS build, but
we define a safe default (10, a divisor of 60) so it can never raise `AttributeError`.

---

## Phase 1.1 — Arabic locale + RTL direction (2026-07-03)

**Context:** Arabic is Jadawel's **primary** locale (English secondary). This phase
adds `ar` as a first-class language on both tiers and makes the default locale
env-configurable so new installs come up Arabic-first.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `backend/src/baserow/config/settings/base.py` | `LANGUAGE_CODE = os.getenv("BASEROW_DEFAULT_LOCALE", "ar")`; prepended `("ar", "Arabic")` to `LANGUAGES` | Make Arabic selectable + the env-configurable default; new-user creation reads `settings.LANGUAGE_CODE` live (see `core.user.handler`) so `BASEROW_DEFAULT_LOCALE` is honoured per deploy | med |
| `backend/src/baserow/core/migrations/0115_jadawel_add_arabic_language.py` | **New** AlterField migration for `userprofile.language` (adds `ar` to choices, default `ar`) | Django requires the migration to live in the model's app (`core`); it's a no-op choices/default change, no data impact | low |
| `web-frontend/config/locales.js` | Added `{ code: 'ar', name: 'العربية', file: 'ar.json', dir: 'rtl' }` (first entry) | Activate the `ar` locale across all module langDirs; `dir: 'rtl'` is the source of truth for direction | med |
| `web-frontend/config/nuxt.config.base.ts` | `defaultLocale` now `process.env.NUXT_DEFAULT_LOCALE || 'ar'` | Arabic-first frontend default, env-overridable to match the backend | med |

**New env var:** `BASEROW_DEFAULT_LOCALE` (backend, default `ar`) / `NUXT_DEFAULT_LOCALE`
(frontend, default `ar`). Set both to `en` to bring the stack up LTR/English for
comparison during the RTL audit.

**Additive (not core edits, not logged in the table):** `ar.json` translation files in
`web-frontend/locales/` and every module `locales/` dir; the arabase frontend plugin that
sets `<html dir/lang>` reactively from the active locale; `web-frontend/modules/arabase/locales/`;
`docs/GLOSSARY_AR.md`.

---

## Phase 1.2–1.3 — RTL foundation: font, logical properties, icon flip (2026-07-03)

**Context:** Make the app render correctly right-to-left. Approach per the plan:
convert to CSS **logical properties** file-by-file (no blind global regex), ship a
proper Arabic UI font, and add a lint guard. Cross-cutting RTL concerns live in the
additive `modules/arabase/assets/scss/arabase.scss` (not logged here); the rows below
are edits to upstream core files.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/modules/core/assets/scss/fonts.scss` | Appended 4 `@font-face` blocks for **IBM Plex Sans Arabic** (weights 400/500/600/700), Arabic `unicode-range`, self-hosted from `static/fonts/ibm-plex-sans-arabic/` | Ship a real Arabic UI face with no runtime CDN (PDPL/KSA self-hosting) | low (append-only) |
| `web-frontend/modules/core/assets/scss/variables.scss` | `$text-font-stack` now `'Inter', 'IBM Plex Sans Arabic', sans-serif` | Arabic glyphs resolve to Plex per-glyph everywhere; RTL flips priority in arabase.scss | med |
| `web-frontend/modules/core/assets/scss/components/layout.scss` | Converted `.layout__col-1/2/2-1` physical `left/right/inset` to logical (`inset-inline*`) | App shell columns must lay out from the inline-start in RTL | med |
| `web-frontend/modules/core/layouts/app.vue` | Inline `:style` `left/right` → `insetInlineStart/insetInlineEnd` on col-2/col-3 and the two resize handles | Reactive column widths must follow inline direction | med |
| `web-frontend/modules/core/assets/scss/components/sidebar.scss` | Converted 13 physical props (border-right, padding/margin-left/right, right, radii) to logical equivalents | Sidebar is inline-start-anchored chrome; must mirror in RTL | med |
| `web-frontend/stylelint.config.mjs` | Added `stylelint-use-logical` plugin: `csstools/use-logical` = `warning` globally, `error` for `modules/arabase/**` | Turn the ~180-file physical-prop backlog into a visible worklist; hold new fork code strictly | low |
| `web-frontend/package.json` / `yarn.lock` | Added `stylelint-use-logical@^2.1.3` devDependency (lockfile: +5 lines only) | Support the rule above | low |

**Additive (not logged in the table):** `modules/arabase/assets/scss/arabase.scss`
(RTL font priority, Arabic line-height 1.6, directional icon-flip allowlist with a
`.rtl-no-flip` opt-out, `direction: ltr` on numeric/date/identifier grid cells,
`.force-ltr` helpers); the bundled font files + `LICENSE.md` under
`static/fonts/ibm-plex-sans-arabic/`; `modules/arabase/module.js` pushes arabase.scss
into `nuxt.options.css`.

### Deliberately NOT done here (needs the browser + native pass)
The **grid engine RTL** (horizontal virtualisation `scrollLeft` normalisation, frozen
column inline-start stickiness, per-field cell nav) is the deep, high-risk piece. Its
SCSS (`components/views/grid.scss`, ~911 lines) is coupled to JS that sets physical
`left` inline, so a blind conversion would break the grid in **both** directions. It is
left for the mandated visual-regression + native-review pass (`docs/RTL_REVIEW.md` §B);
the arabase layer already fixes cell text direction, which is the data-legibility part.

---

## Phase 0 — Re-freeze `FormView.mode` choices after premium strip (2026-07-03)

`makemigrations --check` failed because `FormView.mode`'s `choices` no longer matched
migration `0086_formview_mode` (which froze `[("form","form"),("survey","survey")]`).

**Root cause (a Phase 0 side-effect, *not* upstream drift):** the `"survey"` mode was
registered by the **premium** plugin
(`premium/backend/src/baserow_premium/apps.py` → `FormViewModeTypeSurvey`, `type="survey"`),
which we deleted in the premium/enterprise strip (commit `78b504bc6`). `FormView.mode`
uses registry-driven `choices=lazy(form_view_mode_registry.get_choices, list)()`; with
premium gone the OSS registry holds only `"form"`, so the resolved choices dropped to
`[("form","form")]` and diverged from the frozen migration. Pristine upstream 2.2.2 (with
premium installed) passes the check — this divergence is created by our fork.

**Fix:** a new no-op state migration re-freezing the choices to the OSS-only set. The
migration was **hand-written**, not taken verbatim from `manage.py makemigrations`:
under Django 5.2 the autogenerator serializes the `lazy(...)` proxy as the *string*
`"[('form', 'form')]"`, which never compares equal to the live proxy, so the generated
file regenerates itself on every run (`0210`, `0211`, …). Freezing `choices` as a real
Python list `[("form", "form")]` compares equal to the proxy and makes the check stable.

`choices`/`default` are Python-level only, so this touches no schema and no data —
`sqlmigrate database 0209` prints `-- (no-op)`; `makemigrations --check` is clean across
all apps.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `backend/src/baserow/contrib/database/migrations/0209_alter_formview_mode.py` | New no-op `AlterField` re-freezing `FormView.mode` choices to `[("form","form")]` | Match the OSS-only form-mode registry after the premium strip; unblock `makemigrations --check` in CI | low |

> Merge-risk note: only risk is a migration-number collision if a future upstream merge
> also introduces a `0209_*` leaf on `database`; resolve with a standard merge migration.
> Do **not** re-add the `baserow_premium` survey mode to satisfy the old frozen choices.

---

## Phase 1 WP4 — Top bar + panels/dropdowns to logical properties (2026-07-23)

Converted the header (top bar), context menus, dropdowns, select lists, filter/sort/
group-by panels, row-modal chrome, toasts, tooltip content, and the datepicker text
alignment from physical (`left`/`right`) to CSS logical properties so they follow
`dir="rtl"`. Deliberately **left physical**: JS-positioned bits (tooltip
`--tooltip-cursor-position-*` vars, `dropdown__items--fixed` fixed positioning,
`select__items-loading` symmetric centering hack) because their coordinates come from
`getBoundingClientRect` math, which is physical by definition.

Also added the `clientHandler.cannotDisableAllAuthProviders{Title,Description}` i18n
keys (en + ar): the code in `modules/core/plugins/clientHandler.js` references them but
their definitions lived in the **enterprise** locale files we stripped, causing intlify
fallback warnings on every SSR request. Parity gate remains green (3,484/3,484).

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `modules/core/assets/scss/components/header.scss` | full logical-props conversion (incl. loading keyframes, `header__info` float/border, search/buttons/right `margin-inline-start: auto`) | top bar RTL | low |
| `modules/core/assets/scss/components/context.scss` | `text-align: start`, offset/active/deactivated icons + loading spinner to inline props | context menus RTL (Teleported) | low |
| `modules/core/assets/scss/components/dropdown.scss` | selected/toggle icon margins + `--floating`/`--floating-left` anchors to inline props | dropdown menus RTL | low |
| `modules/core/assets/scss/components/select.scss` | item label/link paddings, active icon, indent, footer-create to inline props | select lists RTL | low |
| `modules/core/assets/scss/components/filters.scss` | 3 props to inline equivalents | filter panel RTL | low |
| `modules/core/assets/scss/components/sortings.scss` | 5 props to inline equivalents | sort panel RTL | low |
| `modules/core/assets/scss/components/group_bys.scss` | 5 props to inline equivalents | group-by panel RTL | low |
| `modules/core/assets/scss/components/row_modal.scss` | drag handle + hidden-separator icon margins | row modal RTL | low |
| `modules/core/assets/scss/components/toast.scss` | toast containers anchored `inset-inline-end` | toasts appear inline-end (left in RTL) | low |
| `modules/core/assets/scss/components/tooltip.scss` | expandable content `text-align: start` only | tooltip text RTL; JS positioning untouched | low |
| `modules/core/assets/scss/components/datepicker.scss` | `text-align: start` | datepicker RTL text alignment | low |
| `web-frontend/locales/en.json` + `locales/ar.json` | add `cannotDisableAllAuthProviders*` keys | keys orphaned by enterprise strip; kill SSR intlify warning spam | low |

---

## Phase 1 WP4/WP5 — RTL-aware context positioning (2026-07-23)

Bug (browser-reproduced): in RTL the view filter panel opened anchored by its **left**
edge (callers pass `horizontal: 'left'`, an LTR assumption), so when its content grew
(empty state 346px → one filter row 681px) it overflowed ~227px past the right edge of
the viewport. The stock `checkForEdges` flip only helps when the panel is already wide
at open time, not when it grows after opening.

Fix in `Context.vue#calculatePositions`: when `document.documentElement.dir === 'rtl'`,
mirror the caller's `horizontal` anchor (`left`↔`right`) **and negate
`horizontalOffset`** (a positive offset means "push towards physical +x" in the stock
code; mirrored it must push towards −x). Without the negation, contexts anchored to
edge-flush triggers (e.g. the sidebar workspace selector, offset 16) compute
`css.right = -16`, trip the "doesn't fit" guard at the top of `updatePosition`, and
silently never open. `checkForEdges` still flips on real overflow after the mirror.
One central change mirrors every context/panel/dropdown in the app.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/modules/core/components/Context.vue` | Mirror `horizontal` + negate `horizontalOffset` in `calculatePositions` when dir=rtl | RTL panels must anchor inline-start and grow towards content; fixes off-screen filter panel + never-opening workspace selector | medium — upstream touches this method occasionally; re-apply block is 12 lines at the top of `calculatePositions` |

---

## Phase 1 WP4 — over-constrained absolute boxes in RTL (2026-07-27)

One CSS bug class produced three separate RTL-only failures. A box with a
definite width plus **both** `left` and `right` is over-constrained, so CSS drops
one of them — `right` under LTR, but **`left` under RTL**. Every instance was
invisible in English and broken in Arabic.

`.dropdown__items` sets both inline insets to `0` (the base rule lets a nested
menu stretch to its trigger). The `--fixed` variant is `position: fixed` and
receives a physical inline `left` from JS with no matching `right`, so cancelling
only `inset-inline-end` left a stray `right: 0` alive under RTL and stretched the
"add field" menu across the whole viewport (measured 1892px wide). Releasing both
inline sides fixes it (measured 351px, fully on screen).

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `modules/core/assets/scss/components/dropdown.scss` | `.dropdown__items--fixed`: `inset-inline-end: auto` → `inset-inline: auto` | Release *both* inline insets; a JS-supplied physical `left` must not combine with the base `right: 0` | low — 1 line, adjacent to the existing `--floating` patch |

---

## Templates — tolerate types this build does not ship (2026-07-27)

Bug (reproduced): the template picker was empty. `/api/templates/` returned `[]`
and `core_template` had 0 rows, because **every bundled template failed to
install**. Stripping `premium/` and `enterprise/` leaves several registries
empty, and the import path treated a missing type as fatal:

- `view_type_registry` has only grid/gallery/form — `timeline`, `kanban` and
  `calendar` are proprietary, and 118 of the 155 templates use at least one.
- `field_rules` is missing `date_dependency`.
- `user_source_type_registry` is empty (`local_baserow` lived in enterprise),
  which aborted the whole `sync_templates` run rather than one template.

Verified before changing anything: of the 816 tables across all templates,
**none** would be left without a view, since every table has a grid/gallery/form
view. Skipping a proprietary view therefore degrades cleanly — the table and its
data import, only that one view is absent.

No proprietary code was copied or reimplemented to fix this.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `backend/src/baserow/contrib/database/application_types.py` | `_import_table_views`: catch `ViewTypeDoesNotExist`, log and skip the view instead of aborting the application import | An export made where kanban/calendar/timeline exist must still import here | medium — small block inside an upstream loop |
| `backend/src/baserow/contrib/database/application_types.py` | `_import_field_rules`: catch `InstanceTypeDoesNotExist`, log and skip the rule (reads `type` before `import_rule` pops it) | Same, for the proprietary `date_dependency` rule | low |
| `backend/src/baserow/core/handler.py` | `sync_templates`: wrap the per-template `_sync_template` call in try/except, collect failures, log a summary at the end | One unimportable template must not abort the sync of the other 154; each template already has its own atomic block so the rollback is clean | medium — upstream occasionally edits this loop |
| `backend/src/baserow/contrib/builder/application_types.py` | `import_user_sources_serialized`: catch `InstanceTypeDoesNotExist`, log and skip the user source | `user_source_type_registry` is empty (`local_baserow` was enterprise); without this the builder app and its databases are lost | low |
| `backend/src/baserow/contrib/builder/pages/handler.py` | `import_elements`: drop elements whose type is unregistered, plus their descendants, before the priority sort | The sort key itself resolves every type through the registry, so an unknown type raised *before* the import loop. Descendants are removed to a fixed point because parents are not guaranteed to be serialized first | medium |
| `backend/src/baserow/contrib/builder/pages/handler.py` | `import_workflow_actions`: skip actions whose `element_id` is absent from `id_mapping` | An action bound to a skipped element raised `KeyError` and aborted the page | low |

Chain of missing types encountered, in the order they surfaced: `view_type`
(timeline/kanban/calendar) → `field_rules` (date_dependency) → `user_source`
(local_baserow) → `element_type` (auth_form, input_file) → workflow actions
orphaned by the skipped element. Templates went 0 → 24 → 123 → 155 as each was
handled.
