import {
  ChartWidgetType,
  ProgressWidgetType,
  RecordsListWidgetType,
  UpcomingDatesWidgetType,
} from '@jadawel/modules/arabase/dashboard/widgetTypes'
import {
  LocalJadawelGroupedAggregateRowsServiceType,
  LocalJadawelUpcomingRowsServiceType,
} from '@jadawel/modules/arabase/integrations/serviceTypes'

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
      new LocalJadawelGroupedAggregateRowsServiceType(context)
    )
    $registry.register(
      'service',
      new LocalJadawelUpcomingRowsServiceType(context)
    )

    $registry.register('dashboardWidget', new ChartWidgetType(context))
    $registry.register('dashboardWidget', new RecordsListWidgetType(context))
    $registry.register('dashboardWidget', new ProgressWidgetType(context))
    $registry.register('dashboardWidget', new UpcomingDatesWidgetType(context))

    // Generative AI keys are not configurable per workspace in Jadawel: the
    // provider credentials are an instance-level concern (env vars) or an
    // integration-level one (the AI integration's own `ai_settings`). Dropping
    // the tab here keeps the core component untouched while removing the entry
    // point; the matching API route is removed in the backend (see PATCHES.md).
    $registry.unregister('workspaceSettings', 'generative-ai')
  },
})
