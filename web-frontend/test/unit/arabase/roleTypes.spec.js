import { ViewerRoleType } from '@jadawel/modules/arabase/roleTypes'

const app = { $i18n: { t: (key) => key } }

describe('ViewerRoleType', () => {
  const role = new ViewerRoleType({ app })

  test('uses the workspace membership role uid the backend enforces', () => {
    expect(role.getUid()).toBe('VIEWER')
    expect(role.getType()).toBe('viewer')
  })

  test('resolves its name and description through i18n', () => {
    expect(role.getName()).toBe('roles.viewer.name')
    expect(role.getDescription()).toBe('roles.viewer.description')
  })

  test('is selectable wherever the role registry is consulted', () => {
    expect(role.isVisible()).toBe(true)
    expect(role.isDeactivated()).toBe(false)
    expect(role.showIsBillable()).toBe(false)
    expect(role.getDeactivatedClickModal()).toBe(null)
  })
})
