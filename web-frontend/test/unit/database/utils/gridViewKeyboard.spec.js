import {
  mirrorInlineRect,
  toInlineArrowKey,
} from '@jadawel/modules/database/utils/gridViewKeyboard'

describe('grid view keyboard navigation', () => {
  test('leaves the arrow keys alone in LTR', () => {
    expect(toInlineArrowKey('ArrowLeft', false)).toBe('ArrowLeft')
    expect(toInlineArrowKey('ArrowRight', false)).toBe('ArrowRight')
  })

  test('swaps the horizontal arrows in RTL', () => {
    // The bug this guards against: ArrowLeft was mapped straight onto the
    // previous field, so in an Arabic grid the selection jumped away from the
    // arrow the user pressed.
    expect(toInlineArrowKey('ArrowLeft', true)).toBe('ArrowRight')
    expect(toInlineArrowKey('ArrowRight', true)).toBe('ArrowLeft')
  })

  test('leaves the vertical arrows alone in RTL', () => {
    // Rows stack top to bottom regardless of the writing direction.
    expect(toInlineArrowKey('ArrowUp', true)).toBe('ArrowUp')
    expect(toInlineArrowKey('ArrowDown', true)).toBe('ArrowDown')
  })

  test('passes through keys it does not own', () => {
    // Tab already means "next in reading order", so it must not be swapped.
    expect(toInlineArrowKey('Tab', true)).toBe('Tab')
    expect(toInlineArrowKey('Enter', true)).toBe('Enter')
  })

  test('leaves a scroll rectangle untouched in LTR', () => {
    expect(
      mirrorInlineRect({ elementLeft: 40, elementRight: 240 }, 800, false)
    ).toStrictEqual({ elementLeft: 40, elementRight: 240 })
  })

  test('flips a scroll rectangle across the viewport in RTL', () => {
    // A field 40px past the inline-start edge sits 40px from the right edge of
    // an 800px viewport, so it ends at x=760 and starts at x=560.
    expect(
      mirrorInlineRect({ elementLeft: 40, elementRight: 240 }, 800, true)
    ).toStrictEqual({ elementLeft: 560, elementRight: 760 })
  })

  test('keeps an off-screen field off-screen after mirroring', () => {
    // Scrolled past the viewport on the inline axis must still read as "past
    // the viewport" physically, otherwise the grid never scrolls to it.
    const offInlineEnd = mirrorInlineRect(
      { elementLeft: 820, elementRight: 1020 },
      800,
      true
    )
    expect(offInlineEnd.elementLeft).toBeLessThan(0)

    const offInlineStart = mirrorInlineRect(
      { elementLeft: -200, elementRight: 0 },
      800,
      true
    )
    expect(offInlineStart.elementRight).toBeGreaterThan(800)
  })
})
