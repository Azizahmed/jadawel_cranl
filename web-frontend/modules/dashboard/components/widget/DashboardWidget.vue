<template>
  <div
    class="dashboard-widget"
    :class="{
      'dashboard-widget--selected': isSelected,
      'dashboard-widget--selectable': isSelectable,
    }"
    :style="gridStyle"
    @click="selectWidgetIfAllowed(widget.id)"
  >
    <div v-if="isSelected && isEditMode" class="dashboard-widget__name">
      {{ widgetType.name }}
    </div>
    <component
      :is="widgetComponent(widget.type)"
      :dashboard="dashboard"
      :widget="widget"
      :store-prefix="storePrefix"
      :loading="isLoading"
      :edit-mode="isEditMode"
    />
  </div>
</template>

<script>
export default {
  name: 'DashboardWidget',
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    widget: {
      type: Object,
      required: true,
    },
    storePrefix: {
      type: String,
      required: false,
      default: '',
    },
  },
  computed: {
    isSelected() {
      return this.selectedWidgetId === this.widget.id && this.isEditMode
    },
    isSelectable() {
      return this.selectedWidgetId !== this.widget.id && this.isEditMode
    },
    widgetType() {
      return this.$registry.get('dashboardWidget', this.widget.type)
    },
    selectedWidgetId() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/getSelectedWidgetId`
      ]
    },
    isEditMode() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/isEditMode`
      ]
    },
    gridStyle() {
      // Jadawel fork (grid board): the widget's cell spans on the 3-column
      // board. Widgets without the fields (created before the grid layout, or
      // mid-creation) keep the old full-width stacked look: 3 columns × 2 rows.
      const width = Math.min(3, Math.max(1, parseInt(this.widget.width) || 3))
      const height = Math.min(3, Math.max(1, parseInt(this.widget.height) || 2))
      return {
        gridColumn: `span ${width}`,
        gridRow: `span ${height}`,
      }
    },
    isLoading() {
      return this.widgetType.isLoading(
        this.widget,
        this.$store.getters[`${this.storePrefix}dashboardApplication/getData`]
      )
    },
  },
  methods: {
    widgetComponent(type) {
      const widgetType = this.$registry.get('dashboardWidget', type)
      return widgetType.component
    },
    selectWidgetIfAllowed(widgetId) {
      if (this.canSelectWidget()) {
        this.$store.dispatch(
          `${this.storePrefix}dashboardApplication/selectWidget`,
          widgetId
        )
      }
    },
    canSelectWidget() {
      return this.$hasPermission(
        'dashboard.widget.update',
        this.widget,
        this.dashboard.workspace.id
      )
    },
  },
}
</script>
