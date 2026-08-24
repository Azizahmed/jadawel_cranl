import {
  applyInterfaceTheme,
  getInterfaceThemeSurfaces,
  INTERFACE_THEMES,
  mixWithWhite,
} from '@jadawel/modules/core/utils/interfaceThemes'

/** WCAG relative luminance, for asserting a border is actually visible. */
const luminance = (hex) => {
  const channels = [0, 2, 4].map((offset) => {
    const value =
      Number.parseInt(hex.replace('#', '').slice(offset, offset + 2), 16) / 255
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

const contrast = (a, b) => {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (light + 0.05) / (dark + 0.05)
}

describe('interface themes', () => {
  test('contains six complete color palettes in the requested order', () => {
    expect(INTERFACE_THEMES).toHaveLength(6)
    expect(INTERFACE_THEMES.map(({ id }) => id)).toEqual([
      'sage',
      'white',
      'gray',
      'blue',
      'rose',
      'amber',
    ])
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

  test('derives themed chrome and a fixed white table workspace', () => {
    expect(getInterfaceThemeSurfaces(INTERFACE_THEMES[0].colors)).toEqual({
      '--jadawel-app-background': '#f5faf7',
      '--jadawel-header-background': '#f0f7f3',
      '--jadawel-sidebar-background': '#f3f8f5',
      '--jadawel-content-background': '#fcfdfc',
      '--jadawel-raised-background': '#fbfdfb',
      '--jadawel-hover-background': '#f7fbf8',
      '--jadawel-border-color': '#cfe8d9',
      '--jadawel-grid-surface': '#ffffff',
      '--jadawel-grid-line': '#e5e7eb',
    })
  })

  test('keeps the table workspace neutral for every interface color', () => {
    INTERFACE_THEMES.forEach(({ colors }) => {
      const surfaces = getInterfaceThemeSurfaces(colors)

      expect(surfaces['--jadawel-grid-surface']).toBe('#ffffff')
      expect(surfaces['--jadawel-grid-line']).toBe('#e5e7eb')
    })
  })

  test('every theme keeps its chrome distinguishable', () => {
    // The surfaces are derived by mixing towards white, so a palette that is
    // already near-white has nowhere to travel and collapses all of them onto
    // one colour — which is what made every border, sidebar edge and grid line
    // vanish on the white theme. A theme in that position states its surfaces
    // instead, and this is the property that has to hold either way.
    INTERFACE_THEMES.forEach((theme) => {
      const surfaces = getInterfaceThemeSurfaces(theme.colors, theme.surfaces)

      expect(surfaces['--jadawel-app-background']).not.toBe(
        surfaces['--jadawel-header-background']
      )
      expect(
        contrast(surfaces['--jadawel-border-color'], '#ffffff')
      ).toBeGreaterThan(1.1)
    })
  })

  test('a theme can state its surfaces instead of deriving them', () => {
    const white = INTERFACE_THEMES.find(({ id }) => id === 'white')
    const surfaces = getInterfaceThemeSurfaces(white.colors, white.surfaces)

    expect(surfaces['--jadawel-border-color']).toBe('#e7e9ec')
    // The overrides must not drop the neutral table canvas the derivation sets.
    expect(surfaces['--jadawel-grid-surface']).toBe('#ffffff')
    expect(surfaces['--jadawel-grid-line']).toBe('#e5e7eb')
  })

  test('falls back to sage for an unknown theme', () => {
    const root = document.createElement('div')

    expect(applyInterfaceTheme('unknown', root)).toBe('sage')
    expect(root.dataset.interfaceTheme).toBe('sage')
    expect(root.style.getPropertyValue('--jadawel-primary-500')).toBe('#278053')
    expect(root.style.getPropertyValue('--jadawel-header-background')).toBe(
      '#f0f7f3'
    )
    expect(root.style.getPropertyValue('--jadawel-grid-surface')).toBe(
      '#ffffff'
    )
    expect(root.style.getPropertyValue('--jadawel-grid-line')).toBe('#e5e7eb')
  })
})
