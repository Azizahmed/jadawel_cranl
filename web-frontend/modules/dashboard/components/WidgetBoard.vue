<template>
  <div class="widget-board" :class="{ 'widget-board--draggable': dragEnabled }">
    <DashboardWidget
      v-for="widget in widgets"
      :key="widget.id"
      v-grid-sortable="{
        id: widget.id,
        enabled: canDrag(widget),
        handle: '.widget__header',
        update: onWidgetDrop,
      }"
      :widget="widget"
      :dashboard="dashboard"
      :store-prefix="storePrefix"
    />
  </div>
</template>

<script>
import DashboardWidget from '@jadawel/modules/dashboard/components/widget/DashboardWidget'
import { notifyIf } from '@jadawel/modules/core/utils/error'
import { computeWidgetOrderUpdate } from '@jadawel/modules/arabase/utils/gridOrder'

// Matches `$dashboard-breakpoint` in the fork's widget_board.scss: below it the
// grid collapses to one column and drag-reorder is disabled (the size picker
// still works there).
const GRID_BREAKPOINT = 900

export default {
  name: 'WidgetBoard',
  components: { DashboardWidget },
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    storePrefix: {
      type: String,
      required: false,
      default: '',
    },
  },
  data() {
    return {
      windowWidth: null,
    }
  },
  computed: {
    isEditMode() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/isEditMode`
      ]
    },
    widgets() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/getWidgets`
      ]
    },
    isNarrowScreen() {
      return this.windowWidth !== null && this.windowWidth <= GRID_BREAKPOINT
    },
    dragEnabled() {
      return this.isEditMode && !this.isNarrowScreen
    },
  },
  mounted() {
    this.windowWidth = window.innerWidth
    this.windowResizeEvent = () => {
      this.windowWidth = window.innerWidth
    }
    window.addEventListener('resize', this.windowResizeEvent)
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.windowResizeEvent)
  },
  methods: {
    canDrag(widget) {
      return (
        this.dragEnabled &&
        this.$hasPermission(
          'dashboard.widget.update',
          widget,
          this.dashboard.workspace.id
        )
      )
    },
    /**
     * Jadawel fork (grid board): a drop only changes the moved widget's
     * position in the order — the fractional `order` between its two new
     * neighbours is computed client-side and PATCHed through the existing
     * debounced update action; the response refreshes the local order value.
     */
    async onWidgetDrop(newOrder, oldOrder, movedId) {
      const widgetsById = new Map(this.widgets.map((w) => [w.id, w]))
      const sortedWidgets = newOrder
        .map((id) => widgetsById.get(id))
        .filter(Boolean)
      const newIndex = sortedWidgets.findIndex((w) => w.id === movedId)
      if (newIndex === -1) {
        return
      }
      const order = computeWidgetOrderUpdate(sortedWidgets, movedId, newIndex)
      try {
        await this.$store.dispatch(
          `${this.storePrefix}dashboardApplication/updateWidget`,
          {
            widgetId: movedId,
            values: { order },
            originalValues: { order: widgetsById.get(movedId)?.order },
          }
        )
      } catch (error) {
        notifyIf(error, 'dashboard')
      }
    },
  },
}
</script>
