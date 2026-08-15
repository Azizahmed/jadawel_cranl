import { readFileSync } from 'node:fs'

// Read from disk rather than imported: Vite routes a `.scss` import through its
// CSS pipeline, so `?raw` yields an empty string for a stylesheet. Paths are
// relative to the vitest root, which is `web-frontend/`.
const read = (name) =>
  readFileSync(`modules/core/assets/scss/components/${name}`, 'utf8')

const panelStyles = read('notification_panel.scss')
const utilityStyles = read('app_utilities.scss')

/**
 * The notification panel has no positioning logic — `toggle(target)` uses the
 * target only for the click-outside handler — so which corner it opens in is
 * decided entirely by CSS.
 *
 * Upstream put the bell in the sidebar and anchored the panel just past the
 * sidebar's edge. This fork moved the workspace utilities to the top inline-end
 * corner, which left the panel opening against the opposite edge of the screen
 * from the control that opens it: in Arabic the bell is top-left and the panel
 * appeared on the right.
 *
 * Asserted against the source because a global stylesheet is not applied to a
 * mounted component under jsdom, so there is no computed style to read.
 */
describe('notification panel anchoring', () => {
  const anchorSideOf = (source, selector) => {
    const block = source.slice(source.indexOf(selector))
    const start = block.search(/^\s*inset-inline-start:/m)
    const end = block.search(/^\s*inset-inline-end:/m)
    const stop = block.indexOf('}')

    const within = (index) => index !== -1 && index < stop
    if (within(start)) return 'start'
    if (within(end)) return 'end'
    return null
  }

  test('the panel opens on the same inline side as the bell', () => {
    const utilities = anchorSideOf(utilityStyles, '.app-utilities {')
    const panel = anchorSideOf(panelStyles, '.notification-panel {')

    expect(utilities).not.toBeNull()
    expect(panel).toBe(utilities)
  })

  test('the panel is positioned with logical insets, not physical ones', () => {
    const block = panelStyles.slice(panelStyles.indexOf('.notification-panel {'))
    const rules = block.slice(0, block.indexOf('}'))

    // A physical `left`/`right` here would pin the panel to one side of the
    // screen regardless of direction, which is the bug in a different shape.
    expect(rules).not.toMatch(/^\s*(left|right):/m)
  })
})
