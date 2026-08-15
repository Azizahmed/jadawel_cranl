import { AdminType } from '@jadawel/modules/core/adminTypes'

export class BackupAdminType extends AdminType {
  static getType() {
    return 'backup'
  }

  getIconClass() {
    return 'iconoir-database-backup'
  }

  getName() {
    const { $i18n: i18n } = this.app
    return i18n.t('adminType.backup')
  }

  getRouteName() {
    return 'admin-backup'
  }

  getOrder() {
    // Just after Health: both answer "is this deployment all right", and an
    // operator checking one is usually about to check the other.
    return 10100
  }
}
