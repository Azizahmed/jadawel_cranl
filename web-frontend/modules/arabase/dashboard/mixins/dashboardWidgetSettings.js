import { notifyIf } from '@jadawel/modules/core/utils/error'
import error from '@jadawel/modules/core/mixins/error'

/**
 * The two writes every widget settings panel makes: one to the widget itself and
 * one to its data source.
 *
 * Widget fields are pushed one at a time from a computed setter (a dropdown or a
 * checkbox changes exactly one thing), while the data source form emits its whole
 * changed set — so the two paths differ and both are needed.
 */
export default {
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
    dataSource() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/getDataSourceById`
      ](this.widget.data_source_id)
    },
  },
  methods: {
    async updateWidget(values) {
      // The store rolls back to `originalValues` if the request fails, so they
      // have to be the values as they are right now, not the form's defaults.
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
