# Code92 Stack Standard

The canonical structure every Code92 project starts from. Jadawel is the first
implementation and the codebase this was read out of; the standard itself is
stated in a project-neutral way so a new project can adopt it without carrying
Jadawel's domain with it.

Two names appear as placeholders throughout:

| Placeholder | In Jadawel | Meaning |
|---|---|---|
| `<core>` | `jadawel` | The upstream/base application namespace. Owns the framework, registries and generic domain. |
| `<fork>` | `arabase` | The **additive extension namespace**. All project-specific work lives here. |

Every project gets both, even a greenfield one. The split is what makes the
structure survive: `<core>` is code you rebase, vendor or freeze; `<fork>` is
code you own. Nothing project-specific is ever written into `<core>`.

---

## 1. Stack

| Layer | Technology | Version pinned here |
|---|---|---|
| Backend language | Python | `==3.14.*` (`requires-python`) |
| Backend framework | Django | 5.2.x + Django REST Framework 3.16 |
| API schema | drf-spectacular (OpenAPI 3) | 0.29 |
| Auth | `djangorestframework-simplejwt` | 5.5 |
| Realtime | Django Channels + Daphne, `channels_redis` layer | 4.3 |
| Async jobs | Celery + `celery-redbeat` + `celery-singleton` | 5.6 |
| Database | PostgreSQL 15 with `pgvector` | `pgvector/pgvector:pg15` |
| Cache / broker | Redis 7 (`redis:7-alpine`) | `django-redis` 6.0 |
| Frontend language | JavaScript / TypeScript, Vue 3 SFCs | — |
| Frontend framework | Nuxt 3 (SSR) on Node | Node 24 (`.nvmrc`) |
| State | Vuex-style namespaced stores registered at runtime | — |
| Styling | SCSS, BEM, CSS logical properties | Stylelint-enforced |
| i18n | `@nuxtjs/i18n` | 10.2 |
| Packaging | `uv` + hatchling (backend), `yarn` (frontend) | — |
| Task runner | `just` (root + per-half justfiles) | — |
| Containers | Docker Compose (dev, prod, all-in-one) | — |
| Observability | OpenTelemetry, Sentry, PostHog, django-health-check | — |

Two runtimes, one repository. Never a third: a sidecar that is not Python or
Node (see `embeddings/`) runs behind a Compose profile and is optional to boot.

---

## 2. Repository layout

```
backend/                  Python half
  pyproject.toml          deps, ruff, pytest, uv — single source of backend config
  src/<core>/             upstream-derived application
  src/<fork>/             this project's additive backend code
  tests/<core>/           mirrors src/<core>/ one-to-one
  tests/<fork>/           mirrors src/<fork>/, plus fork-hygiene tests
  docker/                 backend image + entrypoint
web-frontend/             Node half
  package.json            scripts are the contract: dev/build/test/lint/fix
  nuxt.config.ts          three-way switch → config/nuxt.config.{dev,prod,test}.ts
  config/                 nuxt configs + shared locales.js
  modules/core/           upstream-derived Nuxt module
  modules/<domain>/       one Nuxt module per bounded context
  modules/<fork>/         this project's additive frontend module
  locales/                en.json + <primary>.json, parity enforced in CI
  test/                   Vitest unit tests, fixtures, helpers
  .storybook/, stories/   component workbench
e2e-tests/                Playwright, page-object model, own justfile
embeddings/               optional sidecar, Compose profile `ai`
deploy/                   docker, helm, nginx/apache/traefik, plugin install scripts
docs/                     architecture, configuration, audits, runbooks
docs/agents/              agent-facing conventions (domain, issues, labels)
.agents/skills/           reusable agent workflows (`.claude/skills` symlinks here)
.github/workflows/        CI gates + image publish
justfile                  root task index; `just b <cmd>` / `just f <cmd>`
docker-compose.yml        production topology
docker-compose.dev.yml    development topology
Dockerfile                deploy image (pins a published digest)
AGENTS.md / CLAUDE.md     agent instructions; CLAUDE.md @-includes AGENTS.md
CONTEXT.md                domain vocabulary (canonical terms + rejected synonyms)
PATCHES.md                log of every unavoidable edit to <core>
```

**The mirror rule.** `backend/tests/` mirrors `backend/src/` directory for
directory. A reader who knows where the code is knows where its test is without
searching.

---

## 3. Backend structure

### 3.1 Package layout

```
src/<core>/
  manage.py, version.py, middleware.py, actions.py
  config/
    settings/{base,dev,test,e2e,heroku}.py   layered settings
    settings/utils.py                        env parsing helpers (str_to_bool, crontab, …)
    urls.py       root urlconf; appends plugin_registry.urls
    asgi.py wsgi.py celery.py
    db_routers.py read-replica router with per-request alias pinning
    legacy_env.py backwards-compatible env var renames
  api/            HTTP layer only — one package per resource, mirrors urls.py
  core/           framework: registries, handlers, actions, jobs, trash, search,
                  notifications, permissions, telemetry, user, user_files, …
  contrib/<app>/  bounded contexts (database, dashboard, builder, automation,
                  integrations) — each a full Django app
  ws/             websocket consumers
  throttling/     rate limiting
  test_utils/     fixtures and factories shipped with the package
```

### 3.2 The five-layer call path

Every backend feature is written in this order, outermost first:

```
API view (api/…/views.py)        HTTP, permissions classes, serializers, error mapping
   ↓
Action (…/actions.py)            undo/redo + audit wrapper; registered in action registry
   ↓
Service (…/service.py)           permission checks against the operation registry
   ↓
Handler (…/handler.py)           business logic, transactions, signals — no HTTP awareness
   ↓
Model (…/models.py)              Django ORM
```

`CoreService.__init__` holds a `CoreHandler`; the service filters querysets
through `OperationType` registries, the handler never sees a request. A handler
must be callable from a Celery task and an API view alike — that is the test of
whether the split is right.

Serializers live in `api/`, never next to models. Long-running work becomes a
**job type** (`core/jobs/`) rather than a blocking request.

### 3.3 Django app registration

Each app is a real `AppConfig`. `INSTALLED_APPS` ends with the fork app:

```python
INSTALLED_APPS = [
    …django, rest_framework, corsheaders, drf_spectacular,
      djcelery_email, health_check.*…,
    "<core>.core", "<core>.api", "<core>.ws",
    "<core>.contrib.database", "<core>.contrib.integrations",
    "<core>.contrib.builder", "<core>.contrib.dashboard",
    "<core>.contrib.automation",
    *<CORE>_BUILT_IN_PLUGINS,
    "<fork>",          # always last
]
```

---

## 4. The plugin architecture

This is the load-bearing idea of the whole template: **features attach through
registries, never through edits to core files.**

### 4.1 Registry mechanism

`<core>/core/registry.py` defines `Instance` (one registerable type, identified
by a string `type`) and `Registry` (a named collection), plus mixins that
compose extra capability onto a type:

| Mixin | Grants the type |
|---|---|
| `ModelInstanceMixin` | a Django model, so the registry can resolve type-by-model |
| `CustomFieldsInstanceMixin` | its own serializer fields on a polymorphic endpoint |
| `PublicCustomFieldsInstanceMixin` | a second, public-safe field set |
| `APIUrlsInstanceMixin` | its own urlpatterns, collected by `registry.api_urls` |
| `MapAPIExceptionsInstanceMixin` | declarative exception → HTTP error mapping |
| `ImportExportMixin` / `EasyImportExportMixin` | serialize/deserialize for export, snapshot, template |
| `InstanceWithFormulaMixin` | participation in the formula language |

`<core>` exposes 42 registries. The ones a new project will actually extend:

```
plugin_registry                 mounts whole feature sets and their URL trees
application_type_registry       a new kind of application in a workspace
view_type_registry              a new way to render a table
field_type_registry             a new column type
service_type_registry           a new data source for widgets/pages/automations
integration_type_registry       a new external system connector
widget_type_registry            a new dashboard widget
mcp_tool_registry               a new agent-callable tool (+ call interceptors)
auth_provider_type_registry     a new login method
permission_manager_registry     a new authorization strategy
object_scope_registry           a new permission scope
operation_type_registry         a new named permission
trash_item_type_registry        a new restorable item
job_type_registry               a new background job
notification_type_registry      a new in-app notification
table_exporter_registry         a new export format
webhook_event_type_registry     a new outbound webhook event
data_sync_type_registry         a new two-way sync source
element_type_registry           a new page-builder element
automation_node_type_registry   a new automation step
```

### 4.2 The single wiring point

The fork app's `ready()` is the *only* place registrations happen. Imports stay
inside the method so Django's app-loading order is respected:

```python
class <Fork>Config(AppConfig):
    name = "<fork>"

    def ready(self):
        from <fork>.plugins import <Fork>Plugin
        from <core>.core.registries import plugin_registry
        plugin_registry.register(<Fork>Plugin())

        from <fork>.dashboard.widgets.widget_types import ChartWidgetType
        from <core>.contrib.dashboard.widgets.registries import widget_type_registry
        widget_type_registry.register(ChartWidgetType())

        from <fork>.views.view_types import HtmlPageViewType
        from <core>.contrib.database.views.registries import view_type_registry
        view_type_registry.register(HtmlPageViewType())     # mounts its API too
        …
```

Registering a `ViewType` is all it takes to mount `/api/database/views/<type>/`
— core builds that urlconf from `view_type_registry.api_urls`. Adding a route
never means editing a urls.py.

### 4.3 URL mounting

```
config/urls.py:   ^api/ → <core>.api.urls
                + plugin_registry.urls          ← every plugin's routes
                + static(MEDIA_URL)

api/urls.py:      one include() per resource, then
                + application_type_registry.api_urls
                + auth_provider_type_registry.api_urls
                + service_type_registry.api_urls
```

The fork's `Plugin` subclass returns its own prefix so an upstream route can
never collide:

```python
class <Fork>Plugin(Plugin):
    type = "<fork>"
    def get_api_urls(self):
        return [path("<fork>/", include("<fork>.api.urls", namespace=self.type))]
```

Result: **all project-specific API lives under `/api/<fork>/`.**

### 4.4 Where a plugin lives — three tiers

"Plugin" means three different things in this architecture, and conflating them
is the usual source of confusion. All three attach through the *same* registry
mechanism (§4.1-4.3); what differs is where the code lives and who ships it.

| Tier | Lives in | Ships with | Use it for |
|---|---|---|---|
| **1 · Fork code** | `backend/src/<fork>/`, `web-frontend/modules/<fork>/` | the repository | everything this project owns. The default. |
| **2 · Built-in plugin** | its own package, listed in `<CORE>_BUILT_IN_PLUGINS` | the image | an optional feature set the product ships but can disable |
| **3 · Installed plugin** | a directory under `<CORE>_PLUGIN_DIR` | the operator, at runtime | third-party or per-customer extensions the core team never sees |

Tier 1 is where a new project puts essentially all of its work. Tiers 2 and 3
exist so the architecture can accept code it was not compiled with — do not
reach for them until something genuinely needs to ship separately.

### 4.5 Installed plugins — the on-disk contract

Discovery happens at settings time, before Django loads any app:

```python
<CORE>_PLUGIN_DIR_PATH = Path(os.environ.get("<CORE>_PLUGIN_DIR", "/<core>/plugins"))

if <CORE>_PLUGIN_DIR_PATH.exists():
    <CORE>_PLUGIN_FOLDERS = [
        f for f in <CORE>_PLUGIN_DIR_PATH.iterdir()
        if f.is_dir() and Path(f, "backend").exists()
    ]
<CORE>_BACKEND_PLUGIN_NAMES = [d.name for d in <CORE>_PLUGIN_FOLDERS]
```

A plugin is a directory with up to two halves, mirroring the monorepo itself:

```
<plugin_name>/
  backend/                  a valid installable Python package
    build.sh                optional — run once at install time
    runtime_setup.sh        optional — run on every container start
  web-frontend/             a valid yarn-addable Nuxt module
    build.sh
    runtime_setup.sh
```

The backend half is `pip install`-ed (editable in dev) and its name is appended
to `INSTALLED_APPS`, so its own `AppConfig.ready()` registers into exactly the
registries §4.1 lists — a plugin has the same reach as fork code. The frontend
half is `yarn add`-ed and its module path appended to `ADDITIONAL_MODULES`, a
CSV the Nuxt config concatenates onto the base module list:

```js
const modules = baseModules.concat(additionalModules)
```

`deploy/plugins/` holds `install_plugin.sh`, `uninstall_plugin.sh` and
`list_plugins.sh`. Two details there are load-bearing and easy to lose in a
rewrite:

- **Marker files make installs idempotent.** Each half writes a
  `container_markers/<name>.{backend,web-frontend}-built` file; a restart that
  finds the marker skips the build instead of rebuilding on every boot.
- **Three hooks, all marker-guarded.** `build.sh` runs once at install,
  `runtime_setup.sh` once on the first start after install (and only when the
  installer is passed `--runtime`), `uninstall.sh` at removal while the database
  is still reachable. Database and volume work belongs in `runtime_setup.sh` — a
  build-time side effect is lost when the container is replaced. Forcing any of
  them to re-run means `--overwrite`.

A plugin arrives one of three ways: baked into an image at build time, fetched
at container start from a URL or git ref, or mounted on a volume. In the
all-in-one image `<CORE>_PLUGIN_DIR` points inside the data volume
(`/<core>/data/plugins`) so installed plugins survive a container replacement.

---

## 5. Frontend structure

### 5.1 Module system

Every bounded context is a Nuxt module registered in `config/nuxt.config.base.ts`:

```js
const baseModules = [
  './modules/core/module.js',
  './modules/database/module.js',
  './modules/dashboard/module.js',
  './modules/builder/module.js',
  './modules/automation/module.js',
  './modules/integrations/module.js',
  './modules/<fork>/module.js',      // always last
]
modules: [...baseModules, ...ADDITIONAL_MODULES, '@nuxtjs/i18n', '@sentry/nuxt/module']
```

A module's `module.js` is its manifest. It may only do these things:

```js
export default defineNuxtModule({
  meta: { name: '<fork>-module' },
  dependsOn: ['core'],
  setup(options, nuxt) {
    const { resolve } = createResolver(import.meta.url)
    addPlugin({ src: resolve('./plugin.js') })          // app-level behaviour
    addPlugin({ src: resolve('./registryPlugin.js') })  // registry registrations
    nuxt.options.css.push(resolve('./assets/scss/<fork>.scss'))
    extendPages((pages) => pages.push(...routes))
    nuxt.hook('i18n:registerModule', (register) =>
      register({ langDir: resolve('./locales'), locales }))
  },
})
```

### 5.2 Two plugins, deliberately separate

| File | Runs | Contains |
|---|---|---|
| `plugin.js` | `dependsOn: ['i18n']` | app-wide behaviour: direction, `<html lang/dir>`, global directives |
| `registryPlugin.js` | `dependsOn: ['core','store','dashboard','database']` | `$registry.register(...)` and `$store.registerModuleNuxtSafe(...)` |

They are split because registry registrations depend on namespaces other
modules create at their own plugin time. Collapsing them produces load-order
bugs that only appear in production SSR.

### 5.3 Frontend registry

`modules/core/registry.js` mirrors the backend exactly: a `Registerable` base
class with a static `getType()` (**the string must equal the backend type**),
`getOrder()` for stable listing, and a namespaced `Registry`. Backend
`ViewType.type == "html_page"` ⇔ frontend `HtmlPageViewType.getType() ===
'html_page'`. That equality is the contract between the halves.

### 5.4 Module internals

```
modules/<name>/
  module.js            manifest (above)
  plugin.js            app behaviour
  registryPlugin.js    registry + store registration
  routes.js            route definitions consumed by extendPages
  pages/               route components
  components/          presentational + container components (BEM SCSS)
  store/               one namespaced store per aggregate
  services/            thin HTTP clients — one file per backend resource
  <thing>Types.js      Registerable subclasses (viewTypes, widgetTypes, adminTypes, …)
  locales/{en,<primary>}.json
  assets/scss/
  utils/ mixins/ composables/ directives/ middleware/
```

`services/*.js` is the only place `fetch`/`$client` calls are written. Stores
call services; components call stores. A component never talks HTTP.

### 5.5 Runtime configuration

Defaults are declared in `modules/core/module.js` under
`runtimeConfig.public`, overridable at runtime by `NUXT_*` env vars, with
`env-remap.mjs` translating legacy names. **No `process.env` reads in component
code.**

---

## 6. Data layer

### 6.1 PostgreSQL

- `pgvector/pgvector:pg15` — vector support present from day one, unused until needed.
- `DATABASE_URL` (dj-database-url) with discrete `DATABASE_*` vars as fallback.
- `DATABASE_ROUTERS = ["<core>.config.db_routers.ReadReplicaRouter"]`.
  Reads pin a replica alias for the life of a request/task via `asgiref.local.Local`;
  anything inside an atomic block goes to the primary to avoid replication lag.
- `CONN_MAX_AGE` defaults to **0** and is raised per-deployment (`<CORE>_CONN_MAX_AGE=60`),
  because one settings module serves WSGI, ASGI and Celery and persistent
  connections exhaust the pool in the latter two.
- `CONN_HEALTH_CHECKS = True` on every alias.
- `USER_TABLE_DATABASE` names the connection holding user-generated tables, so
  application schema and user schema can be split later without code changes.
- `django-cachalot` for ORM-level query caching, with a local patch module.

### 6.2 Redis — five distinct roles, one URL builder

`REDIS_URL` is assembled once from `REDIS_HOST/PORT/USER/PASSWORD/PROTOCOL`,
with `rediss://` adding `ssl_cert_reqs` and `ssl_ca_certs`. Everything derives
from it:

| Role | Setting | Notes |
|---|---|---|
| Django cache | `CACHES["default"]` | `django_redis.cache.RedisCache`, `KEY_PREFIX="<core>-default-cache"`, `VERSION=VERSION` — a release invalidates its own cache |
| Generated-model cache | `CACHES["generated-models"]` | separate prefix, `VERSION=None` (survives releases deliberately) |
| Celery broker + result backend | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | results expire in 1h |
| Beat schedule | `CELERY_REDBEAT_REDIS_URL` | lock timeout = loop interval + 60s |
| Channels layer | `CHANNEL_LAYERS.default` | `channels_redis.core.RedisChannelLayer` |

Plus **a second, isolated Redis instance** for security-sensitive state
(`MCP_PROTECTION_REDIS_URL`, `--maxmemory-policy noeviction`). Sharing the main
Redis for it requires an explicit opt-in flag that production refuses. The
pattern generalizes: *any store whose eviction would be a security event gets
its own instance.*

Redis runs with `--appendonly yes` and a named volume — the beat schedule and
throttle counters must survive a container recreation.

### 6.3 Async work

```
celery                  default queue — interactive tasks
celery-export-worker    "export" queue — exports, trash purge, usage, row counts, job cleanup
celery-beat-worker      redbeat scheduler, single-owner via Redis lock
celery-flower           dev-only monitoring UI
```

`CELERY_TASK_ROUTES` maps slow/bulk task paths onto the `export` queue so a
large export can never starve interactive work. `CELERY_TASK_SOFT_TIME_LIMIT`
defaults to 5 min, hard limit soft+60s. `celery-singleton` (with a custom Redis
backend class) prevents duplicate scheduled runs.

---

## 7. Cross-cutting services

| Concern | Implementation |
|---|---|
| Health | `django-health-check` with db, cache, migrations, redis, celery-ping, psutil, s3 sub-checks; `/api/_health/` public-lite, `/api/_health/full/` admin-only |
| Telemetry | OpenTelemetry SDK + OTLP HTTP exporter; auto-instrumentation for Django, ASGI, WSGI, Celery, Redis, psycopg, requests, botocore, grpc, aiohttp; gated by `otel_is_enabled()` |
| Errors | `sentry-sdk` backend, `@sentry/nuxt` frontend |
| Product analytics | PostHog, both halves |
| Rate limiting | `<core>/throttling/` — `RateLimit.from_string`, per-IP toggle, concurrent-request cap, blacklist TTL |
| Files | `django-storages` with S3/Azure/GCS extras; `MEDIA_URL` served by the app in dev, by the proxy in prod |
| Email | `django-celery-email-reboot` (queued), MJML compiler service in dev, MailHog for capture |
| Feature flags | `FEATURE_FLAGS` CSV env → `<core>/core/feature_flags.py` |
| Agent surface | MCP tools in a registry with **call interceptors** and contract validation at startup |

---

## 8. Configuration

Settings are layered, never conditional-in-one-file:

```
config/settings/base.py     everything, env-driven          (~1700 lines)
config/settings/dev.py      imports base, relaxes
config/settings/test.py     imports base, isolates
config/settings/e2e.py      imports test, seeds
config/settings/heroku.py   platform overrides
```

Rules that keep `base.py` maintainable:

1. Every setting reads `os.getenv` with an explicit default at module level.
2. Parsing goes through `settings/utils.py` (`str_to_bool`, `try_int`,
   `get_crontab_from_env`, `read_file`, `set_settings_from_env_if_present`).
3. Renames go through `legacy_env.py`, applied **before the first `os.getenv`**,
   so a deployment's old variable names keep working.
4. A new env var is propagated to five places at once: `base.py`, the compose
   files, `.env.example`, `web-frontend/env-remap.mjs` (if the frontend needs
   it) and `docs/CONFIGURATION.md`. This is what the
   `add-django-config-env-var` skill automates.
5. Secrets never enter the tree: `.env.local` (local processes),
   `.env.docker-dev` (Docker), deploy config (production). Only `*.example`
   files are committed.

---

## 9. Testing

| Level | Tool | Location | Command |
|---|---|---|---|
| Backend unit/integration | pytest + pytest-django | `backend/tests/**` mirroring `src/**` | `just b test -n=auto` |
| Backend performance | pytest, marked | `backend/tests/<core>/performance/` | opt-in |
| Fork hygiene | pytest | `backend/tests/<fork>/` | `pytest tests/<fork> -q` |
| Frontend unit | Vitest + `environment: 'nuxt'`, happy-dom, `pool: 'forks'` | `web-frontend/test/unit/` | `just f test` |
| Component workbench | Storybook :6006 | `web-frontend/stories/` | `just dev up` |
| E2E | Playwright, page-object model | `e2e-tests/tests/`, `e2e-tests/pages/` | `e2e-tests/justfile` |
| Load smoke | node script asserted in CI | `e2e-tests/scripts/production-load-smoke.mjs` | CI gate |

Vitest is pinned to `TZ=UTC` and `LC_ALL=en_GB.UTF-8` so snapshots are
machine-independent. `DJANGO_SETTINGS_MODULE` is fixed in `pyproject.toml`, not
in the environment.

**Fork-hygiene tests are the enforcement arm of this template.** They assert
structural invariants, not behaviour: that removed packages stay unimportable,
that a licence notice is intact, that a flag stays true. Every project gets a
`tests/<fork>/test_fork_hygiene.py`.

---

## 10. Tooling and code style

**Backend** — ruff for both lint and format, 88 columns, `E,W,F,I,S` selected
(`S` = flake8-bandit, security lint on by default). isort sections are
`future, standard-library, django, third-party, first-party, local-folder`, with
**both `<core>` and `<fork>` declared first-party**. Migrations and generated
code are excluded. Per-file ignores relax assert/hardcoded-password rules in
tests only.

**Frontend** — ESLint + Stylelint + Prettier, each with its own cache dir.
`yarn lint` runs all three, `yarn fix` fixes all three. SCSS class names follow
BEM; Stylelint enforces it. Vue 3 semantics: `import { h } from 'vue'` in render
functions; a file containing JSX must be named `.jsx`/`.tsx` so Vite parses it.

**Directional CSS** — CSS logical properties (`margin-inline-start`,
`inset-inline-end`) are a hard error inside `modules/<fork>/` and a warning
elsewhere. This is how a bidirectional UI stays correct without a second
stylesheet.

**Task running** — `just` is the only entry point a human or agent needs:

```
just              recipe index
just init         install both halves
just dev up       local processes  (app :3000, API :8000, Storybook :6006)
just dc-dev up -d the same stack in Docker
just b <cmd>      backend/justfile   (b test, b migrate, b lint)
just f <cmd>      web-frontend/justfile (f test, f lint)
just lint | fix | test
```

Backend commands run through `uv`, frontend through `yarn` on Node 24.

---

## 11. Internationalization

- One primary locale plus English, both mandatory. Every user-facing string
  ships in `en.json` **and** the primary locale file.
- CI runs a strict parity check (`yarn locale:check`); one missing key fails
  the build. A `--baseline` mode exists for the initial adoption only.
- The locale list is declared once in `config/locales.js` and shared by
  `nuxt.config.base.ts` and every module's `i18n:registerModule` hook. Each
  entry carries a `dir` field.
- Direction is driven from the active locale in the fork's `plugin.js` via
  `useHead({ htmlAttrs })`, so it is correct during SSR (no first-paint flash)
  and propagates into teleported DOM (modals, dropdowns, tooltips).
- Placeholders (`{name}`), message links (`@:action.save`), Latin technical
  tokens and Western digits stay verbatim across locales.
- Recurring domain terms are fixed in a glossary document before first use.

---

## 12. CI gates

Seven jobs, all required, concurrency-grouped per ref with
`cancel-in-progress`:

```
backend-lint          ruff check + ruff format --check
backend-test          smoke + fork-hygiene tests (postgres + redis services)
frontend-lint         eslint
frontend-locale-parity  yarn locale:check --strict
frontend-test         vitest
docker-build          both images build
desktop-e2e           Playwright + production load gate
```

The two that are easy to miss locally — locale parity and fork hygiene — are
exactly the two that guard the structure rather than the behaviour. Run both
before pushing.

---

## 13. Deployment topology

Compose files are separated by intent, never by conditionals:

| File | Purpose |
|---|---|
| `docker-compose.yml` | production: caddy, backend, web-frontend, 3 celery workers, db, redis, isolated redis, volume-permissions-fixer |
| `docker-compose.dev.yml` | development: the above plus storybook, flower, mjml compiler, mailhog, otel-collector, embeddings |
| `docker-compose.no-caddy.yml` | behind an external TLS terminator |
| `docker-compose.all-in-one.yml` | single-container supervisor image |
| `docker-compose.build.yml` | build-only overlay |
| `Dockerfile` (root) | **deploy image: pins a published image by digest** |

Named volumes for `pgdata`, `redisdata`, isolated-redis data, `media`, and
proxy state. Every stateful service declares a `healthcheck`, and the Redis
probe authenticates (a bare `PING` against a password-protected server answers
`NOAUTH` and never tests anything).

Where the platform cannot build the monorepo, CI builds and publishes the image
and the deploy target only pulls it. Then **pushing code deploys nothing** —
shipping is: push → run the publish workflow → bump the pinned digest →
redeploy. Whichever model a project uses, the deploy procedure is written down
in `docs/DEPLOY_<TARGET>.md` and the working environment set is captured
alongside it.

---

## 14. Documentation and agent surface

| File | Role |
|---|---|
| `AGENTS.md` | build/test/lint truth, layout, style, testing, commit conventions |
| `CLAUDE.md` | `@AGENTS.md` include + project identity, remotes, deploy, decommissioned infra |
| `CONTEXT.md` | domain vocabulary: canonical term, definition, *and the synonyms to avoid* |
| `PATCHES.md` | every unavoidable edit to `<core>`, with its reason |
| `docs/agents/domain.md` | how to use `CONTEXT.md` and ADRs |
| `docs/agents/issue-tracker.md` | where specs live |
| `docs/agents/triage-labels.md` | canonical labels |
| `docs/CONFIGURATION.md` | every env var |
| `docs/*_PLAN.md`, `docs/AUDIT.md` | scope and history, so it is not re-derived |
| `.agents/skills/<name>/SKILL.md` | reusable agent workflows; `.claude/skills` symlinks here |

Skills carried forward by default: `add-<framework>-config-env-var`,
`create-in-app-notification`, `create-update-service`, `write-backend-unit-test`,
`write-frontend-unit-test`, `silk-profiler` (or the equivalent profiler).

Commits are short imperative Conventional Commits (`feat(dashboard):`,
`fix(mcp):`, `chore(deploy):`). History is linear — rebase, never merge.

---

## 15. The invariants

Everything above is negotiable per project except these. They are what the
alignment checklist and, later, the alignment skill actually enforce.

1. **Two namespaces.** `<core>` is rebased or frozen; `<fork>` is owned. Project
   work goes in `<fork>` only.
2. **Registries, not edits.** A feature attaches through a registry hook in one
   `ready()` and one `registryPlugin.js`. A core edit is a last resort and is
   logged in `PATCHES.md` with its reason.
3. **One API prefix for the fork.** `/api/<fork>/` via a `Plugin` subclass, so
   an upstream route can never collide.
4. **Type strings match across halves.** Backend `Type.type` ≡ frontend
   `getType()`.
5. **Five layers, one direction.** view → action → service → handler → model.
   The handler is HTTP-unaware and callable from a Celery task.
6. **Tests mirror source.** `tests/**` reproduces `src/**` path for path.
7. **Structural tests exist.** A fork-hygiene suite asserts the invariants that
   linting cannot.
8. **Config is env-driven and layered.** No settings branch on hostname; new
   vars propagate to all five places at once.
9. **Redis roles are explicit.** One URL builder, named prefixes, versioned
   cache keys, and a separate instance for anything whose eviction is a
   security event.
10. **Secrets stay out of the tree.** Only `*.example` is committed.
11. **Two locales minimum, parity enforced in CI.** Direction driven from the
    locale, styling in logical properties.
12. **`just` is the interface.** Every routine action has a recipe; CI calls the
    same recipes a human does.
13. **Deploy is written down.** A `docs/DEPLOY_*.md` states what shipping
    actually means for this project.
