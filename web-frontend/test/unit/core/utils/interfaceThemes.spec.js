import {
  applyInterfaceTheme,
  getInterfaceThemeSurfaces,
  INTERFACE_THEMES,
  mixWithWhite,
} from '@jadawel/modules/core/utils/interfaceThemes'

describe('interface themes', () => {
  test('contains six complete color palettes', () => {
    expect(INTERFACE_THEMES).toHaveLength(6)
    INTERFACE_THEMES.forEach((theme) => {
      expect(Object.keys(theme.colors)).toEqual([
        '100',
        '200',
        '300',
        '400',
        '500',
        '600',
        '700',
        '800',
        '900',
      ])
    })
  })

  test('lightens the grid colors by fifty percent', () => {
    expect(mixWithWhite('#dbeee3')).toBe('#edf7f1')
  })

  test('derives coordinated surfaces for the whole application', () => {
    expect(getInterfaceThemeSurfaces(INTERFACE_THEMES[0].colors)).toEqual({
      '--jadawel-app-background': '#f5faf7',
      '--jadawel-header-background': '#f0f7f3',
      '--jadawel-sidebar-background': '#f3f8f5',
      '--jadawel-content-background': '#fcfdfc',
      '--jadawel-raised-background': '#fbfdfb',
      '--jadawel-hover-background': '#f7fbf8',
      '--jadawel-border-color': '#e0f1e7',
      '--jadawel-grid-surface': '#f8fbf9',
      '--jadawel-grid-line': '#edf7f1',
    })
  })

  test('falls back to sage for an unknown theme', () => {
    const root = document.createElement('div')

    expect(applyInterfaceTheme('unknown', root)).toBe('sage')
    expect(root.dataset.interfaceTheme).toBe('sage')
    expect(root.style.getPropertyValue('--jadawel-primary-500')).toBe('#278053')
    expect(root.style.getPropertyValue('--jadawel-header-background')).toBe(
      '#f0f7f3'
    )
    expect(root.style.getPropertyValue('--jadawel-grid-line')).toBe('#edf7f1')
  })
})
