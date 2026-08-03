<template>
  <div>
    <FormGroup
      :label="$t('listRowsDataSourceForm.sourceFieldLabel')"
      class="margin-bottom-2"
      small-label
      required
      horizontal
      horizontal-narrow
    >
      <Dropdown
        :model-value="tableId"
        :show-search="true"
        fixed-items
        :error="tableHasErrors"
        @update:model-value="$emit('update:tableId', $event)"
      >
        <DropdownSection
          v-for="database in databases"
          :key="database.id"
          :title="`${database.name} (${database.id})`"
        >
          <DropdownItem
            v-for="table in database.tables"
            :key="table.id"
            :name="table.name"
            :value="table.id"
            :indented="true"
          >
            {{ table.name }}
          </DropdownItem>
        </DropdownSection>
      </Dropdown>
    </FormGroup>

    <FormGroup
      v-if="tableId && !tableHasErrors"
      :label="$t('listRowsDataSourceForm.viewFieldLabel')"
      :helper-text="$t('listRowsDataSourceForm.viewHelp')"
      class="margin-bottom-2"
      small-label
      horizontal
      horizontal-narrow
    >
      <Dropdown
        :model-value="viewId"
        fixed-items
        :disabled="fieldsLoading"
        @update:model-value="$emit('update:viewId', $event)"
      >
        <DropdownItem
          :name="$t('listRowsDataSourceForm.notSelected')"
          :value="null"
          >{{ $t('listRowsDataSourceForm.notSelected') }}</DropdownItem
        >
        <DropdownItem
          v-for="view in tableViews"
          :key="view.id"
          :name="view.name"
          :value="view.id"
        >
          {{ view.name }}
        </DropdownItem>
      </Dropdown>
    </FormGroup>
  </div>
</template>

<script>
/**
 * The table and view pickers, which every row-reading widget starts with.
 *
 * Presentational on purpose: the owning form keeps the values and the validation,
 * so this can be dropped into a form without dictating its shape.
 */
export default {
  name: 'TableViewFormGroups',
  props: {
    tableId: {
      type: Number,
      required: false,
      default: null,
    },
    viewId: {
      type: Number,
      required: false,
      default: null,
    },
    databases: {
      type: Array,
      required: true,
    },
    tableViews: {
      type: Array,
      required: true,
    },
    fieldsLoading: {
      type: Boolean,
      required: false,
      default: false,
    },
    tableHasErrors: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  emits: ['update:tableId', 'update:viewId'],
}
</script>
