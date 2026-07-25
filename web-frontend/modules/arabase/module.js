import { defineNuxtModule, addPlugin, createResolver } from 'nuxt/kit'

/**
 * Arabase (Jadawel) Nuxt module — the home for our additive frontend code.
 *
 * Kept as a separate module (rather than editing web-frontend/modules/core/*)
 * so upstream merges stay cheap. RTL/Arabic-first behaviour, the `ar` locale,
 * custom field-type components (Hijri date), and enterprise-equivalent UI
 * (SSO / audit / RBAC screens) are wired up here as each phase lands.
 *
 * Direct edits to core components that are unavoidable (e.g. deep RTL work in
 * the grid) are tracked in PATCHES.md, not hidden here.
 */
export default defineNuxtModule({
  meta: {
    name: 'arabase-module',
  },
  dependsOn: ['core'],
  setup(options, nuxt) {
    const { resolve } = createResolver(import.meta.url)

    addPlugin({
      src: resolve('./plugin.js'),
    })

    // Global RTL / Arabic-first stylesheet. Pushed after core's default.scss
    // (core registers in its own module setup) so it can layer on top. See 1.2.
    nuxt.options.css.push(resolve('./assets/scss/arabase.scss'))

    // The `ar` locale itself is activated via config/locales.js (shared list) and
    // the existing per-module langDirs; arabase does not register its own langDir
    // yet because it has no user-facing strings of its own. When it does, add a
    // nuxt.hook('i18n:registerModule', ...) here with an ./locales dir.
  },
})
