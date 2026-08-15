import { calculateTempOrder } from '@jadawel/modules/core/utils/order'

/**
 * Pure computations behind the dashboard grid board (wedage_kimi_plan.md): where
 * a dragged widget lands in the order, and which fractional `order` value that
 * position maps to. Kept separate from the directive so they are unit-testable.
 */

/**
 * Computes the index (in DOM/reading order) before which a dragged item should
 * be inserted, based on the cursor position relative to each item's midlines.
 * Unlike core's Y-axis-only sortable, this looks at both axes so it works in a
 * multi-column grid: the cursor lands before an item when it is above the
 * item's row band, or inside the band but before the item's inline midline
 * (left of it in LTR, right of it in RTL).
 *
 * @param rects   The item rects in DOM (reading) order.
 * @param clientX Cursor position.
 * @param clientY Cursor position.
 * @param rtl     Whether the document is right-to-left.
 * @returns The index to insert before, or `rects.length` for the end.
 */
export function findGridDropIndex(rects, clientX, clientY, rtl = false) {
  // The board is laid out with `grid-auto-flow: dense`, which backfills gaps —
  // so a narrow widget later in the DOM can render *before* a wider one that
  // precedes it. Scanning in DOM order then compares the cursor against boxes
  // that are not in the order the reader sees, and the computed index lands one
  // slot out. Walking in visual order and reporting the DOM index of whatever
  // is found keeps both halves honest.
  const ordered = rects
    .map((rect, index) => ({ rect, index }))
    .sort((a, b) => {
      if (a.rect.top !== b.rect.top) {
        return a.rect.top - b.rect.top
      }
      return rtl ? b.rect.left - a.rect.left : a.rect.left - b.rect.left
    })

  for (const { rect, index } of ordered) {
    const midX = rect.left + rect.width / 2
    const bottom = rect.top + rect.height
    const inRowBand = clientY >= rect.top && clientY < bottom
    const beforeInRow = rtl ? clientX > midX : clientX < midX
    if (clientY < rect.top || (inRowBand && beforeInRow)) {
      return index
    }
  }
  return rects.length
}

/**
 * Computes the fractional `order` (Decimal string) a widget gets when dropped at
 * `newIndex`, as the midpoint between its two new neighbours. `sortedWidgets` is
 * the order-sorted widget list with the moved widget already spliced into its
 * new position. Approximates what the backend computes, exactly like
 * `calculateTempOrder` does for other reorder flows.
 */
export function computeWidgetOrderUpdate(sortedWidgets, movedId, newIndex) {
  const remaining = sortedWidgets.filter((widget) => widget.id !== movedId)
  const before = newIndex > 0 ? remaining[newIndex - 1] : null
  const after = newIndex < remaining.length ? remaining[newIndex] : null
  return calculateTempOrder(
    before ? before.order : null,
    after ? after.order : null
  )
}
