import { JadawelPlugin } from '@jadawel/modules/core/plugins'
import DatabaseDashboardResourceLinks from '@jadawel/modules/database/components/dashboard/DatabaseDashboardResourceLinks'

export class DatabasePlugin extends JadawelPlugin {
  static getType() {
    return 'database'
  }

  getDashboardResourceLinksComponent() {
    return DatabaseDashboardResourceLinks
  }
}
