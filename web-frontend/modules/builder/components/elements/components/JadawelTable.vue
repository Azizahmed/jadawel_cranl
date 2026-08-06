<template>
  <div class="jadawel-table-wrapper">
    <table class="jadawel-table" :class="`jadawel-table--${orientation}`">
      <template v-if="orientation === ORIENTATIONS.HORIZONTAL">
        <thead>
          <tr class="jadawel-table__row">
            <template v-for="field in fields" :key="field.__id__">
              <slot name="field-name" :field="field">
                <th class="jadawel-table__header-cell">
                  {{ field.name }}
                </th>
              </slot>
            </template>
          </tr>
        </thead>
        <tbody v-if="rows.length">
          <tr
            v-for="(row, index) in rows"
            :key="row.__id__"
            class="jadawel-table__row"
          >
            <template v-for="field in fields" :key="field.id">
              <slot
                name="cell-content"
                :value="row[field.__id__]"
                :field="field"
                :row-index="index"
                :row="row"
              >
                <td class="jadawel-table__cell">
                  {{ row[field.__id__] }}
                </td>
              </slot>
            </template>
          </tr>
        </tbody>
      </template>
      <template v-else>
        <template v-if="rows.length">
          <tbody
            v-for="(row, rowIndex) in rows"
            :key="row.__id__"
            class="jadawel-table__row"
          >
            <tr
              v-for="(field, fieldIndex) in fields"
              :key="`${row.__id__}_${field.__id__}`"
            >
              <slot name="field-name" :field="field">
                <th :key="field.__id__" class="jadawel-table__header-cell">
                  {{ field.name }}
                </th>
              </slot>
              <slot
                name="cell-content"
                :value="row[field.__id__]"
                :field="field"
                :row-index="rowIndex"
                :row="row"
              >
                <td
                  class="jadawel-table__cell"
                  :class="{
                    'jadawel-table__separator':
                      fieldIndex === fields.length - 1,
                  }"
                >
                  {{ value }}
                </td>
              </slot>
            </tr>
          </tbody>
        </template>
      </template>
      <tbody v-if="!rows.length">
        <tr>
          <td class="jadawel-table__empty-message" :colspan="fields.length">
            <slot name="empty-state"></slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { ORIENTATIONS } from '@jadawel/modules/builder/enums'

export default {
  name: 'JadawelTable',
  inject: ['mode'],
  props: {
    fields: {
      type: Array,
      required: true,
    },
    rows: {
      type: Array,
      required: true,
    },
    orientation: {
      type: String,
      default: ORIENTATIONS.HORIZONTAL,
    },
  },
  computed: {
    ORIENTATIONS() {
      return ORIENTATIONS
    },
  },
}
</script>
