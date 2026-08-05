<template>
  <div>
    <form class="margin-bottom-2" @submit.prevent>
      <FormSection :title="$t('chartWidgetSettings.appearance')">
        <FormGroup
          :label="$t('chartWidgetSettings.chartType')"
          class="margin-bottom-2"
          small-label
          required
          horizontal
          horizontal-narrow
        >
          <Dropdown v-model="chartType">
            <DropdownItem
              v-for="type in chartTypes"
              :key="type.value"
              :name="type.name"
              :value="type.value"
              :icon="type.icon"
            >
            </DropdownItem>
          </Dropdown>
        </FormGroup>
        <FormGroup small-label horizontal horizontal-narrow>
          <Checkbox v-model="showLegend">{{
            $t('chartWidgetSettings.showLegend')
          }}</Checkbox>
        </FormGroup>
      </FormSection>
    </form>

    <GroupedAggregateRowsDataSourceForm
      v-if="dataSource"
      ref="dataSourceForm"
      :dashboard="dashboard"
      :widget="widget"
      :data-source="dataSource"
      :default-values="dataSource"
      :store-prefix="storePrefix"
      @values-changed="onDataSourceValuesChanged"
    />
  </div>
</template>

<script>
import GroupedAggregateRowsDataSourceForm from '@jadawel/modules/arabase/dashboard/components/data_source/GroupedAggregateRowsDataSourceForm'
import error from '@jadawel/modules/core/mixins/error'
import { notifyIf } from '@jadawel/modules/core/utils/error'

export default {
  name: 'ChartWidgetSettings',
  components: { GroupedAggregateRowsDataSourceForm },
  mixins: [error],
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
    chartTypes() {
      return [
        {
          value: 'bar',
          name: this.$t('chartWidget.bar'),
          icon: 'iconoir-bar-chart',
        },
        {
          value: 'line',
          name: this.$t('chartWidget.line'),
          icon: 'iconoir-graph-up',
        },
        {
          value: 'pie',
          name: this.$t('chartWidget.pie'),
          icon: 'iconoir-pie-chart',
        },
        {
          value: 'doughnut',
          name: this.$t('chartWidget.doughnut'),
          icon: 'iconoir-pie-chart',
        },
      ]
    },
    chartType: {
      get() {
        return this.widget.chart_type
      },
      set(value) {
        this.updateWidget({ chart_type: value })
      },
    },
    showLegend: {
      get() {
        return this.widget.show_legend
      },
      set(value) {
        this.updateWidget({ show_legend: value })
      },
    },
    dataSource() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/getDataSourceById`
      ](this.widget.data_source_id)
    },
  },
  methods: {
    async updateWidget(values) {
      const originalValues = Object.fromEntries(
        Object.keys(values).map((key) => [key, this.widget[key]])
      )
      try {
        await this.$store.dispatch(
          `${this.storePrefix}dashboardApplication/updateWidget`,
          {
            widgetId: this.widget.id,
            values,
            originalValues,
          }
        )
      } catch (error) {
        notifyIf(error, 'dashboard')
      }
    },
    async onDataSourceValuesChanged(changedDataSourceValues) {
      if (this.$refs.dataSourceForm.isFormValid()) {
        try {
          await this.$store.dispatch(
            `${this.storePrefix}dashboardApplication/updateDataSource`,
            {
              dataSourceId: this.dataSource.id,
              values: changedDataSourceValues,
            }
          )
        } catch (error) {
          this.$refs.dataSourceForm.reset()
          this.$refs.dataSourceForm.touch()
          notifyIf(error, 'dashboard')
        }
      }
    },
  },
}
</script>
