import { TestApp } from '@jadawel/test/helpers/testApp'
import AppUtilities from '@jadawel/modules/core/components/AppUtilities'
import {
  getInterfaceThemeSurfaces,
  INTERFACE_THEMES,
  INTERFACE_THEME_STORAGE_KEY,
} from '@jadawel/modules/core/utils/interfaceThemes'

const ContextStub = {
  name: 'Context',
  emits: ['hidden', 'shown'],
  methods: {
    toggle() {
      this.$emit('shown')
    },
    hide() {
      this.$emit('hidden')
    },
  },
  template: '<div class="context"><slot /></div>',
}

const EmptyOverlayStub = {
  methods: {
    show() {},
    toggle() {},
  },
  template: '<div />',
}

describe('AppUtilities component', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
    localStorage.removeItem(INTERFACE_THEME_STORAGE_KEY)
  })

  afterEach(async () => {
    INTERFACE_THEMES.forEach(({ colors }) => {
      Object.keys(colors).forEach((step) => {
        document.documentElement.style.removeProperty(
          `--jadawel-primary-${step}`
        )
      })
    })
    document.documentElement.style.removeProperty('--jadawel-grid-surface')
    document.documentElement.style.removeProperty('--jadawel-grid-line')
    Object.keys(getInterfaceThemeSurfaces(INTERFACE_THEMES[0].colors)).forEach(
      (property) => document.documentElement.style.removeProperty(property)
    )
    delete document.documentElement.dataset.interfaceTheme
    localStorage.removeItem(INTERFACE_THEME_STORAGE_KEY)
    await testApp.afterEach()
  })

  test('groups workspace services and exposes six interface colors', async () => {
    const wrapper = await testApp.mount(AppUtilities, {
      props: {
        workspace: { id: 1, users: [{ id: 1 }, { id: 2 }] },
      },
      global: {
        mocks: {
          $hasPermission: () => true,
        },
        stubs: {
          Context: ContextStub,
          NotificationPanel: EmptyOverlayStub,
          WorkspaceMemberInviteModal: EmptyOverlayStub,
          TrashModal: EmptyOverlayStub,
          BadgeCounter: true,
        },
      },
    })

    expect(wrapper.findAll('.app-utilities__item')).toHaveLength(2)
    expect(wrapper.find('.app-utilities__item .iconoir-bell').exists()).toBe(
      true
    )
    expect(
      wrapper.find('.app-utilities__item .iconoir-view-grid').exists()
    ).toBe(true)
    expect(wrapper.find('.context__menu .iconoir-group').exists()).toBe(true)
    expect(wrapper.find('.context__menu .iconoir-add-user').exists()).toBe(
      true
    )
    expect(wrapper.find('.context__menu .iconoir-bin').exists()).toBe(true)

    const colorOptions = wrapper.findAll('.app-utilities__theme-option')
    expect(colorOptions).toHaveLength(6)
    expect(colorOptions[0].attributes('aria-checked')).toBe('true')

    await colorOptions[1].trigger('click')

    expect(colorOptions[1].attributes('aria-checked')).toBe('true')
    expect(document.documentElement.dataset.interfaceTheme).toBe('blue')
    expect(
      document.documentElement.style.getPropertyValue('--jadawel-primary-500')
    ).toBe('#275d9f')
    expect(
      document.documentElement.style.getPropertyValue(
        '--jadawel-header-background'
      )
    ).toBe('#f0f4fc')
    expect(
      document.documentElement.style.getPropertyValue(
        '--jadawel-app-background'
      )
    ).toBe('#f5f8fd')
    expect(localStorage.getItem(INTERFACE_THEME_STORAGE_KEY)).toBe('blue')
  })
})
