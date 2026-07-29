<template>
  <div class="chart">
    <div class="chart__title">{{ title }}</div>

    <!--
      Every value is rendered as text beside its bar, so the chart is readable
      without seeing the bars at all. That is why there is no separate table
      view here: the table would repeat the DOM that already exists.
    -->
    <ul v-if="items.length" class="chart__bars">
      <li v-for="item in scaled" :key="item.key" class="chart__bar-row">
        <span class="chart__bar-label" :title="item.label">{{ item.label }}</span>
        <span class="chart__bar-track">
          <span
            class="chart__bar-fill"
            :style="{ inlineSize: item.percentage + '%' }"
          ></span>
        </span>
        <span class="chart__bar-value">{{ formatValue(item.value) }}</span>
      </li>
    </ul>

    <div v-else class="chart__empty">{{ emptyMessage }}</div>
  </div>
</template>

<script>
export default {
  name: 'DashboardBarChart',
  props: {
    title: {
      type: String,
      required: true,
    },
    /**
     * `[{ key, label, value }]`, already ordered by the caller. One series, so
     * one colour and no legend — the row labels carry identity.
     */
    items: {
      type: Array,
      required: true,
    },
    emptyMessage: {
      type: String,
      required: true,
    },
  },
  computed: {
    /**
     * Bar widths as a percentage of the largest value, not of the total.
     *
     * Scaling to the total would make every bar in a lopsided workspace
     * invisible: with 200/66/13 rows the two smaller databases would be 24% and
     * 5% of the track instead of 33% and 7% of the leader. The chart compares
     * databases to each other, so the leader is the right reference.
     *
     * A minimum width keeps a non-zero value from rendering as nothing at all,
     * which would read as "no rows" rather than "few rows".
     */
    scaled() {
      const max = Math.max(...this.items.map((item) => item.value), 0)
      return this.items.map((item) => ({
        ...item,
        percentage:
          max > 0 && item.value > 0
            ? Math.max((item.value / max) * 100, 1.5)
            : 0,
      }))
    },
  },
  methods: {
    formatValue(value) {
      return new Intl.NumberFormat(this.$i18n.locale).format(value)
    },
  },
}
</script>
