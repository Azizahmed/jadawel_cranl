<template>
  <section class="dashboard__overview">
    <h4 class="dashboard__section-title">{{ $t('dashboardOverview.title') }}</h4>

    <div class="dashboard__stat-tiles">
      <div v-for="tile in tiles" :key="tile.key" class="dashboard__stat-tile">
        <div class="dashboard__stat-tile-label">{{ tile.label }}</div>
        <div class="dashboard__stat-tile-value">{{ tile.value }}</div>
      </div>
    </div>

    <div class="dashboard__charts">
      <DashboardBarChart
        :title="$t('dashboardCharts.rowsPerDatabase')"
        :items="rowsPerDatabase"
        :empty-message="$t('dashboardCharts.noDatabases')"
      />
      <DashboardAreaChart
        :title="$t('dashboardCharts.rowsAddedOverTime', { days: activityDays })"
        :series="activitySeries"
        :empty-message="$t('dashboardCharts.noActivity')"
      />
    </div>
  </section>
</template>

<script>
import DashboardBarChart from '@baserow/modules/core/components/dashboard/DashboardBarChart'
import DashboardAreaChart from '@baserow/modules/core/components/dashboard/DashboardAreaChart'

// Beyond this the chart is a wall of near-identical bars that answers nothing.
// The remainder is folded into one row rather than dropped, so the totals in the
// tiles above still reconcile with what the chart shows.
const MAX_BARS = 6

export default {
  name: 'DashboardOverview',
  components: { DashboardBarChart, DashboardAreaChart },
  props: {
    workspace: {
      type: Object,
      required: true,
    },
    applications: {
      type: Array,
      required: true,
    },
    /**
     * `{ [databaseId]: { table_count, field_count, row_count, rows_exact } }`,
     * or `{}` while the request is in flight or after it failed.
     */
    stats: {
      type: Object,
      required: true,
    },
    /**
     * `{ days, complete, total, series }`, or null until it resolves.
     */
    activity: {
      type: Object,
      required: false,
      default: null,
    },
  },
  computed: {
    statEntries() {
      return Object.entries(this.stats)
    },
    /**
     * Row totals are only shown when every database reported an exact count.
     * One database that gave up on counting would make the workspace total an
     * undercount presented as fact, which is worse than showing a dash.
     */
    rowsAreExact() {
      return this.statEntries.every(([, stat]) => stat.rows_exact)
    },
    tiles() {
      const tables = this.statEntries.reduce(
        (sum, [, stat]) => sum + stat.table_count,
        0
      )
      const rows = this.statEntries.reduce(
        (sum, [, stat]) => sum + (stat.row_count || 0),
        0
      )

      return [
        {
          key: 'databases',
          label: this.$t('dashboardOverview.databases'),
          value: this.format(this.statEntries.length),
        },
        {
          key: 'tables',
          label: this.$t('dashboardOverview.tables'),
          value: this.format(tables),
        },
        {
          key: 'rows',
          label: this.$t('dashboardOverview.rows'),
          value: this.rowsAreExact ? this.format(rows) : '—',
        },
        {
          key: 'members',
          label: this.$t('dashboardOverview.members'),
          value: this.format(this.workspace.users?.length || 0),
        },
      ]
    },
    rowsPerDatabase() {
      if (!this.rowsAreExact) {
        return []
      }

      const named = this.statEntries
        .map(([id, stat]) => ({
          key: id,
          label:
            this.applications.find((a) => String(a.id) === String(id))?.name ||
            this.$t('dashboardCharts.untitledDatabase'),
          value: stat.row_count || 0,
        }))
        .sort((a, b) => b.value - a.value)

      if (named.length <= MAX_BARS) {
        return named
      }

      const shown = named.slice(0, MAX_BARS - 1)
      const rest = named.slice(MAX_BARS - 1)
      return [
        ...shown,
        {
          key: 'other',
          label: this.$t('dashboardCharts.otherDatabases', {
            count: rest.length,
          }),
          value: rest.reduce((sum, item) => sum + item.value, 0),
        },
      ]
    },
    activitySeries() {
      return this.activity?.complete ? this.activity.series : []
    },
    activityDays() {
      return this.activity?.days || 30
    },
  },
  methods: {
    format(value) {
      return new Intl.NumberFormat(this.$i18n.locale).format(value)
    },
  },
}
</script>
