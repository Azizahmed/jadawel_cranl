/**
 * Arrow keys name a physical direction, but grid navigation moves along the
 * field order, and that is an inline axis: it runs left to right in LTR and
 * right to left in RTL. Mapping ArrowLeft straight onto "previous field" is
 * therefore only correct in LTR — in an Arabic grid the previous field sits to
 * the right of the selected cell, so the arrows appear to work in reverse.
 *
 * Swapping the key before it is mapped to a direction keeps every caller
 * working in field order and leaves the LTR path untouched.
 *
 * Vertical arrows are returned as-is: rows stack top to bottom in both
 * directions. Tab is deliberately not routed through here — it already means
 * "next in reading order", which is the field order, so it needs no flip.
 */
export function toInlineArrowKey(key, rtl = false) {
  if (!rtl) {
    return key
  }

  if (key === 'ArrowLeft') {
    return 'ArrowRight'
  }

  if (key === 'ArrowRight') {
    return 'ArrowLeft'
  }

  return key
}

/**
 * Mirrors a viewport-relative horizontal rectangle across its container.
 *
 * Scroll-into-view offsets for a field are accumulated in field order, which
 * gives a position along the inline axis. `scrollToElementRect` expects
 * physical offsets from the container's left edge. The two are the same thing
 * in LTR; in RTL the inline axis starts at the right edge, so the rectangle has
 * to be flipped across the container before it is used.
 */
export function mirrorInlineRect(
  { elementLeft, elementRight },
  containerWidth,
  rtl = false
) {
  if (!rtl) {
    return { elementLeft, elementRight }
  }

  return {
    elementLeft: containerWidth - elementRight,
    elementRight: containerWidth - elementLeft,
  }
}
