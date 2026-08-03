import form from '@baserow/modules/core/mixins/form'
import tableFields from '@baserow/modules/database/mixins/tableFields'

/**
 * The table/view half of a dashboard data source form.
 *
 * Every widget that reads rows needs the same four things — the integration's
 * databases, the tables in them, the views of the chosen table, and a reset when
 * the table changes — and the differences between the widgets live entirely in
 * what they add on top. Components using this own their `values`, `allowedValues`
 * and `validations`, and may override `onTableChanged` to clear anything else
 * that pointed at the previous table.
 */
export default {
  mixins: [form, tableFields],
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    widget: {
      type: Object,
      required: true,
    },
    dataSource: {
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
    computedTableId: {
      get() {
        return this.values.table_id
      },
      set(tableId) {
        if (tableId !== this.values.table_id) {
          this.values.table_id = tableId
          this.onTableChanged()
        }
      },
    },
    integration() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/getIntegrationById`
      ](this.dataSource.integration_id)
    },
    databases() {
      return this.integration.context_data.databases
    },
    databaseSelected() {
      return this.databases.find((database) =>
        database.tables.some((table) => table.id === this.values.table_id)
      )
    },
    tables() {
      return this.databases.map((database) => database.tables).flat()
    },
    tableIds() {
      return this.tables.map((table) => table.id)
    },
    tableViews() {
      return (
        this.databaseSelected?.views.filter(
          (view) => view.table_id === this.values.table_id
        ) || []
      )
    },
  },
  watch: {
    dataSource: {
      async handler() {
        // Reset so the form shows the newly selected widget's values, then run
        // validation immediately so a broken configuration is visible without the
        // user having to touch a field first.
        this.setEmitValues(false)
        await this.reset(true)
        this.v$.$touch()
        await this.$nextTick()
        this.setEmitValues(true)
      },
      deep: true,
    },
  },
  mounted() {
    this.v$.$validate()
  },
  methods: {
    /* Overrides the method in the tableFields mixin */
    getTableId() {
      return this.values.table_id
    },
    onTableChanged() {
      // The view belongs to the table that was just replaced.
      this.values.view_id = null
    },
    isValidTableId(value) {
      return this.tableIds.includes(value)
    },
  },
}
