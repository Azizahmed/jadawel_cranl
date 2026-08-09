import { JadawelPlugin } from '@jadawel/modules/core/plugins'
import ShareDashboardLink from '@jadawel/modules/arabase/dashboard/components/ShareDashboardLink'

/**
 * Fork-level UI that core modules render through their plugin hooks. Using the
 * hook keeps the dependency pointing the right way: the dashboard module never
 * imports anything from `arabase`.
 */
export class ArabasePlugin extends JadawelPlugin {
  static getType() {
    return 'arabase'
  }

  getAdditionalDashboardHeaderComponents(dashboard) {
    // The endpoints behind it all require `application.update`; rendering the
    // menu for a viewer would only produce a permission error.
    if (
      !this.app.$hasPermission(
        'application.update',
        dashboard,
        dashboard.workspace.id
      )
    ) {
      return []
    }
    return [ShareDashboardLink]
  }
}
