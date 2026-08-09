<template>
  <Context ref="context">
    <div class="widget-size-context">
      <div class="widget-size-context__grid" @mouseleave="preview = null">
        <button
          v-for="cell in cells"
          :key="`${cell.width}x${cell.height}`"
          type="button"
          class="widget-size-context__cell"
          :class="{
            'widget-size-context__cell--preview': isPreviewed(cell),
            'widget-size-context__cell--current': isCurrent(cell),
          }"
          :aria-label="$t('widgetContext.sizePreview', cell)"
          @mouseenter="preview = cell"
          @click="selectSize(cell)"
        ></button>
      </div>
      <div class="widget-size-context__preview">
        {{ previewLabel }}
      </div>
    </div>
  </Context>
</template>

<script>
import context from '@jadawel/modules/core/mixins/context'
import { notifyIf } from '@jadawel/modules/core/utils/error'

/**
 * Jadawel fork (grid board): the "Size" submenu of the widget context menu — a
 * 3×3 mini-grid picker. Rows are widget height, columns are widget width;
 * hovering a cell previews that rectangle and clicking PATCHes `width`/`height`
 * through the existing debounced `updateWidget` action.
 */
export default {
  name: 'WidgetSizeContext',
  mixins: [context],
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    widget: {
      type: Object,
      required: true,
    },
  },
  emits: ['selected'],
  data() {
    return {
      preview: null,
    }
  },
  computed: {
    cells() {
      const cells = []
      for (let height = 1; height <= 3; height++) {
        for (let width = 1; width <= 3; width++) {
          cells.push({ width, height })
        }
      }
      return cells
    },
    currentSize() {
      return {
        width: parseInt(this.widget.width) || 3,
        height: parseInt(this.widget.height) || 2,
      }
    },
    previewLabel() {
      const size = this.preview || this.currentSize
      return this.$t('widgetContext.sizePreview', size)
    },
  },
  methods: {
    isPreviewed(cell) {
      return (
        this.preview !== null &&
        cell.width <= this.preview.width &&
        cell.height <= this.preview.height
      )
    },
    isCurrent(cell) {
      return (
        cell.width === this.currentSize.width &&
        cell.height === this.currentSize.height
      )
    },
    async selectSize({ width, height }) {
      try {
        await this.$store.dispatch('dashboardApplication/updateWidget', {
          widgetId: this.widget.id,
          values: { width, height },
          originalValues: {
            width: this.currentSize.width,
            height: this.currentSize.height,
          },
        })
      } catch (error) {
        notifyIf(error, 'dashboard')
      }
      this.hide()
      this.$emit('selected')
    },
  },
}
</script>
