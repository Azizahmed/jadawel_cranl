---
name: jadawel-plugin
description: Build a Jadawel plugin as additive fork code under `arabase/`. Use when adding a type to one of Jadawel's registries (view, field, widget, service, MCP tool, notification, exporter, admin page), when adding routes under `/api/arabase/`, or when packaging a standalone plugin for `JADAWEL_PLUGIN_DIR`.
version: 1.0.0
---

# Build a Jadawel Plugin

A plugin here is **additive** code that attaches to core through a **seam** — a
registry hook — and nowhere else. Core builds its urlconfs, its serializers and
its UI from what the registries hold, so registering a type is the whole
integration. There is no second wiring step and no core file to edit.

Work in this order. Each step names what "done" looks like; the gates at the end
are the real completion bar.

## 1. Pick the seam

Name the registry before writing any code. Copy the closest existing type rather
than deriving a new shape.

| Intent | Registry | Core base class |
|---|---|---|
| a new way to render a table | `view_type_registry` | `contrib/database/views/registries.py` |
| a new column type | `field_type_registry` | `contrib/database/fields/registries.py` |
| a new dashboard widget | `widget_type_registry` | `contrib/dashboard/widgets/registries.py` |
| a new data source for widgets, pages, automations | `service_type_registry` | `core/services/registries.py` |
| a new external system connector | `integration_type_registry` | `core/integrations/registries.py` |
| a new agent-callable tool | `mcp_tool_registry` | `core/mcp/registries.py` |
| a new in-app notification | `notification_type_registry` | `core/notifications/registries.py` |
| a new background job | `job_type_registry` | `core/jobs/registries.py` |
| a new export format | `table_exporter_registry` | `contrib/database/export/registries.py` |
| a whole feature plus its own URL tree | `plugin_registry` | `core/registries.py` |

Paths are relative to `backend/src/jadawel/`. For anything not listed, the full
set of seams is one command away:

```bash
grep -rhoE '^[a-z_]+_registry = [A-Za-z]+\(\)' backend/src/jadawel --include=*.py | sort -u
```

Frontend-only seams (admin pages, settings panels) are namespaces on `$registry`;
read `web-frontend/modules/core/adminTypes.js` and its siblings.

**Done when:** you can name the registry, its core base class file, and the
existing type you are copying.

## 2. Stay additive

Every file you create or modify lives under one of:

- `backend/src/arabase/`
- `web-frontend/modules/arabase/`
- `backend/tests/arabase/`
- `web-frontend/test/`

Check it before you finish:

```bash
git status --short | grep -E 'src/jadawel/|modules/(core|database|dashboard|builder|automation|integrations)/'
```

That command returning nothing is the pass condition. If a core edit is genuinely
unavoidable, add an entry to `PATCHES.md` giving the file and the reason in the
same change.

## 3. Backend

Give the feature its own package under `backend/src/arabase/<feature>/`, following
the shape the existing ones use — `models.py`, `handler.py`, `<thing>_types.py`,
`exceptions.py`, `constants.py`.

1. **Models and migration**, if the plugin stores anything. Migrations go in
   `backend/src/arabase/migrations/` and are numbered on from the last one:
   `just b makemigrations arabase`.
2. **The type class** subclasses the core base class from step 1 and sets a
   `type` string that is unique across that registry.
3. **Business logic goes in a handler**, not the type class and not a view. The
   handler takes no `request` and imports no DRF, so a Celery task can call it.
4. **API routes**, only if the plugin needs endpoints core does not already
   generate. Add the view under `backend/src/arabase/api/<feature>/` and a
   `re_path` in `backend/src/arabase/api/urls.py`. They mount under
   `/api/arabase/` through `ArabasePlugin`.

Types that carry their own urlpatterns (view types, service types) need no route
work at all — core collects `registry.api_urls`.

**Done when:** the type class exists and its handler is callable without a request.

## 4. Register in `ready()`

`ArabaseConfig.ready()` in `backend/src/arabase/apps.py` is the only place a
backend registration happens. Append to it:

```python
from arabase.<feature>.<thing>_types import MyThingType
from jadawel.contrib.<app>.<area>.registries import thing_type_registry

thing_type_registry.register(MyThingType())
```

Keep the imports **inside** `ready()`. Module-level imports here run before the
app registry is populated and fail at boot.

**Done when:**

```bash
just b manage shell -c "from jadawel.contrib.database.views.registries import view_type_registry; print(view_type_registry.get_all())"
```

lists your type (substituting your own registry).

## 5. Frontend

Mirror the backend under `web-frontend/modules/arabase/<feature>/` with
`components/`, `store/`, `services/`.

1. **The type class** extends core's counterpart and returns the **exact backend
   type string** from its static `getType()`. A mismatch here fails silently —
   the type is registered on both sides and never resolves.
2. **HTTP calls go in `services/`.** Stores call services; components call stores.
3. **Register in `registryPlugin.js`**, not `plugin.js`. `plugin.js` is app-wide
   behaviour that runs early; `registryPlugin.js` declares `dependsOn` for the
   modules whose namespaces it extends, which is why registrations belong there:

```js
$registry.register('view', new MyThingType(context))
```

4. **Register any store** through the guard the file already uses:

```js
if (!$store.hasModule('view/my_thing')) {
  $store.registerModuleNuxtSafe('view/my_thing', myThingStore)
}
```

**Done when:** the type appears in the UI and its store is mounted.

## 6. Strings in both locales

Add every user-facing string to **both** `web-frontend/modules/arabase/locales/en.json`
and `ar.json`.

Namespace keys under the fork's own top-level key (`myThingType.name`), not into
a core module's namespace — extending a core namespace from here depends on how
i18n merges module messages and conflicts on every upstream merge.

Take Arabic wording from `docs/GLOSSARY_AR.md`, and add a new recurring term
there before using it. Placeholders (`{name}`), message links (`@:action.save`),
Latin technical tokens and Western digits stay verbatim.

Style with CSS logical properties (`margin-inline-start`, `inset-inline-end`) —
they are a hard lint error under `modules/arabase/`.

**Done when:** `cd web-frontend && yarn locale:check` passes. The script runs
strict; one missing Arabic key fails it, and fails CI.

## 7. Tests

- Backend: `backend/tests/arabase/test_<feature>.py`. Follow the patterns in the
  `write-backend-unit-test` skill.
- Frontend: a targeted Vitest test for component or store behaviour, per the
  `write-frontend-unit-test` skill.

Cover the type's registration and its behaviour, not just the happy-path view.

## 8. Gates

Run all four. Two of them guard the structure rather than the behaviour and are
the ones that catch a plugin wired in wrong:

```bash
just b test -n=auto                        # backend suite
just b test tests/arabase -q               # fork hygiene
cd web-frontend && yarn locale:check       # Arabic parity, strict
just lint
```

**Done when:** all four pass and the step 2 `git status` check is still clean.

## Standalone plugins

Everything above is fork code shipped in the repository — the right answer for
essentially all work. A plugin that must install into a running deployment from
outside the image is a different artifact with its own on-disk contract —
manifest, three lifecycle hooks, installer flags: see
[STANDALONE.md](STANDALONE.md).

Baserow's upstream plugin docs describe that same contract under `baserow_*`
names, and two of their claims do not hold here: they document a **Nuxt 2**
module where this fork runs Nuxt 3, and their plugin boilerplate is stale
("Baserow 2.0.6 and lower"). Read `deploy/plugins/*.sh` in this repository
rather than trusting an upstream page.
