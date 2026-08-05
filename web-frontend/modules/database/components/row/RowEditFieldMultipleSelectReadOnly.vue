<template>
  <div>
    <RowEditFieldMultipleSelect
      :read-only="true"
      :field="field"
      :value="value"
      :workspace-id="workspaceId"
    >
    </RowEditFieldMultipleSelect>
  </div>
</template>

<script>
import RowEditFieldMultipleSelect from '@jadawel/modules/database/components/row/RowEditFieldMultipleSelect'
import baseField from '@jadawel/modules/database/mixins/baseField'

export default {
  name: 'RowEditFieldMultipleSelectReadOnly',
  components: { RowEditFieldMultipleSelect },
  mixins: [baseField],
}
</script>
