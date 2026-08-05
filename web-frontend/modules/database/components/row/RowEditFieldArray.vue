<template>
  <div class="control__elements">
    <FunctionalFormulaArrayItems
      class="row-edit-array-field"
      :row="row"
      :field="field"
      :value="value"
      :selected="true"
    >
      <div
        v-if="shouldFetchRow"
        class="array-field__item"
        :class="{ 'array-field__item--loading': isFetchingRow }"
      >
        <div v-if="isFetchingRow" class="loading"></div>
        <span v-else>...</span>
      </div>
    </FunctionalFormulaArrayItems>
  </div>
</template>

<script>
import rowEditField from '@jadawel/modules/database/mixins/rowEditField'
import FunctionalFormulaArrayItems from '@jadawel/modules/database/components/formula/array/FunctionalFormulaArrayItems'
import arrayLoading from '@jadawel/modules/database/mixins/arrayLoading'

export default {
  name: 'RowEditFieldArray',
  components: {
    FunctionalFormulaArrayItems,
  },
  mixins: [rowEditField, arrayLoading],
}
</script>
