/**
 * Fork-owned test helper.
 *
 * The arabase module registers its row-coloring decorators and value
 * providers app-wide (modules/arabase/registryPlugin.js), so they show up in
 * every registry the test environment builds. Upstream specs whose snapshots
 * enumerate the whole toolbar or decorator registry assert a core-only
 * registry and would capture the fork's items.
 *
 * `scopeOutArabaseRowColoring(registry)` unregisters the four fork types for
 * the duration of a spec; the nuxt test environment is rebuilt per spec file,
 * so nothing needs to be restored afterwards. The feature itself stays
 * registered everywhere else and has its own coverage in
 * test/unit/arabase/rowColoring.spec.js.
 */

const ARABASE_VIEW_DECORATOR_TYPES = [
  'background_color',
  'left_border_color',
]

const ARABASE_DECORATOR_VALUE_PROVIDER_TYPES = [
  'single_select_color',
  'conditional_color',
]

export function scopeOutArabaseRowColoring(registry) {
  for (const type of ARABASE_VIEW_DECORATOR_TYPES) {
    try {
      registry.unregister('viewDecorator', type)
    } catch {
      /* empty */
    }
  }
  for (const type of ARABASE_DECORATOR_VALUE_PROVIDER_TYPES) {
    try {
      registry.unregister('decoratorValueProvider', type)
    } catch {
      /* empty */
    }
  }
}
