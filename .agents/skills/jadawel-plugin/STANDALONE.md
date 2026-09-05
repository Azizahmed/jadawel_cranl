# Standalone Installable Plugins

For a plugin that installs into a running deployment from outside the image —
third-party or per-customer code the core team never ships. Fork code under
`arabase/` is the right answer for everything else; reach here only when
something genuinely must ship separately from the repository.

The reach is identical either way: an installed plugin's backend half lands in
`INSTALLED_APPS`, so its own `ready()` registers into the same seams fork code
uses. There is no privileged path around the registries.

This follows upstream Baserow's plugin contract, renamed for the fork. Where the
two differ, **this file describes what `deploy/plugins/*.sh` in this repository
actually does** — read those scripts before trusting any upstream page.

## Two things upstream's docs will mislead you on

- **Nuxt 3, not Nuxt 2.** Upstream documents a Nuxt v2 module. This fork runs
  Nuxt 3, so a plugin's `module.js` uses `defineNuxtModule` from `@nuxt/kit` and
  the `dependsOn` / `addPlugin` / `extendPages` API. Copy
  `web-frontend/modules/arabase/module.js` as the template.
- **The upstream boilerplate is stale.** `github.com/baserow/plugin-boilerplate`
  is documented as "only made for Baserow 2.0.6 and lower" and generates Nuxt 2
  code with `baserow_*` naming. Write the layout below by hand instead.

## Layout

A plugin is a folder named after the plugin, holding one or both halves:

```
<plugin_name>/
  jadawel_plugin_info.json
  backend/
    setup.py                a valid installable Python package
    src/<plugin_name>/      the Django app — folder name matches the app name
    build.sh                optional
    runtime_setup.sh        optional
    uninstall.sh            optional
  web-frontend/
    package.json            a valid node package
    modules/<plugin-name>/module.js
    build.sh
    runtime_setup.sh
    uninstall.sh
```

Naming: the plugin folder name matches the Django app name exactly; the frontend
module folder is the kebab-case form of the same name.

When distributing by URL or git, wrap the plugin folder in a `plugins/` directory
at the archive root.

## Manifest

`jadawel_plugin_info.json` sits at the plugin root. `list_plugins.sh` reads its
`description`; the rest is metadata for whoever installs the plugin:

```json
{
  "name": "",
  "version": "",
  "supported_jadawel_versions": "",
  "plugin_api_version": "0.0.1-alpha",
  "description": "",
  "author": "",
  "author_url": "",
  "url": "",
  "license": "",
  "contact": ""
}
```

## Discovery

`backend/src/jadawel/config/settings/base.py` scans the plugin directory at
settings time, before Django loads any app:

```python
JADAWEL_PLUGIN_DIR_PATH = Path(os.environ.get("JADAWEL_PLUGIN_DIR", "/jadawel/plugins"))
# any subdirectory containing a backend/ becomes an installed app
```

The frontend mirrors it: `ADDITIONAL_MODULES` is a CSV of Nuxt module paths that
`web-frontend/config/nuxt.config.base.ts` concatenates onto the base module list.

## Installing

`deploy/plugins/install_plugin.sh` takes exactly one source flag:

| Flag | Source |
|---|---|
| `-f, --folder <path>` | a local directory, usually copied into a Dockerfile |
| `-u, --url <url>` | a `.tar.gz` archive |
| `-g, --git <repo>` | a git repository |

And four modifiers:

| Flag | Effect |
|---|---|
| `--hash <hash>` | hashes the plugin contents and fails the install on mismatch — use it for anything fetched over the network |
| `-d, --dev` | installs the backend editable, for development |
| `-r, --runtime` | permits the runtime setup scripts to run; never pass it from a Dockerfile |
| `-o, --overwrite` | force re-install, re-build and re-setup over an existing plugin of the same name |

On container start, `startup_plugin_setup()` in `deploy/plugins/utils.sh`
installs every folder already in `JADAWEL_PLUGIN_DIR`, then everything listed in
`JADAWEL_PLUGIN_URLS` and `JADAWEL_PLUGIN_GIT_REPOS` (both comma-separated),
each with `--runtime`. Set `JADAWEL_DISABLE_PLUGIN_INSTALL_ON_STARTUP` to skip
all of it.

`uninstall_plugin.sh` removes a plugin and runs either half's `uninstall.sh`
while the database is still reachable, so a migration rollback works.
`list_plugins.sh` reports what is installed.

## The three hooks

| Script | Runs |
|---|---|
| `build.sh` | once, at install — during a Dockerfile build or a runtime install |
| `runtime_setup.sh` | once, on the first container start after install, and only when `--runtime` was passed |
| `uninstall.sh` | at removal, with the database still available |

Both build and runtime setup are marker-guarded, so neither repeats on restart:

```
/jadawel/container_markers/<plugin_name>.backend-built
/jadawel/container_markers/<plugin_name>.backend-runtime-setup
/jadawel/container_markers/<plugin_name>.web-frontend-built
/jadawel/container_markers/<plugin_name>.web-frontend-runtime-setup
```

Database and volume work belongs in `runtime_setup.sh` — a build-time side
effect is lost the moment the container is replaced. `--overwrite` is what
forces a marker-guarded step to run again.

All four guards test `! -f "$MARKER"` — run when the marker is absent. The
web-frontend runtime-setup guard was inverted until 2026-09-05, so a
`web-frontend/runtime_setup.sh` never fired on a fresh install; if you are
reading this against an older image, that is why. `deploy/plugins/test_marker_guards.sh`
asserts all four guards and fails if one is re-inverted.

## Persistence

In the all-in-one image `JADAWEL_PLUGIN_DIR` is `/jadawel/data/plugins` — inside
the data volume — so installed plugins survive a container replacement. Any
single-container deployment needs the same, or plugins vanish on redeploy.
