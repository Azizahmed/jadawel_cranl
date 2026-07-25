import {
  getFieldDragTarget,
  getInlinePointerDelta,
  getInlinePointerPosition,
  getInlineScrollOffset,
  getPhysicalScrollDelta,
} from '@baserow/modules/database/utils/gridViewDrag'

describe('grid view field dragging coordinates', () => {
  const rect = { left: 100, right: 600 }
  const fields = [{ id: 1 }, { id: 2 }, { id: 3 }]
  const getFieldWidth = () => 100

  test('normalizes pointer coordinates from inline-start', () => {
    expect(getInlinePointerPosition(230, rect, false)).toBe(130)
    expect(getInlinePointerPosition(470, rect, true)).toBe(130)
  })

  test('normalizes movement direction in RTL', () => {
    expect(getInlinePointerDelta(240, 200, false)).toBe(40)
    expect(getInlinePointerDelta(160, 200, true)).toBe(40)
  })

  test('normalizes RTL scrolling and emitted scroll deltas', () => {
    expect(getInlineScrollOffset(-120, true)).toBe(120)
    expect(getInlineScrollOffset(120, false)).toBe(120)
    expect(getPhysicalScrollDelta(5, true)).toBe(-5)
    expect(getPhysicalScrollDelta(5, false)).toBe(5)
  })

  test('moving physically left advances to the next RTL field', () => {
    const firstPosition = getInlinePointerPosition(470, rect, true)
    const secondPosition = getInlinePointerPosition(370, rect, true)

    expect(
      getFieldDragTarget(firstPosition, fields, 0, getFieldWidth)
    ).toStrictEqual({ fieldId: 1, inlineStart: 100 })
    expect(
      getFieldDragTarget(secondPosition, fields, 0, getFieldWidth)
    ).toStrictEqual({ fieldId: 2, inlineStart: 200 })
  })
})
