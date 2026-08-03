<template>
  <div class="widget-record-rows">
    <table class="widget-record-rows__table">
      <thead>
        <tr>
          <th v-for="field in fields" :key="field.id">{{ field.name }}</th>
          <th v-if="trailingLabel" class="widget-record-rows__trailing">
            {{ trailingLabel }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, index) in rows"
          :key="row.id ?? index"
          :class="{ 'widget-record-rows__row--flagged': flagged(row) }"
        >
          <td
            v-for="field in fields"
            :key="field.id"
            :title="value(row, field)"
          >
            {{ value(row, field) }}
          </td>
          <td v-if="trailingLabel" class="widget-record-rows__trailing">
            {{ trailing(row) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { formatRecordValue } from '@baserow/modules/arabase/dashboard/recordValues'

export default {
  name: 'RecordRows',
  props: {
    rows: {
      type: Array,
      required: true,
    },
    fields: {
      type: Array,
      required: true,
    },
    /**
     * An extra right-hand column, used by the agenda widget for its due-date
     * text. Kept as a callback so this component stays about layout only.
     */
    trailingLabel: {
      type: String,
      required: false,
      default: null,
    },
    trailingValue: {
      type: Function,
      required: false,
      default: null,
    },
    rowIsFlagged: {
      type: Function,
      required: false,
      default: null,
    },
  },
  methods: {
    value(row, field) {
      return formatRecordValue(row[field.name])
    },
    trailing(row) {
      return this.trailingValue ? this.trailingValue(row) : ''
    },
    flagged(row) {
      return this.rowIsFlagged ? this.rowIsFlagged(row) : false
    },
  },
}
</script>
