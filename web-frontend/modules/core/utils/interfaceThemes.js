export const INTERFACE_THEME_STORAGE_KEY = 'jadawel.interfaceTheme'
export const DEFAULT_INTERFACE_THEME = 'sage'

export const INTERFACE_THEMES = [
  {
    id: 'sage',
    colors: {
      100: '#f0f7f3',
      200: '#dbeee3',
      300: '#b5dcc5',
      400: '#55a97d',
      500: '#278053',
      600: '#1b5a3a',
      700: '#15472e',
      800: '#103522',
      900: '#06170e',
    },
  },
  {
    id: 'blue',
    colors: {
      100: '#f0f4fc',
      200: '#dae4fd',
      300: '#acc8f8',
      400: '#5190ef',
      500: '#275d9f',
      600: '#1d508b',
      700: '#124377',
      800: '#0d355e',
      900: '#05223f',
    },
  },
  {
    id: 'purple',
    colors: {
      100: '#f9f1fd',
      200: '#efdcfb',
      300: '#dfb9f7',
      400: '#af50ea',
      500: '#7b38a4',
      600: '#69308c',
      700: '#582875',
      800: '#46205e',
      900: '#301540',
    },
  },
  {
    id: 'rose',
    colors: {
      100: '#fdf3f9',
      200: '#f9e1ef',
      300: '#f3c3df',
      400: '#e26ab0',
      500: '#88406a',
      600: '#713558',
      700: '#5a2a46',
      800: '#421d33',
      900: '#2a1020',
    },
  },
  {
    id: 'amber',
    colors: {
      100: '#fffbf0',
      200: '#fff4da',
      300: '#ffe9b4',
      400: '#ffc744',
      500: '#806422',
      600: '#66501b',
      700: '#513e14',
      800: '#3c2d0e',
      900: '#271c08',
    },
  },
  {
    id: 'teal',
    colors: {
      100: '#ecfbfd',
      200: '#cff5fa',
      300: '#a0ebf5',
      400: '#11cce5',
      500: '#0a7a89',
      600: '#096673',
      700: '#07525c',
      800: '#053d45',
      900: '#03282d',
    },
  },
]

export const mixWithWhite = (hexColor, amount = 0.5) => {
  const value = hexColor.replace('#', '')
  const channels = [0, 2, 4].map((offset) =>
    Number.parseInt(value.slice(offset, offset + 2), 16)
  )
  const mixed = channels.map((channel) =>
    Math.round(channel + (255 - channel) * amount)
      .toString(16)
      .padStart(2, '0')
  )
  return `#${mixed.join('')}`
}

export const getInterfaceThemeSurfaces = (colors) => ({
  '--jadawel-app-background': mixWithWhite(colors[100], 0.35),
  '--jadawel-header-background': colors[100],
  '--jadawel-sidebar-background': mixWithWhite(colors[100], 0.18),
  '--jadawel-content-background': mixWithWhite(colors[100], 0.78),
  '--jadawel-raised-background': mixWithWhite(colors[100], 0.7),
  '--jadawel-hover-background': mixWithWhite(colors[100], 0.45),
  '--jadawel-border-color': mixWithWhite(colors[200], 0.15),
  '--jadawel-grid-surface': mixWithWhite(colors[100]),
  '--jadawel-grid-line': mixWithWhite(colors[200]),
})

export const applyInterfaceTheme = (
  themeId,
  root = globalThis.document?.documentElement
) => {
  const theme =
    INTERFACE_THEMES.find(({ id }) => id === themeId) || INTERFACE_THEMES[0]

  if (!root) {
    return theme.id
  }

  Object.entries(theme.colors).forEach(([step, color]) => {
    root.style.setProperty(`--jadawel-primary-${step}`, color)
  })
  Object.entries(getInterfaceThemeSurfaces(theme.colors)).forEach(
    ([property, color]) => root.style.setProperty(property, color)
  )
  root.dataset.interfaceTheme = theme.id

  return theme.id
}
