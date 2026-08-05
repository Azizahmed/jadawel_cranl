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
| `backend/src/jadawel/config/settings/base.py` | Force `BASEROW_OSS_ONLY = True` and `BASEROW_BUILT_IN_PLUGINS = []`; removed `baserow_premium_*`/`baserow_enterprise_*` table names from the CACHALOT lists; added a default for `BASEROW_ENTERPRISE_USER_SOURCE_COUNTING_TASK_INTERVAL_MINUTES` | Stop loading the deleted plugins; keep cache config referencing only existing tables; provide the setting core still reads (see below) | high |
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
- `backend/src/jadawel/core/generative_ai/generative_ai_model_types.py` and
  `.../registries.py` import `baserow_premium.fields.ai_file.AIFile` **only under
  `if TYPE_CHECKING:`**. These are never evaluated at runtime and copy no proprietary
  code (name reference only). Left untouched to minimise core-file churn; will be
  revisited if/when we run `mypy` in CI. **Do not** re-add the `baserow_premium` package.
- `.github/dependabot.yml`, `backend/src/jadawel/test_utils/pytest_conftest.py`,
  `backend/src/jadawel/contrib/database/mcp/services.py`: comment-only mentions. Harmless.

## Phase 0 — Register the `arabase` app / module (2026-07-03)

Additive scaffolding lives in `backend/src/arabase/` and
`web-frontend/modules/arabase/` (not logged individually — they're our files). The
two core files below are edited only to *register* that additive code:

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `backend/src/jadawel/config/settings/base.py` | Appended `"arabase"` to `INSTALLED_APPS` | Load our Django app | med |
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
| `backend/src/jadawel/config/settings/base.py` | `LANGUAGE_CODE = os.getenv("BASEROW_DEFAULT_LOCALE", "ar")`; prepended `("ar", "Arabic")` to `LANGUAGES` | Make Arabic selectable + the env-configurable default; new-user creation reads `settings.LANGUAGE_CODE` live (see `core.user.handler`) so `BASEROW_DEFAULT_LOCALE` is honoured per deploy | med |
| `backend/src/jadawel/core/migrations/0115_jadawel_add_arabic_language.py` | **New** AlterField migration for `userprofile.language` (adds `ar` to choices, default `ar`) | Django requires the migration to live in the model's app (`core`); it's a no-op choices/default change, no data impact | low |
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
| `backend/src/jadawel/contrib/database/migrations/0209_alter_formview_mode.py` | New no-op `AlterField` re-freezing `FormView.mode` choices to `[("form","form")]` | Match the OSS-only form-mode registry after the premium strip; unblock `makemigrations --check` in CI | low |

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
| `backend/src/jadawel/contrib/database/application_types.py` | `_import_table_views`: catch `ViewTypeDoesNotExist`, log and skip the view instead of aborting the application import | An export made where kanban/calendar/timeline exist must still import here | medium — small block inside an upstream loop |
| `backend/src/jadawel/contrib/database/application_types.py` | `_import_field_rules`: catch `InstanceTypeDoesNotExist`, log and skip the rule (reads `type` before `import_rule` pops it) | Same, for the proprietary `date_dependency` rule | low |
| `backend/src/jadawel/core/handler.py` | `sync_templates`: wrap the per-template `_sync_template` call in try/except, collect failures, log a summary at the end | One unimportable template must not abort the sync of the other 154; each template already has its own atomic block so the rollback is clean | medium — upstream occasionally edits this loop |
| `backend/src/jadawel/contrib/builder/application_types.py` | `import_user_sources_serialized`: catch `InstanceTypeDoesNotExist`, log and skip the user source | `user_source_type_registry` is empty (`local_baserow` was enterprise); without this the builder app and its databases are lost | low |
| `backend/src/jadawel/contrib/builder/pages/handler.py` | `import_elements`: drop elements whose type is unregistered, plus their descendants, before the priority sort | The sort key itself resolves every type through the registry, so an unknown type raised *before* the import loop. Descendants are removed to a fixed point because parents are not guaranteed to be serialized first | medium |
| `backend/src/jadawel/contrib/builder/pages/handler.py` | `import_workflow_actions`: skip actions whose `element_id` is absent from `id_mapping` | An action bound to a skipped element raised `KeyError` and aborted the page | low |

Chain of missing types encountered, in the order they surfaced: `view_type`
(timeline/kanban/calendar) → `field_rules` (date_dependency) → `user_source`
(local_baserow) → `element_type` (auth_form, input_file) → workflow actions
orphaned by the skipped element. Templates went 0 → 24 → 123 → 155 as each was
handled.

---

## Jadawel theme — sage/emerald palette (2026-07-28)

Retones the interface from Baserow's blue to a calm sage/emerald, and adds a
faint grid behind the working area.

The important structural change is in `colors.scss`. The `$colors` map is
**user data** — its keys are what get written to the database when someone
picks a colour for a select option or a view — but it was reading the semantic
`$color-*` tokens. Repointing `$color-primary-*` at the brand would therefore
have silently repainted colours people already chose, and a select option
labelled "blue" would have come back green. The map now reads raw `$palette-*`
values only, with the greys frozen to their pre-sage hex. Verified: all 42
entries resolve byte-identically before and after.

34 component stylesheets referenced `$palette-blue-*` directly for chrome
(buttons, inputs, checkboxes, tabs, toasts, focus rings) rather than going
through `$color-primary-*`, so repointing the semantic token alone left the
primary button blue. All 78 occurrences were moved to `$palette-brand-*`.

`$palette-brand-500` is pinned at `#278053` rather than a lighter, more
saturated green: -500 is the step that carries white text, and the lighter
value measured 3.93:1 against white, failing WCAG AA. `#278053` measures
4.89:1. Verified in-browser after the change.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/modules/core/assets/scss/colors.scss` | Add `$palette-brand-*`; tint neutrals sage; repoint `$color-primary-*` at brand; decouple `$colors` map from semantic tokens | Brand retone without touching stored user colours | medium — upstream edits this file |
| `web-frontend/modules/core/assets/scss/base.scss` | Faint brand-derived grid on `body`, 32px, fixed attachment | Texture behind the transparent `.layout__col-2-scroll` | low |
| 34 × `web-frontend/modules/core/assets/scss/**` | `$palette-blue-*` → `$palette-brand-*` (78 occurrences) | Chrome bypassed the semantic token | medium — mechanical, re-runnable |
| `backend/templates/{all-fields,custom-code-demos,formulas,password-reset}.json` | Category `"Baserow"` → `"Examples"` | A template category named after the upstream project was visible in the picker | low |

---

## Arabic and English only (2026-07-28)

Drops every language except Arabic and English across both tiers: 113 frontend
locale JSON files, 53 backend `locale/<lang>` directories with their .po/.mo
catalogues, and the eight surplus entries in each of the two language lists.

Three things this touched that are easy to miss:

- `UserProfile.language` takes `choices` from `settings.LANGUAGES`, so trimming
  the list is a model change and needs a migration, not just a settings edit.
- Dropping a language does not touch rows that already hold it. A user sitting
  on `fr` would keep requesting a locale the frontend can no longer resolve, so
  the migration also normalises those rows to the default. It is deliberately
  one-way — the original values are overwritten, and reversing restores the
  choices but not the users' previous languages.
- `modules/builder/plugin.js` imported seven locale JSON files that nothing in
  the file used. Dead as they were, they still broke the build the moment the
  files were deleted. Two further modules referenced deleted locales from inside
  commented-out legacy blocks; those were inert but cleaned for consistency.

Backend Arabic was already absent upstream (there is no `locale/ar` catalogue),
so server-side strings such as e-mails fall back to the English msgid. That is
pre-existing, not a regression from this change.

Verified: `makemigrations --check` reports no drift; `PATCH /api/user/account/`
rejects `fr` with "Only the following language keys are valid: ar,en" and
accepts both `ar` and `en`; the login language switcher offers exactly العربية
and English; locale parity stays 3469/3469 with strict mode clean.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/config/locales.js` | Keep `ar` + `en` | Single source of truth for the frontend language list | low |
| `backend/src/jadawel/config/settings/base.py` | `LANGUAGES` → `ar`, `en` | Drives `UserProfile.language` choices and API validation | low |
| `backend/src/jadawel/core/migrations/0116_jadawel_arabic_english_only.py` | New: alter choices + normalise stranded users | Model change; orphaned rows would request an unresolvable locale | low |
| `web-frontend/modules/builder/plugin.js` | Remove 7 unused locale imports | Dead imports that broke the build once the files were gone | low |
| 113 × `web-frontend/**/locales/*.json`, 53 × `backend/**/locale/<lang>/` | Deleted | Unshipped languages | low |

---

## Sidebar simplification (2026-07-28)

The panel was hard to read for three reasons that compound: you could not tell
which row was selected, table rows carried no glyph, and four one-item sections
each paid for a heading, a `+` and a separator.

**Selection was invisible.** `.tree__item.active`, `.tree__action:hover` and
`.tree__sub:hover` all resolved to the same `rgba($palette-neutral-1300, 0.04)`,
so the open table and the row under the cursor were the same colour. Selection
now carries the brand tint, brand text, a brand icon and a 3px marker bar;
hover keeps the neutral wash. Where a row is both, `.active` wins on source
order. These two states must never resolve to the same value again.

**Tables had no icon.** A database with a dozen tables was a dozen identical
lines of text. Every row now shows `iconoir-table` — the same glyph the search
results already use for a table — except synced tables, which keep the sync
icon rather than showing two.

**`tree.scss` was written in physical directions** while the rest of the
codebase uses logical ones: the sub-item indent, the connector line, the row
menu, the counter and the loading spinners were all pinned to the LTR side and
did not mirror in Arabic. Converted; verified that toggling `dir` produces an
exact mirror, so LTR geometry is byte-for-byte what upstream shipped.

**Workspace utilities became an icon row.** Notifications, members, invite and
trash were five labelled rows costing ~170px above the fold; they are now 30px
icon buttons under the workspace picker. The whole block is 92px. The sidebar's
own search box went with them — global search stays reachable as the first icon,
and the Ctrl/⌘ K hint the box used to show moved into its tooltip. Every icon
carries a tooltip and an `aria-label`; the member count moved into the members
tooltip rather than being dropped.

**The four application sections became one list.** Applications now sort on
`order` alone, which is correct because `Application.order` is allocated per
workspace — the grouped rendering was re-sorting one workspace-wide sequence
inside each type. A side effect is that a database and a dashboard can now be
dragged past each other, which the backend already accepted. The per-type `+`
buttons are gone; the "add new" menu at the foot of the panel already offers
every creatable type plus templates and import.

Not done, deliberately: the collapse control stays in `SidebarFoot`. Moving it
into the utility row would have removed the expand affordance when the sidebar
is collapsed, because that row is inside the block hidden by `v-show`.

Verified in the running app in Arabic: five utility buttons with correct labels,
no search box, zero headings, zero separators, active `rgb(240,247,243)` against
hover `rgba(8,11,7,0.04)`, marker and row menu on the correct inline edges in
both directions, stylelint clean on both stylesheets, locale parity 3470/3470.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/modules/core/assets/scss/components/tree.scss` | Distinct active state + `%tree-active-marker`; `.tree__sub-icon`; physical → logical properties | Active was indistinguishable from hover; RTL did not mirror | medium — upstream edits this file |
| `web-frontend/modules/core/assets/scss/components/sidebar.scss` | Replace `.sidebar__search*` with `.sidebar__utilities` / `.sidebar__utility` / badge override | Search box removed, utilities became icons | medium |
| `web-frontend/modules/core/components/sidebar/SidebarMenu.vue` | Utilities as icon buttons; tooltips + aria-labels; Ctrl/⌘ K in the search tooltip | ~140px reclaimed above the fold | medium |
| `web-frontend/modules/core/components/sidebar/SidebarSearch.vue` | Deleted | Its only caller was `SidebarMenu` | low |
| `web-frontend/modules/core/components/sidebar/SidebarWithWorkspace.vue` | One flat application list; drop headings, per-type `+`, separators | Chrome outweighed content | medium |
| `web-frontend/modules/database/components/sidebar/SidebarItem.vue` | Table glyph on every row | Rows were undifferentiated text | low |
| `web-frontend/modules/core/locales/{en,ar}.json` | Add `sidebar.searchTooltip` | Keeps the keyboard shortcut discoverable without the box | low |

---

## Workspace utilities move to the content header (2026-07-28)

Follow-up to the sidebar work above. The utility icons were still inside the
sidebar, which put them top-right in Arabic; they belong in the top-left corner
of the content area, next to where the eye already goes for search. And with a
magnifier in both places the app showed two search icons that did different
things.

`AppUtilities.vue` now renders notifications, members, invite and trash, pinned
to the top inline-end corner of `.layout__col-2`. It is mounted once by the app
layout rather than by each header, because there are five separate header
components — table, dashboard, automation, builder, workspace home — and the
group has to appear on all of them. The band it occupies is reserved by the
headers themselves via `padding-inline-end: $app-utilities-band`; each is a flex
row whose end-side content is pushed over with `margin-inline-start: auto`, so a
padding on the container is sufficient and no header needs to know the group
exists. The workspace home page has a 74px header rather than the shared 51px
one, so a `:has()` rule matches the group's height to it.

There is deliberately no search icon in the group. The two searches were never
the same feature: the sidebar box was the global Ctrl/⌘ K search, while the
magnifier in the view header is `ViewSearch`, which searches rows in the table
you are looking at. `ViewSearch` has no keyboard shortcut — the magnifier is its
only affordance — whereas global search keeps Ctrl/⌘ K, so dropping the global
icon is the one that loses nothing outright.

The cost, stated plainly: global search now has no visible affordance anywhere.
On a table page there is exactly one magnifier and it searches that table; on
the workspace home and dashboards there is none. If that proves wrong, the fix
is to put the global-search icon back into the group and remove `ViewSearch`
from the view header instead.

Verified in the running app: on a table page the group sits at 0–142px with the
view search starting at 152px and exactly one magnifier on the page; on the
workspace home the group matches the 74px header and centres on it, with the
header's own controls starting flush at 142px. Toggling `dir` moves the group
from the far left to the far right, which is the conventional corner in English.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/modules/core/components/AppUtilities.vue` | New: the four utility buttons | Must appear on every page, not per header | low |
| `web-frontend/modules/core/assets/scss/components/app_utilities.scss` | New: pinned band, button and badge styles | — | low |
| `web-frontend/modules/core/layouts/app.vue` | Mount `AppUtilities` in `layout__col-2`; drop the dead search emit | Single mount point for every page | medium |
| `web-frontend/modules/core/assets/scss/components/layout.scss` | `.layout__col-2-1` reserves the band | Five headers share this class | medium |
| `web-frontend/modules/core/assets/scss/components/dashboard.scss` | `.dashboard__header` reserves the band | Workspace home has its own taller header | low |
| `web-frontend/modules/core/assets/scss/variables.scss` | Add `$app-utilities-band` | Consumed by both header stylesheets | low |
| `web-frontend/modules/core/components/sidebar/{SidebarMenu,Sidebar}.vue` | Remove the icon row and the search emit chain | Moved to the content header | medium |
| `web-frontend/modules/core/locales/{en,ar}.json` | Remove `sidebar.searchTooltip` | Its only consumer is gone | low |

## Phase — Arabic terminology pass + hide unfinished app types (2026-07-29)

**Context:** A product-language pass over the Arabic UI, plus temporarily removing two
application types from the creation flow. Six of the seven changes are pure locale-value
edits (no keys added or removed — parity stays 3469/3469). The seventh, the default view
name, could not be fixed in the frontend at all: `TableHandler.create_table` names the
view with `_("Grid")` inside `translation.override(user.profile.language)`, so the name is
**stored as literal text** at creation time and rendered as data thereafter.

Upstream ships no `ar` backend catalogue (noted in the Phase 0 language strip above), so
that gettext call had nothing to translate to and every Arabic user's tables were created
with a view literally named "Grid". This adds the catalogue — the first Arabic backend
translations in the fork — and a data migration to rewrite the rows created before it
existed. Adding the catalogue alone would have fixed only newly created tables.

The `.mo` is committed alongside the `.po` because nothing in the build runs
`compilemessages` — the same convention upstream already follows for `en`.

**Application types:** `builder` ("تطبيق") and `automation` ("أتمتة") are hidden from the
"add new" context via the existing `canBeCreated()` hook rather than by deleting the
registrations. Existing applications of both kinds keep loading, routing and rendering
normally; only the creation entry point is gone. Both surfaces that offer creation
(workspace home and the sidebar) share `CreateApplicationContext`, so one hook covers both.
Reverting is a one-line change per file.

**Terminology:** "لوحة التحكم" → "لوحة البيانات" is applied to the `applicationType.*` keys
only — the dashboard *application type*. `sidebar.dashboard`, `dashboard.title` and
`adminType.dashboard` still read "لوحة التحكم" because they name the workspace home and the
admin area, which are different things that happened to share a translation.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/modules/builder/applicationTypes.js` | Add `canBeCreated() { return false }` | Hide "تطبيق" from the add-new context without unregistering the type | low |
| `web-frontend/modules/automation/applicationTypes.js` | Add `canBeCreated() { return false }` | Same, for "أتمتة" | low |
| `web-frontend/locales/ar.json` | `applicationType.dashboard{,s,DefaultName}` → "لوحة البيانات"; `common.summarize` → "تحليل"; `viewType.grid` → "جدول" | Product terminology; `common.summarize` is the grid footer aggregation row | low |
| `web-frontend/modules/core/locales/ar.json` | `createApplicationContext.fromTemplate` → "القوالب الجاهزة" | Reads as a destination, not a preposition | low |
| `web-frontend/modules/database/locales/ar.json` | `databaseDashboardResourceLinks.title` → "API"; `viewGroupBy.groupBy` + `viewGroupByContext.{groupBy,noGroupByTitle}` → "مجموعة" | "API" is the term users actually search for; "تجميع" collided with the rollup field type | low |
| `backend/src/jadawel/contrib/database/locale/ar/LC_MESSAGES/django.{po,mo}` | New: first Arabic backend catalogue; translates `"Grid"` → "جدول" | The view name is picked in the backend under `translation.override`; untranslated entries still fall back to English | low |
| `backend/src/jadawel/contrib/database/migrations/0210_jadawel_rename_default_grid_views.py` | New: rename views named exactly `"Grid"` → `"جدول"`, reversible | The catalogue fixes new tables only; existing rows hold the untranslated literal | low |

### Known limitation
`fieldType.rollup` is still "تجميع". It is a different concept (the rollup field type) that
upstream happens to translate with the same Arabic word as group-by; renaming it was out of
scope for this pass and needs its own term.

## Phase — Workspace home: data-bearing database list (2026-07-29)

**Context:** The workspace home page led with two static blocks — "suggested templates"
(two cards hardcoded in `workspace.vue`) and "resources" (one plugin-provided API link) —
and only then showed the user's own applications, each labelled with nothing but its type
and creation date. This moves the application list to the top, adds real counters to it,
and puts per-database actions on the card.

**The reorder needed a stylesheet change, not just a template change.** `.dashboard__main`
is a flex column and `.dashboard__extras` carried `order: 1` / `order: 0` (wide screens),
so DOM order was being silently overridden — upstream used `order` to place the block
above the list on desktop while keeping it below on mobile. Reordering the template alone
would have had no effect above 1280px. Both `order` declarations are removed so the markup
is the single source of truth.

**Counters are a separate endpoint, not extra fields on the application payload.** That
payload is fetched on every route because the sidebar depends on it; row counting is the
expensive part, and folding it in would make every page load pay for a number only the home
page renders. `GET /api/arabase/workspace/<id>/database-stats/` is fetched client-side after
first paint, and failures are swallowed — the cards are fully usable without the numbers.

**Row counts are counted live.** `TableUsage.row_count` exists but is written by the
periodic `run_calculate_storage` task, which is gated behind the instance setting
`track_workspace_usage` — off by default, so the table was empty for all 845 tables on the
dev instance, and even when enabled it lags by up to 30 minutes. Each Baserow table is a
real Postgres table, so exact counts mean one `COUNT(*)` each. Through the ORM that costs a
dynamic model build per table (measured: ~370ms for 14 tables); as a single `UNION ALL` of
plain counts it is ~4ms for the same 14. The endpoint does the latter, caps the fan-out at
200 tables, and returns `rows_exact: false` with a null count past that rather than a
partial total.

**Export is the only genuinely new action.** Rename, duplicate, snapshots, trash and delete
were already in the `⋮` menu of the dashboard card — that menu has always rendered
`getApplicationContextComponent(application)`, the same component the sidebar uses.
`ExportWorkspaceModal` gained an optional `application` prop; when set it preselects that
one application, replaces the application picker with an empty slot so the scope cannot be
widened, and retitles. Passing nothing keeps the workspace-wide behaviour the workspace
context menu relies on.

The `$tc` helper does not exist in this build of vue-i18n. Pluralised keys are called as
`$t(key, { count })`, which is what the rest of the app already does.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/modules/core/pages/workspace.vue` | Move `.dashboard__extras` after `.dashboard__wrapper`; fetch and pass `databaseStats` | Put the user's data first; feed the cards | med |
| `web-frontend/modules/core/assets/scss/components/dashboard.scss` | Drop both `order` declarations on `.dashboard__extras` | They overrode DOM order and made the template reorder a no-op on desktop | low |
| `web-frontend/modules/core/components/dashboard/DashboardApplication.vue` | New `stats` prop; render table/column/row counts | The counters | low |
| `web-frontend/modules/arabase/services/databaseStats.js` | New: client for the stats endpoint | — | low |
| `web-frontend/modules/core/components/export/ExportWorkspaceModal.vue` | Optional `application` prop: scoped title, preselection, picker suppressed | Export one database from its own menu | med |
| `web-frontend/modules/core/components/export/ExportWorkspaceForm.vue` | Optional `initialApplicationIds` prop | Null keeps the select-all default | low |
| `web-frontend/modules/database/components/application/ApplicationContext.vue` | Add the export item + modal inside `#additional-context-items` | Core renders no default slot, so anything outside a named slot is dropped | low |
| `web-frontend/modules/core/locales/{en,ar}.json` | `dashboardApplication.{table,field,row}Count`, `sidebarApplication.exportDatabase`, `exportWorkspaceModal.application{Title,Description}` | — | low |
| `backend/src/arabase/api/{database_stats,views,urls}.py`, `arabase/plugins.py` | New: the stats endpoint, mounted under `/api/arabase/` via `plugin_registry` | Additive; no core url file touched | low |
| `backend/src/arabase/apps.py` | Register `ArabasePlugin` in `ready()` | First use of the registry hook the file was written for | low |

### Known limitations
- Arabic plural forms use the repo's existing three-form convention, so counts above ten
  read "94 أعمدة" where strict grammar wants "94 عمودًا". The grid footer already says
  "200 صفوف"; fixing it properly means adding Arabic CLDR plural rules to `i18n.config.ts`
  and is a separate change.
- Counters cover databases only. Other application types render as before.

---

## Workspace home: overview charts, template cards, resources (2026-07-29)

The section under the application list was three problems at once. The two
"suggested templates" were a hardcoded array of English slugs in `workspace.vue`,
so an Arabic-first product advertised English templates and never surfaced the
Arabic ones this fork ships. The "view more" tile rendered as an empty white box
that reads as a failed image load. And both panels were stretched to
`calc(100% - 33px)` so each matched its neighbour's height rather than its own
contents — the resources block was 190px of white around a single link.

**Overview strip.** Four stat tiles plus two charts, above the templates, because
it is the only part of that area that reflects the user's own data. Rows, tables
and members are separate tiles rather than one chart: they are 279, 14 and 1, and
forcing measures of different magnitude onto shared axes — or worse two y-axes —
is the standard way a chart misleads.

`DashboardBarChart` plots rows per database, single hue, no legend (one series;
the row labels carry identity), bars scaled against the largest value rather than
the total so a small database is still visible. `DashboardAreaChart` plots rows
added per day with a crosshair, tooltip, keyboard arrow-key traversal, and a
visually-hidden table — the bar chart needs no table because every value is
already text beside its bar. Both are hand-rolled SVG/CSS: no chart library, so
no runtime CDN fetch.

**The time axis deliberately does not mirror.** It reads left-to-right in Arabic
too. Mirroring a time series is a known source of misreading and Arabic-language
dashboards overwhelmingly keep time flowing this way.

**Backend.** `/arabase/workspace/{id}/activity/` aggregates `created_on` across
every user table, capped and reported the same way the counters are. The
alternatives were all worse: `TableUsage` has no history and is off by default,
`RowHistory` records only edits and is pruned, and the audit log is an enterprise
feature this fork must not read.

Two bugs found while verifying, both of which looked fine on screen:

- `$i18n.locale` is a **ref** inside `<script setup>` and a **string** through the
  options API. Indexing the slug map with the ref missed silently and fell back
  to English, while `$i18n.t` still returned Arabic — so the cards rendered
  Arabic names that opened the English templates. Fixed with `unref`.
- Arabic number agreement. vue-i18n applies the English plural rule to every
  locale, so 200 rows read `200 صفوف` and 24 columns `24 أعمدة`; Arabic takes the
  singular above ten. Supplying a custom rule does not work — this build of
  @nuxtjs/i18n honours neither `pluralizationRules` nor `pluralRules` from
  `i18n.config.ts`, and both were tried; the runtime kept returning the dual form
  for every count above one. The category is now resolved with `Intl.PluralRules`
  (CLDR is in the browser) and used to pick a plain message key. Counts render
  `200 صف`, `24 عمودًا`, `13 صفًا`, `6 أعمدة`.

Only `dashboardApplication`'s three count messages were converted. The other 24
Arabic plural messages still use vue-i18n's pipe syntax and the English rule;
converting one is a local edit to that message plus a `counted()` call, with no
further code change.

Verified in the running app in both languages: tiles 3/14/279/1, bars at 100/33/6.5
percent with the rounded end on the data side in both directions, hover tooltip
and crosshair, activity path drawn from the live endpoint, Arabic cards opening
`arabic-project-management`, English cards opening `project-management`, resources
row 38px instead of 190px. Backend 8/8 pytest, frontend 9/9 vitest, stylelint
clean, locale parity 3501/3501.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `backend/src/arabase/api/activity.py` | New: rows-created-per-day aggregation | No non-enterprise source for row history | low |
| `backend/src/arabase/api/{views,urls}.py` | New `WorkspaceActivityView` | — | low |
| `backend/tests/arabase/test_workspace_activity.py` | New: 8 tests | Density, trashed rows, window, clamping, permissions | low |
| `web-frontend/modules/arabase/services/workspaceActivity.js` | New service | — | low |
| `web-frontend/modules/core/components/dashboard/Dashboard{Overview,BarChart,AreaChart,TemplateCard}.vue` | New | Overview strip and redesigned cards | low |
| `web-frontend/modules/core/pages/workspace.vue` | Locale-aware featured templates; mount overview; fetch activity | Hardcoded English slugs; `unref` bug | medium |
| `web-frontend/modules/core/assets/scss/components/dashboard.scss` | Chart, tile and card styles; unstretch both panels | Panels were sized to each other, not their contents | medium |
| `web-frontend/modules/core/utils/plural.js` | New: CLDR category via `Intl.PluralRules` | vue-i18n's rule is English-only | low |
| `web-frontend/modules/core/components/dashboard/DashboardApplication.vue` | Resolve counts through `pluralKeys` | Arabic number agreement | low |
| `web-frontend/scripts/check-locale-parity.mjs` | Allow `two`/`few`/`many` without an English twin | Categories Arabic needs and English lacks | low |
| `web-frontend/modules/core/locales/{en,ar}.json` | Overview/chart/template strings; count messages as per-category keys | — | low |

## Grid keyboard navigation follows field order in RTL (2026-07-29)

Arrow keys name a physical direction; grid navigation moves along the field
order, which is an inline axis. `ArrowLeft` was mapped straight onto "previous
field", which is only true in LTR — in an Arabic grid the previous field sits to
the *right* of the selected cell, so every horizontal arrow moved the selection
away from the key the user pressed. Reported as: pressing left goes right and
right goes left.

The swap happens once, where the key becomes a direction, so both `Tab` and the
vertical arrows are untouched: `Tab` already means "next in reading order",
which *is* the field order, and rows stack top to bottom in both directions.

The direction is read from `.grid-view`, not from the cell. Number, date, url,
email and phone cells are pinned to `direction: ltr` in `arabase.scss` so their
digits stay readable; reading the cell would have left the arrows inverted in
exactly those columns and correct everywhere else.

Shift+arrow multi-select had the same inversion, plus a second bug behind it:
its scroll-into-view rectangle is accumulated in field order — an inline
position — but `scrollToElementRect` measures from the container's left edge.
The two coincide only in LTR. It now normalises `scrollLeft` (browsers report it
negative in RTL) and mirrors the finished rectangle across the viewport.

Verified in the running app in Arabic: selection steps 523 → 323 → 91 px on
`ArrowLeft`, back the same way on `ArrowRight`, crosses into the frozen primary
column at the far right, `Tab` still moves toward inline-end, `ArrowDown` holds
its column. Shift+arrow extends field 1 → 5 and scrolls to `scrollLeft: -671`,
landing the last field 20px inside the viewport. The same sequence with `dir`
toggled to `ltr` produces the exact mirror (`+671`), so LTR is unchanged.
7/7 new vitest; the 4 pre-existing snapshot failures in
`test/unit/database/components/view/grid` were confirmed identical with the
change stashed.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/modules/database/utils/gridViewKeyboard.js` | New: `toInlineArrowKey`, `mirrorInlineRect` | Pure helpers, testable without a grid | low |
| `web-frontend/test/unit/database/utils/gridViewKeyboard.spec.js` | New: 7 tests | Swap, vertical/Tab pass-through, rect mirroring | low |
| `web-frontend/modules/database/mixins/gridField.js` | Swap horizontal arrows before mapping to a direction | Arrows were inverted in RTL | low |
| `web-frontend/modules/database/components/view/grid/GridView.vue` | Same swap for shift+arrow; inline-normalised scroll rect | Multi-select inverted; scroll rect was inline, consumed as physical | medium |

## Workspace home: two applications per row (2026-07-29)

The application list was a single flex column, so on a wide screen each row was
a ~1900px band holding a 40px icon, a short name and one line of counters. The
list is now a two-column grid.

`minmax(0, 1fr)` rather than `1fr` for the tracks: `1fr` is `minmax(auto, 1fr)`,
and `auto` refuses to shrink below the widest counter line, which would push the
columns out of the container instead of letting the existing text ellipsis do
its job.

Grid rows are as tall as their tallest cell, so each `li` is a flex column and
the application block takes up the slack. Without that the two hairline
separators in a row sit at different heights as soon as one application's name
wraps and its neighbour's does not.

Below `$dashboard-applications-breakpoint` it falls back to one column. The
number is measured, not guessed: the longest counter line in the seeded
workspace ("قاعدة بيانات • 10 جداول • 94 عمودًا • 66 صفًا • تاريخ الإنشاء منذ
ساعات") needs 362px of text plus 76px of icon, gap and padding, so two columns
and the 32px gap want ~910px of list, and the sidebar plus the utility band take
a further ~318px off the viewport. At 1200px the counters were clipping and the
creation date was the first thing lost; 1280px clears it.

Nothing was needed for RTL — grid flow follows the writing direction on its own.
Verified at 1400px: first application in the right column in Arabic, in the left
column with `dir` toggled to `ltr`, separators aligned per row, no clipped
counter lines; at 1279px a single 961px column.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/modules/core/assets/scss/components/dashboard.scss` | `.dashboard__applications` flex column → two-column grid; separator pinned to the bottom of the cell | Full-width rows wasted the screen | low |
| `web-frontend/modules/core/assets/scss/variables.scss` | New `$dashboard-applications-breakpoint` | Single column below the width where counters clip | low |

## Production hardening: security headers, source maps, inline CSS (2026-07-29)

Audit of the live deployment before go-live. Full findings, including the items
that need an admin-panel or Coolify change, are in
[docs/PRODUCTION_HARDENING.md](docs/PRODUCTION_HARDENING.md).

**The stylesheet was being inlined into every SSR response.** Nuxt does this by
default, which is right for a small stylesheet and wrong for a 1,870,576-byte
one: ~188 KB gzipped of uncacheable CSS on every document request, re-parsed
before first paint. Production was serving `entry.tn0RQdqM.css` at 0 bytes,
which is the tell. A verification build with `features.inlineStyles: false`
emits it as a real external file under `/_nuxt/`, where the existing
`immutable` cache header applies.

**Source maps were public.** `/_nuxt/DtultdTW.js.map` returned 200 with 4.2 MB
of original source. `sourcemap.client: 'hidden'` removes the pointer from all 81
chunks — verified 81 maps still emitted, 0 references remaining — but the files
stay on disk and stay fetchable, so Caddy also 404s `/_nuxt/*.map`. Scoped to
build output, so a user's own uploaded `.map` file still downloads.

**No security headers were sent at all.** HSTS, nosniff, Referrer-Policy and
Permissions-Policy added in the Caddyfile rather than at the edge, so they
survive a change of proxy. No global CSP: Nuxt serves inline bootstrap scripts,
so a guessed policy breaks the app silently. HSTS is a one-way door and is
called out as such in the doc.

**Clickjacking protection is scoped.** `frame-ancestors 'self'` on the signed-in
app, nothing on `/form/*` and `/public/*` so shared links stay embeddable.
`'self'` not `'none'` because the builder previews pages in a same-origin
iframe. Testing against a live Caddy — not just `caddy validate` — showed Django
sends its own `X-Frame-Options: DENY`, producing two conflicting values on
upstream errors; the `>` replace prefix fixes that.

**Login had no rate limiting.** Twelve consecutive failed logins returned 401
every time, never 429. Baserow's own throttle is off by default and counts
concurrency per user, not attempts per IP. A Traefik middleware on a
higher-priority router now covers the four credential endpoints at 5 req/s with
burst 20, keyed on `X-Forwarded-For` depth 1 — without that every request shares
one bucket and the site throttles as a whole.

Ruled out as causes of the reported self-reloading, by measurement: websockets
(101 upgrade in 0.44 s, anonymous auth succeeds), backend latency (0.28–0.36 s),
and TLS/redirects. Remaining candidate is container restarts, which cannot be
seen from outside; `docs/diagnose-production.sh` is read-only and collects it.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `web-frontend/config/nuxt.config.prod.ts` | `inlineStyles: false`; client sourcemaps `hidden` | 1.8 MB CSS re-sent per request; 4.2 MB of source public | low |
| `Caddyfile` | Baseline security headers; scoped frame-ancestors; 404 for build source maps | No headers at all; app framable; maps served | medium |
| `docker-compose.yml` | Traefik rate-limit router on the credential endpoints | No brute-force protection | low |
| `docs/PRODUCTION_HARDENING.md` | New: findings, and the settings only the operator can change | — | low |
| `docs/diagnose-production.sh` | New: read-only VPS diagnostics | Self-reload cause needs server-side data | low |

## Dashboard charts — grouped aggregation service + chart widget (2026-08-03)

Upstream's four chart widgets (bar, line, pie, doughnut) are one `chart` widget
type living in the deleted `premium/`, backed by a premium
`local_baserow_grouped_aggregate_rows` service. Both are rebuilt from scratch
under `backend/src/arabase/` and `web-frontend/modules/arabase/`, keeping
upstream's **registry type names** so dashboards and templates that contain
charts import here instead of being skipped.

New models live in `arabase` (its first migration) rather than in
`contrib.integrations` / `contrib.dashboard`: a fork migration inserted into an
upstream app's sequence conflicts on every merge from upstream. Cross-app FKs to
`core.service`, `dashboard.Widget` and `dashboard.DashboardDataSource` work
unchanged, and both types register into the existing open registries from
`arabase/apps.py`, so no upstream Python file needed editing for the feature
itself. The four core-file edits below are registration and tooling only.

| File | Change | Reason | Merge risk |
|------|--------|--------|------------|
| `backend/src/jadawel/config/settings/base.py` | Appended `ARABASE_CHART_MAX_BUCKETS` (default 100) under a "JADAWEL FORK SETTINGS" heading at the end of the file | A chart grouped by a high-cardinality field would otherwise ask the browser for one category per row | low |
| `web-frontend/modules/arabase/module.js` | Registers `./registryPlugin.js`, the `./locales` langDir, and `./assets/scss/dashboard_chart_widget.scss` | Fork-owned file; the widget needs registry entries, its own strings, and styles | none |
| `web-frontend/scripts/check-locale-parity.mjs` | Added `modules/arabase/locales` to `localeDirectories` | The strict CI gate must cover the fork's own strings, which are deliberately *not* added to upstream modules' locale files | low |
| `backend/src/arabase/apps.py` | Registers the service type and widget type in `ready()` | Fork-owned file | none |
