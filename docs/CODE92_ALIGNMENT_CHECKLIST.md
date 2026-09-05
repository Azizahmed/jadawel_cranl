# Code92 Alignment Checklist

Verifies a project against `docs/CODE92_STACK_STANDARD.md`. Use it when
bootstrapping a new project and as a periodic audit of an existing one.

Placeholders: `<core>` = base namespace, `<fork>` = owned extension namespace.
In Jadawel — the first implementation — these are `jadawel` and `arabase`.

Each item states **what to check** and **how to check it**. An item marked
**[INVARIANT]** maps to §15 of the template and is non-negotiable — a project
that fails one is not aligned, it is a different architecture.

---

## A. Repository shape

- [ ] `backend/` and `web-frontend/` are the only two application runtimes.
      Any third runtime lives in its own directory behind a Compose profile.
      → `ls -d */ | grep -v node_modules`
- [ ] `backend/src/<core>/` and `backend/src/<fork>/` both exist. **[INVARIANT 1]**
      → `ls backend/src`
- [ ] `web-frontend/modules/core/` and `web-frontend/modules/<fork>/` both exist. **[INVARIANT 1]**
      → `ls web-frontend/modules`
- [ ] `backend/tests/` mirrors `backend/src/` directory-for-directory. **[INVARIANT 6]**
      → `diff <(ls backend/src) <(ls backend/tests)`
- [ ] Root files present: `justfile`, `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`,
      `PATCHES.md`, `README.md`, `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE`,
      `.nvmrc`, `.editorconfig`, `.gitattributes`, `.dockerignore`.
- [ ] `docs/`, `docs/agents/`, `.agents/skills/`, `.github/workflows/`,
      `deploy/`, `e2e-tests/` all exist.
- [ ] `.claude/skills` is a symlink to `.agents/skills`.
      → `readlink .claude/skills`
- [ ] No secrets committed: only `*.example` env files are tracked. **[INVARIANT 10]**
      → `git ls-files | grep -E '^\.env' | grep -v example` returns nothing

## B. Backend package layout

- [ ] `src/<core>/config/settings/` contains `base.py` plus at least
      `dev.py`, `test.py`. **[INVARIANT 8]**
- [ ] `settings/utils.py` exists and holds the env-parsing helpers; no ad-hoc
      `bool(os.getenv(...))` in `base.py`.
      → `grep -n 'bool(os.getenv' backend/src/<core>/config/settings/base.py`
- [ ] `legacy_env.py` (or equivalent) is applied before the first `os.getenv`
      in `base.py`.
- [ ] `config/urls.py` appends `plugin_registry.urls`. **[INVARIANT 3]**
- [ ] `config/db_routers.py` defines the read-replica router and it is listed
      in `DATABASE_ROUTERS`.
- [ ] `src/<core>/api/` contains only HTTP concerns; no business logic.
      → serializers live in `api/`, not beside models
- [ ] `src/<core>/core/` holds registries, handlers, actions, jobs, trash,
      notifications, permissions, telemetry.
- [ ] Each bounded context is a Django app under `contrib/` with its own
      `apps.py`, `handler.py`, `models.py`, `api/`, `migrations/`.
- [ ] `INSTALLED_APPS` ends with `"<fork>"`.

## C. Layering

- [ ] Every feature follows view → action → service → handler → model. **[INVARIANT 5]**
- [ ] Handlers contain no `request` parameter and no DRF imports.
      → `grep -rn 'from rest_framework' backend/src/*/**/handler.py` returns nothing
- [ ] Services perform permission checks against operation types; handlers do not.
- [ ] Long-running work is a registered job type, not a blocking request.
- [ ] Every handler used by a view is also callable from a Celery task.

## D. Plugin architecture

- [ ] `<core>/core/registry.py` defines `Instance`, `Registry` and the capability
      mixins (`ModelInstanceMixin`, `CustomFieldsInstanceMixin`,
      `APIUrlsInstanceMixin`, `ImportExportMixin`, …).
- [ ] `<fork>/apps.py` has a single `ready()` that is the **only** place
      registry registrations happen. **[INVARIANT 2]**
      → `grep -rn '_registry.register(' backend/src/<fork>/ | grep -v apps.py`
        returns nothing outside `ready()`
- [ ] Imports inside `ready()` are function-local, not module-level.
- [ ] `<fork>/plugins.py` defines a `Plugin` subclass with `type = "<fork>"` and
      `get_api_urls()` returning a single `<fork>/` prefix. **[INVARIANT 3]**
- [ ] All fork API routes resolve under `/api/<fork>/`.
      → `grep -rn 'path(' backend/src/<fork>/api/urls.py`
- [ ] No route was added by editing `<core>/api/urls.py` or `<core>/config/urls.py`.
      → those two files appear in `PATCHES.md` if they were touched
- [ ] `<CORE>_PLUGIN_DIR` disk-discovery and the frontend `ADDITIONAL_MODULES`
      CSV both work; `deploy/plugins/{install,uninstall,list}_plugin.sh` present.
- [ ] Every core edit is logged in `PATCHES.md` with its reason. **[INVARIANT 2]**
      → `git diff <upstream-ref> -- backend/src/<core>/ web-frontend/modules/core/`
        and confirm each file appears in `PATCHES.md`

## D2. Plugin distribution (only if tier 2 or 3 is in use)

- [ ] Fork code (tier 1) is the default; tiers 2 and 3 are used only where
      something genuinely must ship separately from the repository.
- [ ] `<CORE>_PLUGIN_DIR` discovery runs at settings time and accepts any
      subdirectory containing a `backend/`.
- [ ] A plugin's backend half is an installable Python package whose own
      `ready()` registers into the same registries fork code uses.
- [ ] A plugin's frontend half is a yarn-addable Nuxt module, appended through
      the `ADDITIONAL_MODULES` CSV.
- [ ] `deploy/plugins/{install,uninstall,list}_plugin.sh` present and working.
- [ ] Installs are idempotent — marker files short-circuit a rebuild on restart.
      → check `container_markers/` is written and honoured
- [ ] `build.sh` (once, at install), `runtime_setup.sh` (once, first start
      after install, requires `--runtime`) and `uninstall.sh` (at removal, database
      still reachable) are separate hooks; volume and database work is in the second.
- [ ] A manifest (`<core>_plugin_info.json`) sits at the plugin root.
- [ ] The plugin folder name matches the Django app name; the frontend module
      folder is its kebab-case form.
- [ ] In any single-container image, `<CORE>_PLUGIN_DIR` points inside the data
      volume so installed plugins survive a container replacement.
- [ ] A plugin gets no privileged path into core — it reaches the system only
      through registries, exactly as fork code does. **[INVARIANT 2]**

## E. Frontend module system

- [ ] Every bounded context is a Nuxt module listed in `config/nuxt.config.base.ts`.
- [ ] `modules/<fork>/module.js` declares `dependsOn: ['core']` and is listed last.
- [ ] `module.js` only: adds plugins, pushes CSS, extends pages, registers
      locales. No business logic.
- [ ] `plugin.js` and `registryPlugin.js` are separate files with correct
      `dependsOn` arrays.
- [ ] All `$registry.register(...)` and `$store.registerModuleNuxtSafe(...)`
      calls live in `registryPlugin.js`.
      → `grep -rn '\$registry.register' web-frontend/modules/<fork>/ | grep -v registryPlugin`
- [ ] Every frontend type's `getType()` string equals its backend `type`. **[INVARIANT 4]**
      → for each registered type, compare `<fork>/**/…Types.js` against
        `backend/src/<fork>/**/*_types.py`
- [ ] HTTP calls appear only in `modules/*/services/`.
      → `grep -rn 'client\.\(get\|post\|patch\|delete\)' web-frontend/modules --include=*.vue`
        returns nothing
- [ ] Runtime config defaults are declared in `module.js` under
      `runtimeConfig.public`; no `process.env` reads in component code.
      → `grep -rn 'process.env' web-frontend/modules --include=*.vue`

## F. Database

- [ ] PostgreSQL image includes the vector extension.
- [ ] `DATABASE_URL` supported, with discrete `DATABASE_*` vars as fallback.
- [ ] `CONN_MAX_AGE` defaults to `0` in code and is raised via env per deployment.
- [ ] `CONN_HEALTH_CHECKS = True` applied to every alias.
- [ ] `DATABASE_ROUTERS` set; read pinning is request/task-scoped and atomic
      blocks fall back to the primary.
- [ ] `USER_TABLE_DATABASE` names the connection for user-generated tables.
- [ ] Migrations exist for `<fork>` and are never edited retroactively.

## G. Redis and async **[INVARIANT 9]**

- [ ] `REDIS_URL` is built once from `REDIS_HOST/PORT/USER/PASSWORD/PROTOCOL`,
      with `rediss://` adding `ssl_cert_reqs`/`ssl_ca_certs`.
- [ ] `CACHES["default"]` uses a redis backend with an explicit `KEY_PREFIX`
      and `VERSION` bound to the release version.
- [ ] A second cache alias exists for generated/derived models with its own
      prefix and a deliberately unset `VERSION`.
- [ ] `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_REDBEAT_REDIS_URL`
      and `CHANNEL_LAYERS` all derive from `REDIS_URL`.
- [ ] Any store whose eviction would be a security event has its **own** Redis
      instance with `--maxmemory-policy noeviction`; sharing requires an
      explicit dev-only flag.
- [ ] Redis runs `--appendonly yes` with a named volume.
- [ ] Redis healthcheck authenticates (a bare `PING` returns `NOAUTH`).
- [ ] Separate Celery worker per queue class; slow/bulk tasks routed off the
      default queue via `CELERY_TASK_ROUTES`.
- [ ] `CELERY_TASK_SOFT_TIME_LIMIT` set, hard limit = soft + 60s.
- [ ] `CELERY_BEAT_MAX_LOOP_INTERVAL < CELERY_REDBEAT_LOCK_TIMEOUT`.
- [ ] Singleton backend configured so scheduled tasks cannot double-run.

## H. Cross-cutting services

- [ ] Health checks registered for db, cache, migrations, redis, celery-ping,
      disk/memory, and object storage; expensive checks are admin-only.
- [ ] OpenTelemetry auto-instrumentation for the web framework, ASGI/WSGI,
      Celery, Redis, the DB driver and the HTTP client, gated by one flag.
- [ ] Error reporting wired in both halves.
- [ ] Rate limiting: per-IP toggle, concurrent-request cap, blacklist TTL.
- [ ] File storage abstracted (S3/Azure/GCS extras installed).
- [ ] Email queued through the task system, with a local capture service in dev.
- [ ] Feature flags read from one CSV env var through one module.

## I. Configuration **[INVARIANT 8]**

- [ ] Settings are layered by file; no branching on hostname or deploy name.
- [ ] Every setting reads env with an explicit default at module level.
- [ ] Renamed vars keep working through the legacy-env layer.
- [ ] A new env var lands in all five places in one change: settings, compose
      files, `.env.example`, frontend env remap (if needed), `docs/CONFIGURATION.md`.
- [ ] `docs/CONFIGURATION.md` documents every variable currently read.
      → cross-check `grep -o 'os.getenv("[A-Z_]*"' base.py` against the doc

## J. Testing

- [ ] `DJANGO_SETTINGS_MODULE` fixed in `pyproject.toml`, not the environment.
- [ ] Backend tests mirror source paths; named `test_*.py`.
- [ ] Frontend unit tests pinned to `TZ=UTC` and a fixed locale.
- [ ] E2E suite uses the page-object model with pages under `e2e-tests/pages/`.
- [ ] A structural/hygiene test suite exists under `tests/<fork>/` and asserts
      the invariants linting cannot. **[INVARIANT 7]**
- [ ] Backend changes ship backend tests; component/store changes ship frontend tests.

## K. Tooling and style

- [ ] One formatter+linter for the backend, ≤ 88 columns, with a security
      ruleset (`S`/bandit) enabled.
- [ ] isort declares **both** `<core>` and `<fork>` as first-party.
- [ ] Migrations and generated code excluded from lint.
- [ ] Frontend runs ESLint + Stylelint + Prettier, all three behind
      `yarn lint` / `yarn fix`.
- [ ] SCSS follows BEM, enforced by Stylelint.
- [ ] CSS logical properties are a hard error inside `modules/<fork>/`. **[INVARIANT 11]**
- [ ] `just` recipes exist for: `init`, `dev up`, `dc-dev up`, `b <cmd>`,
      `f <cmd>`, `lint`, `fix`, `test`. **[INVARIANT 12]**
      → `just` prints the index
- [ ] CI invokes the same `just`/`yarn` recipes a human runs — no bespoke CI shell.

## L. Internationalization **[INVARIANT 11]**

- [ ] At least two locales, one of which is English.
- [ ] The locale list is declared once in `config/locales.js` and each entry
      carries `dir`.
- [ ] Every user-facing string exists in both locale files.
      → `yarn locale:check --strict`
- [ ] Direction is derived from the active locale at the document root during
      SSR, not set by CSS or a client-side effect.
- [ ] Placeholders, message links, technical tokens and digits are verbatim
      across locales.
- [ ] Recurring domain terms are fixed in a glossary before first use.

## M. CI gates

- [ ] Jobs exist for: backend lint, backend test, frontend lint, locale parity,
      frontend test, image build, E2E.
- [ ] All are required for merge.
- [ ] Concurrency grouped per ref with `cancel-in-progress: true`.
- [ ] The two structural gates (locale parity, fork hygiene) are runnable
      locally and documented in `AGENTS.md`.

## N. Deployment **[INVARIANT 13]**

- [ ] Compose files separated by intent, not by conditionals inside one file.
- [ ] Every stateful service declares a healthcheck; auth-protected services
      authenticate in the probe.
- [ ] Named volumes for every piece of persistent state.
- [ ] `docs/DEPLOY_<TARGET>.md` states what shipping actually means, including
      whether pushing code deploys anything.
- [ ] The working production environment set is captured in a document.
- [ ] Decommissioned infrastructure is marked as history in `CLAUDE.md` rather
      than deleted, so it is not mistaken for live.

## O. Documentation and agent surface

- [ ] `AGENTS.md` states build/test/lint truth, layout, style, testing and
      commit conventions.
- [ ] `CLAUDE.md` includes `@AGENTS.md` and adds identity, remotes and deploy.
- [ ] `CONTEXT.md` defines each domain term **and the synonyms to avoid**.
- [ ] `PATCHES.md` is current. **[INVARIANT 2]**
- [ ] `docs/agents/{domain,issue-tracker,triage-labels}.md` present.
- [ ] Baseline skills carried forward under `.agents/skills/`.
- [ ] Commits are imperative Conventional Commits; history is linear.

---

## Scoring

| Result | Meaning |
|---|---|
| All **[INVARIANT]** items pass | Aligned. Divergence elsewhere is a deliberate project choice. |
| Any **[INVARIANT]** item fails | Not aligned. Fix before building further — each one gets more expensive with every feature added on top. |
| Non-invariant items failing | Drift. Record the reason in `docs/` or fix it. |

## Bootstrapping a new project

In order, because each step depends on the one before:

1. Copy the skeleton: `backend/`, `web-frontend/`, `e2e-tests/`, `deploy/`,
   `docs/agents/`, `.agents/skills/`, `justfile`, compose files, CI workflows.
2. Choose `<core>` and `<fork>` names. Rename the Python distribution, import
   namespace, `src/` dir, frontend alias, env var prefix, image paths, task
   names, metric names, table prefixes and headers together — then record how
   in `docs/RENAME_TO_<CORE>.md`.
3. Write `CONTEXT.md` first, before any feature code. The vocabulary decides
   the module names.
4. Stand up `<fork>` empty but wired: `apps.py` with an empty `ready()`,
   `plugins.py` with the API prefix, `module.js` + `plugin.js` +
   `registryPlugin.js`, and one passing hygiene test.
5. Bring up the data layer: Postgres, Redis, the second Redis, three Celery
   workers. Confirm `/api/_health/` is green before the first feature.
6. Turn on all seven CI gates while they are trivially green.
7. Write `docs/DEPLOY_<TARGET>.md` and ship a hello-world through it end to end.
8. Only then start on features.
