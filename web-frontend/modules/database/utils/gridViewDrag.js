/**
 * Converts a physical pointer X coordinate into a distance from the inline-start
 * edge of an element. Inline-start is left in LTR and right in RTL.
 */
export function getInlinePointerPosition(clientX, rect, rtl = false) {
  return rtl ? rect.right - clientX : clientX - rect.left
}

/**
 * Returns pointer movement in logical reading order. A positive value moves
 * toward inline-end in both LTR and RTL.
 */
export function getInlinePointerDelta(clientX, startX, rtl = false) {
  return rtl ? startX - clientX : clientX - startX
}

/**
 * Browsers expose RTL scrollLeft as a negative value while LTR is positive.
 * Drag calculations only need the positive distance from inline-start.
 */
export function getInlineScrollOffset(scrollLeft, rtl = false) {
  return rtl ? Math.abs(scrollLeft) : scrollLeft
}

/**
 * GridView.scroll consumes a physical scrollLeft delta. Convert a logical
 * inline delta back to that physical value before emitting it.
 */
export function getPhysicalScrollDelta(inlineDelta, rtl = false) {
  return rtl ? -inlineDelta : inlineDelta
}

/**
 * Finds the insertion point for a normalized inline pointer position.
 */
export function getFieldDragTarget(
  inlinePosition,
  fields,
  offset,
  getFieldWidth
) {
  let inlineStart = offset

  for (let i = 0; i < fields.length; i++) {
    const width = getFieldWidth(fields[i])
    const nextWidth =
      i + 1 < fields.length ? getFieldWidth(fields[i + 1]) : width
    const startHalf = inlineStart + Math.floor(width / 2)
    const endHalf = inlineStart + width + Math.floor(nextWidth / 2)

    if (i === 0 && inlinePosition < startHalf) {
      return { fieldId: 0, inlineStart: offset }
    }

    if (inlinePosition > startHalf && inlinePosition < endHalf) {
      return { fieldId: fields[i].id, inlineStart: inlineStart + width }
    }

    inlineStart += width
  }

  return null
}
