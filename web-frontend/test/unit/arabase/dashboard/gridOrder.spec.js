import {
  computeWidgetOrderUpdate,
  findGridDropIndex,
} from '@jadawel/modules/arabase/utils/gridOrder'

describe('computeWidgetOrderUpdate', () => {
  const widgets = [
    { id: 1, order: '1' },
    { id: 2, order: '2' },
    { id: 3, order: '3' },
    { id: 4, order: '4' },
  ]

  test('move forward lands on the midpoint of the two new neighbours', () => {
    // 1 moves after 3: [2, 3, 1, 4]
    const sorted = [widgets[1], widgets[2], widgets[0], widgets[3]]
    expect(computeWidgetOrderUpdate(sorted, 1, 2)).toBe('3.5')
  })

  test('move back lands on the midpoint of the two new neighbours', () => {
    // 4 moves before 2: [1, 4, 2, 3]
    const sorted = [widgets[0], widgets[3], widgets[1], widgets[2]]
    expect(computeWidgetOrderUpdate(sorted, 4, 1)).toBe('1.5')
  })

  test('drop at end is the last order plus one', () => {
    // 2 moves to the end: [1, 3, 4, 2]
    const sorted = [widgets[0], widgets[2], widgets[3], widgets[1]]
    expect(computeWidgetOrderUpdate(sorted, 2, 3)).toBe('5')
  })

  test('drop at start is the first order halved', () => {
    // 3 moves to the start: [3, 1, 2, 4]
    const sorted = [widgets[2], widgets[0], widgets[1], widgets[3]]
    expect(computeWidgetOrderUpdate(sorted, 3, 0)).toBe('0.5')
  })

  test('decimal orders keep their precision', () => {
    const sorted = [
      { id: 1, order: '1.00000000000000000000' },
      { id: 2, order: '1.50000000000000000000' },
    ]
    // 2 moves before 1: the midpoint of nothing and 1.
    expect(computeWidgetOrderUpdate(sorted, 2, 0)).toBe('0.5')
  })
})

describe('findGridDropIndex', () => {
  // A 3-column grid of 100x160 cells, 16px gaps: A B C on row one, D below A.
  const ltrRects = [
    { left: 0, top: 0, width: 100, height: 160 },
    { left: 116, top: 0, width: 100, height: 160 },
    { left: 232, top: 0, width: 100, height: 160 },
    { left: 0, top: 176, width: 100, height: 160 },
  ]
  // The same grid in RTL: the reading order runs right to left.
  const rtlRects = [
    { left: 232, top: 0, width: 100, height: 160 },
    { left: 116, top: 0, width: 100, height: 160 },
    { left: 0, top: 0, width: 100, height: 160 },
    { left: 232, top: 176, width: 100, height: 160 },
  ]

  test('cursor before an item in its row band lands before that item', () => {
    // Inside B's band, left of B's midline (166).
    expect(findGridDropIndex(ltrRects, 130, 80)).toBe(1)
  })

  test('cursor past an item moves on to the next row', () => {
    // Right of C's midline in row one: lands before D, the next item.
    expect(findGridDropIndex(ltrRects, 300, 80)).toBe(3)
  })

  test('cursor below every item lands at the end', () => {
    expect(findGridDropIndex(ltrRects, 300, 400)).toBe(4)
  })

  test('cursor above the first row lands at the start', () => {
    expect(findGridDropIndex(ltrRects, 300, -20)).toBe(0)
  })

  test('drop on a different column targets that column', () => {
    // Directly on A (left column) while dragging another widget.
    expect(findGridDropIndex(ltrRects, 30, 80)).toBe(0)
  })

  test('in RTL before means right of the midline', () => {
    // Inside B's band (x 116-216, midline 166): right of the midline is
    // earlier in right-to-left reading order.
    expect(findGridDropIndex(rtlRects, 200, 80, true)).toBe(1)
    expect(findGridDropIndex(rtlRects, 130, 80, true)).toBe(2)
  })
})
