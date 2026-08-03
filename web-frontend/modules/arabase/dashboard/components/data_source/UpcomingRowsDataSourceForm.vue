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

      <template v-if="values.table_id && !fieldHasErrors('table_id')">
        <FormGroup
          :label="$t('upcomingRowsDataSourceForm.dateFieldLabel')"
          :helper-text="$t('upcomingRowsDataSourceForm.dateFieldHelp')"
          class="margin-bottom-2"
          small-label
          required
          horizontal
          horizontal-narrow
        >
          <Dropdown
            v-model="values.date_field_id"
            :disabled="fieldsLoading"
            :error="fieldHasErrors('date_field_id')"
          >
            <DropdownItem
              v-for="field in dateFields"
              :key="field.id"
              :name="field.name"
              :value="field.id"
              :icon="fieldIconClass(field)"
            >
            </DropdownItem>
            <template #emptyState>
              {{ $t('upcomingRowsDataSourceForm.noDateFields') }}
            </template>
          </Dropdown>
        </FormGroup>

        <FormGroup
          :label="$t('upcomingRowsDataSourceForm.windowLabel')"
          class="margin-bottom-2"
          small-label
          required
          horizontal
          horizontal-narrow
        >
          <Dropdown v-model="values.days_ahead">
            <DropdownItem
              v-for="option in windowOptions"
              :key="option"
              :name="$t('upcomingRowsDataSourceForm.days', { count: option })"
              :value="option"
            >
            </DropdownItem>
          </Dropdown>
        </FormGroup>

        <FormGroup
          :label="$t('upcomingRowsDataSourceForm.rowCountLabel')"
          :error="fieldHasErrors('default_result_count')"
          class="margin-bottom-2"
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
            {{
              $t('listRowsDataSourceForm.rowCountError', { max: maxRowCount })
            }}
          </template>
        </FormGroup>

        <FormGroup small-label horizontal horizontal-narrow>
          <Checkbox v-model="values.include_overdue">{{
            $t('upcomingRowsDataSourceForm.includeOverdue')
          }}</Checkbox>
        </FormGroup>
      </template>
    </FormSection>
  </form>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { required, integer, minValue, maxValue } from '@vuelidate/validators'
import dashboardTableSourceForm from '@baserow/modules/arabase/dashboard/mixins/dashboardTableSourceForm'
import TableViewFormGroups from '@baserow/modules/arabase/dashboard/components/data_source/TableViewFormGroups'

const MAX_ROW_COUNT = 20

// The windows people actually ask for. An arbitrary number of days would be a
// free-text field whose sensible values are these three anyway.
const WINDOW_OPTIONS = [7, 14, 30]

// Field types that carry a date. `created_on` and `last_modified` are included
// deliberately: an agenda of recently-touched records is a legitimate use, and
// the backend accepts them too.
const DATE_FIELD_TYPES = ['date', 'created_on', 'last_modified']

export default {
  name: 'UpcomingRowsDataSourceForm',
  components: { TableViewFormGroups },
  mixins: [dashboardTableSourceForm],
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  data() {
    return {
      allowedValues: [
        'table_id',
        'view_id',
        'date_field_id',
        'days_ahead',
        'include_overdue',
        'default_result_count',
      ],
      values: {
        table_id: null,
        view_id: null,
        date_field_id: null,
        days_ahead: 7,
        include_overdue: true,
        default_result_count: 10,
      },
      skipFirstValuesEmit: true,
    }
  },
  computed: {
    maxRowCount() {
      return MAX_ROW_COUNT
    },
    windowOptions() {
      return WINDOW_OPTIONS
    },
    dateFields() {
      return this.tableFields.filter((field) =>
        DATE_FIELD_TYPES.includes(field.type)
      )
    },
    dateFieldIds() {
      return this.dateFields.map((field) => field.id)
    },
  },
  watch: {
    fieldsLoading(loading) {
      // A widget with no date field cannot dispatch at all, so the first date
      // field on a newly chosen table is selected rather than left empty.
      if (!loading && this.values.date_field_id === null) {
        if (this.dateFields.length > 0) {
          this.values.date_field_id = this.dateFields[0].id
        }
      }
    },
  },
  validations() {
    return {
      values: {
        table_id: {
          required,
          isValidTableId: (value) => this.isValidTableId(value),
        },
        date_field_id: {
          required,
          isValidDateField: (value) => this.dateFieldIds.includes(value),
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
  methods: {
    onTableChanged() {
      this.values.view_id = null
      // The date field belongs to the table that was just replaced.
      this.values.date_field_id = null
    },
    fieldIconClass(field) {
      return this.$registry.get('field', field.type).iconClass
    },
  },
}
</script>
