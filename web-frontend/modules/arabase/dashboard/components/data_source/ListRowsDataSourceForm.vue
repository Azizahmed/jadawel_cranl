<template>
  <form @submit.prevent>
    <FormSection
      :title="$t('listRowsDataSourceForm.data')"
      class="margin-bottom-2"
    >
      <TableViewFormGroups
        v-model:table-id="computedTableId"
        v-model:view-id="values.view_id"
        :databases="databases"
        :table-views="tableViews"
        :fields-loading="fieldsLoading"
        :table-has-errors="fieldHasErrors('table_id')"
      />

      <FormGroup
        v-if="values.table_id && !fieldHasErrors('table_id')"
        :label="$t('listRowsDataSourceForm.rowCountLabel')"
        :error="fieldHasErrors('default_result_count')"
        small-label
        required
        horizontal
        horizontal-narrow
      >
        <FormInput
          v-model="values.default_result_count"
          type="number"
          :min="1"
          :max="maxRowCount"
          :error="fieldHasErrors('default_result_count')"
          @input="v$.values.default_result_count.$touch"
        />
        <template #error>
          {{ $t('listRowsDataSourceForm.rowCountError', { max: maxRowCount }) }}
        </template>
      </FormGroup>
    </FormSection>
  </form>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { required, integer, minValue, maxValue } from '@vuelidate/validators'
import dashboardTableSourceForm from '@jadawel/modules/arabase/dashboard/mixins/dashboardTableSourceForm'
import TableViewFormGroups from '@jadawel/modules/arabase/dashboard/components/data_source/TableViewFormGroups'

// A dashboard widget is a glance, not a table view. Twenty rows is already more
// than fits without scrolling on most boards.
const MAX_ROW_COUNT = 20

export default {
  name: 'ListRowsDataSourceForm',
  components: { TableViewFormGroups },
  mixins: [dashboardTableSourceForm],
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  data() {
    return {
      allowedValues: ['table_id', 'view_id', 'default_result_count'],
      values: {
        table_id: null,
        view_id: null,
        default_result_count: 5,
      },
      skipFirstValuesEmit: true,
    }
  },
  computed: {
    maxRowCount() {
      return MAX_ROW_COUNT
    },
  },
  validations() {
    return {
      values: {
        table_id: {
          required,
          isValidTableId: (value) => this.isValidTableId(value),
        },
        default_result_count: {
          required,
          integer,
          minValue: minValue(1),
          maxValue: maxValue(MAX_ROW_COUNT),
        },
      },
    }
  },
}
</script>
