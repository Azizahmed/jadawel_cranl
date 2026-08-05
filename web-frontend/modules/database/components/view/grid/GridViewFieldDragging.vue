<template>
  <div
    v-show="dragging && moved"
    class="grid-view__field-dragging-container"
    :style="{
      insetInlineStart: clipOffset + 'px',
      insetInlineEnd: '0',
    }"
  >
    <div
      class="grid-view__field-dragging"
      :style="{
        width: draggingWidth + 'px',
        insetInlineStart: draggingInlineStart - clipOffset + 'px',
      }"
    ></div>
    <div
      class="grid-view__field-target"
      :style="{ insetInlineStart: targetInlineStart - clipOffset + 'px' }"
    ></div>
  </div>
</template>

<script>
import { notifyIf } from '@jadawel/modules/core/utils/error'
import gridViewHelpers from '@jadawel/modules/database/mixins/gridViewHelpers'
import {
  getFieldDragTarget,
  getInlinePointerDelta,
  getInlinePointerPosition,
  getInlineScrollOffset,
  getPhysicalScrollDelta,
} from '@jadawel/modules/database/utils/gridViewDrag'

export default {
  name: 'GridViewFieldDragging',
  mixins: [gridViewHelpers],
  props: {
    view: {
      type: Object,
      required: true,
    },
    fields: {
      type: Array,
      required: true,
    },
    offset: {
      type: Number,
      required: false,
      default: 0,
    },
    readOnly: {
      type: Boolean,
      required: true,
    },
    getScrollElement: {
      type: Function,
      required: true,
    },
    getScrollableElement: {
      type: Function,
      required: false,
      default: null,
    },
    frozenSectionWidth: {
      type: Number,
      required: false,
      default: 0,
    },
  },
  emits: ['scroll'],
  data() {
    return {
      // Indicates if the user is dragging a field to another position.
      dragging: false,
      // Indicates whether the user has moved the mouse more than the 3px threshold.
      moved: false,
      // The field object that is being dragged.
      field: null,
      // The id of the field where the dragged field must be placed after.
      targetFieldId: null,
      // The horizontal starting position of the mouse.
      mouseStartX: 0,
      // The vertical starting position of the mouse.
      mouseStartY: 0,
      // The horizontal scrollbar offset starting position.
      scrollStart: 0,
      // The visual inline-start position of the field at drag start.
      initialVisualInlineStart: 0,
      // The width of the dragging animation, this is equal to the width of the field.
      draggingWidth: 0,
      // The inline-start position of the dragging animation.
      draggingInlineStart: 0,
      // The inline-start position of the target insertion indicator.
      targetInlineStart: 0,
      // The inline-start offset of the clipping container. When scrolled, clips the
      // frozen area so scrolled-out positions aren't visible behind frozen fields.
      clipOffset: 0,
      // The mouse move event.
      lastMoveEvent: null,
      // Indicates if the user is auto scrolling at the moment.
      autoScrolling: false,
      // Event handler references for cleanup
      moveEvent: null,
      upEvent: null,
      keydownEvent: null,
      scrollTimeout: null,
    }
  },
  beforeUnmount() {
    this.cancel()
  },
  methods: {
    _getScrollableElement() {
      return this.getScrollableElement
        ? this.getScrollableElement()
        : this.getScrollElement()
    },
    _isRTL(element = this.getScrollElement()) {
      return getComputedStyle(element).direction === 'rtl'
    },
    _contentToVisual(contentPos, rtl = this._isRTL()) {
      if (
        this.frozenSectionWidth > 0 &&
        contentPos >= this.frozenSectionWidth
      ) {
        return (
          contentPos -
          getInlineScrollOffset(this._getScrollableElement().scrollLeft, rtl)
        )
      }
      return contentPos
    },
    getFieldLeft(id) {
      let left = 0
      for (let i = 0; i < this.fields.length; i++) {
        if (this.fields[i].id === id) {
          break
        }
        left += this.getFieldWidth(this.fields[i])
      }
      return left
    },
    /**
     * Called when the field dragging must start. It will register the global mouse
     * move, mouse up events and keyup events so that the user can drag the field to
     * the correct position.
     */
    start(field, event) {
      event.preventDefault()
      this.field = field
      this.targetFieldId = field.id
      this.dragging = true
      this.moved = false
      this.mouseStartX = event.clientX
      this.mouseStartY = event.clientY
      const scrollable = this._getScrollableElement()
      this.scrollStart = scrollable.scrollLeft
      const rtl = this._isRTL()
      const contentInlineStart = this.offset + this.getFieldLeft(field.id)
      this.initialVisualInlineStart = this._contentToVisual(
        contentInlineStart,
        rtl
      )
      this.draggingInlineStart = 0
      this.targetInlineStart = 0

      this.moveEvent = (event) => this.move(event)
      window.addEventListener('mousemove', this.moveEvent)

      this.upEvent = (event) => this.up(event)
      window.addEventListener('mouseup', this.upEvent)

      this.keydownEvent = (event) => {
        if (event.key === 'Escape') {
          // When the user presses the escape key we want to cancel the action
          this.cancel(event)
        }
      }
      document.body.addEventListener('keydown', this.keydownEvent)
    },
    /**
     * The move method is called when every time the user moves the mouse while
     * dragging a field. It can also be called while auto scrolling.
     */
    move(event = null, startAutoScroll = true) {
      if (event !== null) {
        event.preventDefault()
        this.lastMoveEvent = event
      } else {
        event = this.lastMoveEvent
      }

      // Sometimes the user could accidentally drag the element one or two pixels while
      // clicking it. Because it could be annoying that the click doesn't work because
      // the moving state started, we check here if the user has at least dragged
      // the element 3 pixels vertically or horizontally before starting the moved
      // state.
      if (!this.moved) {
        if (
          Math.abs(event.clientX - this.mouseStartX) > 3 ||
          Math.abs(event.clientY - this.mouseStartY) > 3
        ) {
          this.moved = true
        } else {
          return
        }
      }

      // The positioning element for coordinate calculations (getBoundingClientRect).
      const element = this.getScrollElement()
      // The element that actually scrolls horizontally.
      const scrollable = this._getScrollableElement()
      const rtl = this._isRTL(element)
      const scrollOffset = getInlineScrollOffset(scrollable.scrollLeft, rtl)

      this.draggingWidth = this.getFieldWidth(this.field)
      this.clipOffset = scrollOffset > 0 ? this.frozenSectionWidth : 0

      // The overlay is in the non-scrolling grid container. Work in logical inline
      // coordinates so moving toward inline-end behaves identically in LTR and RTL.
      const unclampedInlineStart =
        this.initialVisualInlineStart +
        getInlinePointerDelta(event.clientX, this.mouseStartX, rtl)
      const visibleWidth = this.frozenSectionWidth + scrollable.clientWidth
      this.draggingInlineStart = Math.max(
        0,
        Math.min(unclampedInlineStart, visibleWidth - this.draggingWidth)
      )

      const mouseInlineStart =
        getInlinePointerPosition(
          event.clientX,
          element.getBoundingClientRect(),
          rtl
        ) + scrollOffset
      const target = getFieldDragTarget(
        mouseInlineStart,
        this.fields,
        this.offset,
        (field) => this.getFieldWidth(field)
      )
      if (target !== null) {
        this.targetFieldId = target.fieldId
        // The value 1 keeps the indicator inside the clipping viewport.
        this.targetInlineStart = Math.max(
          this._contentToVisual(target.inlineStart, rtl),
          1
        )
      }

      // If the user is not already auto scrolling, which happens while dragging and
      // moving the element outside of the view port at the left or right side, we
      // might need to initiate that process.
      if (!this.autoScrolling || !startAutoScroll) {
        const maxScrollLeft = scrollable.scrollWidth - scrollable.clientWidth
        let speed = 0

        if (
          unclampedInlineStart < this.frozenSectionWidth &&
          scrollOffset > 0
        ) {
          // If the animation enters the frozen area, scroll toward inline-start.
          speed = -Math.ceil(
            Math.min(
              Math.abs(unclampedInlineStart - this.frozenSectionWidth),
              100
            ) / 20
          )
        } else if (
          unclampedInlineStart + this.draggingWidth > visibleWidth &&
          scrollOffset < maxScrollLeft
        ) {
          // If it falls beyond inline-end, continue scrolling in reading order.
          speed = Math.ceil(
            Math.min(
              unclampedInlineStart + this.draggingWidth - visibleWidth,
              100
            ) / 20
          )
        }

        // If the speed is either a position or negative, so not 0, we know that we
        // need to start auto scrolling.
        if (speed !== 0) {
          this.autoScrolling = true
          this.$emit('scroll', {
            pixelY: 0,
            pixelX: getPhysicalScrollDelta(speed, rtl),
          })
          this.scrollTimeout = setTimeout(() => {
            this.move(null, false)
          }, 1)
        } else {
          this.autoScrolling = false
        }
      }
    },
    /**
     * Can be called when the current dragging state needs to be stopped. It will
     * remove all the created event listeners and timeouts.
     */
    cancel() {
      this.dragging = false
      this.mouseStartX = 0
      this.mouseStartY = 0
      window.removeEventListener('mousemove', this.moveEvent)
      window.removeEventListener('mouseup', this.upEvent)
      document.body.removeEventListener('keydown', this.keydownEvent)
      clearTimeout(this.scrollTimeout)
    },
    /**
     * Called when the user releases the mouse on a the desired position. It will
     * calculate the new position of the field in the list and if it has changed
     * position, then the order in the field options is updated accordingly.
     */
    async up(event) {
      event.preventDefault()
      this.cancel()

      if (!this.moved) {
        return
      }

      // We don't need to do anything if the field needs to be placed after itself
      // because that wouldn't change the position.
      if (this.field.id === this.targetFieldId) {
        return
      }

      // If targetfieldId is 0 then the field should be moved to the left of the
      // first field, otherwise it should be moved at the right of the target field
      const position = this.targetFieldId === 0 ? 'left' : 'right'
      const fromField = {
        id: this.targetFieldId === 0 ? this.fields[0].id : this.targetFieldId,
      }
      try {
        await this.$store.dispatch(
          `${this.storePrefix}view/grid/updateSingleFieldOptionOrder`,
          {
            fieldToMove: this.field,
            position,
            fromField,
            readOnly: this.readOnly,
          }
        )
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
  },
}
</script>
