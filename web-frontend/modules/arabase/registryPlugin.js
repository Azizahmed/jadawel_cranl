import { ChartWidgetType } from '@baserow/modules/arabase/dashboard/widgetTypes'
import { LocalBaserowGroupedAggregateRowsServiceType } from '@baserow/modules/arabase/integrations/serviceTypes'

/**
 * Registry registrations for the fork's own types.
 *
 * Separate from ./plugin.js (which only wires up direction/locale) because these
 * depend on namespaces other modules create: `dashboardWidget` is registered by
 * the dashboard plugin, and service types have to exist before a dashboard
 * renders a widget whose data source uses one.
 */
export default defineNuxtPlugin({
  name: 'arabase-registry',
  dependsOn: ['core', 'store', 'dashboard'],
  setup(nuxtApp) {
    const { $registry } = nuxtApp
    const context = { app: nuxtApp }

    $registry.register(
      'service',
      new LocalBaserowGroupedAggregateRowsServiceType(context)
    )
    $registry.register('dashboardWidget', new ChartWidgetType(context))
  },
})
