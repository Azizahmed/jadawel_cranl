import { Registerable } from '@jadawel/modules/core/registry'

/**
 * The fork's workspace VIEWER role (#36).
 *
 * Core only ships the ADMIN and MEMBER role types (`modules/database/
 * roleTypes.js`), and its `RoleType` base class is not exported, so the
 * default-method surface is reproduced here. Registering this type makes
 * "Viewer" appear wherever the role registry is consulted: the invite form
 * and the members table role dropdown both read `workspace._.roles`, which
 * the roles service builds from `$registry.getAll('roles')`.
 *
 * The role is enforced server-side by the additive `viewer_role` permission
 * manager (see `backend/src/arabase/permissions/viewer_role.py`): a viewer
 * sees everything a member sees — including row colors — but view
 * configuration (colors, filters, sorts, groupings) is read-only.
 */

class ForkRoleType extends Registerable {
  // Indicates whether to show the role as billable/non-billable or show
  // nothing.
  showIsBillable(workspaceId) {
    return false
  }

  // Indicates whether the role is billable.
  getIsBillable() {
    return false
  }

  // Indicates whether the role should be visible in the list.
  isVisible(workspaceId) {
    return true
  }

  // Indicates whether the role is visible, but in a deactivated state.
  isDeactivated(workspaceId) {
    return false
  }

  // The modal component that must be shown when a deactivated role is
  // clicked.
  getDeactivatedClickModal(workspaceId) {
    return null
  }

  // `null` equals all scope types.
  get allowedScopeTypes() {
    return null
  }

  // `null` equals all subject types.
  get allowedSubjectTypes() {
    return null
  }
}

export class ViewerRoleType extends ForkRoleType {
  static getType() {
    return 'viewer'
  }

  getUid() {
    return 'VIEWER'
  }

  getName() {
    const { $i18n: i18n } = this.app
    return i18n.t('roles.viewer.name')
  }

  getDescription() {
    const { $i18n: i18n } = this.app
    return i18n.t('roles.viewer.description')
  }
}
