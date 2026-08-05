<template>
  <component
    :is="componentType"
    v-if="componentType"
    :row="row"
    :field="field"
    :value="value"
  ></component>
  <div v-else class="grid-view__cell cell-error">
    {{ $t('functionalGridViewFieldFormula.unknownFieldType') }}
  </div>
</template>
<script>
import FunctionalGridViewFieldBoolean from '@jadawel/modules/database/components/view/grid/fields/FunctionalGridViewFieldBoolean'
import FunctionalGridViewFieldDate from '@jadawel/modules/database/components/view/grid/fields/FunctionalGridViewFieldDate'
import FunctionalGridViewFieldNumber from '@jadawel/modules/database/components/view/grid/fields/FunctionalGridViewFieldNumber'
import FunctionalGridViewFieldText from '@jadawel/modules/database/components/view/grid/fields/FunctionalGridViewFieldText'
import FunctionalGridViewSingleFile from '@jadawel/modules/database/components/view/grid/fields/FunctionalGridViewSingleFile'

export default {
  name: 'FunctionalGridViewFieldFormula',
  components: {
    FunctionalGridViewFieldDate,
    FunctionalGridViewFieldText,
    FunctionalGridViewFieldBoolean,
    FunctionalGridViewFieldNumber,
    FunctionalGridViewSingleFile,
  },
  props: {
    row: {
      type: Object,
      required: true,
    },
    field: {
      type: Object,
      required: true,
    },
    value: {
      type: null,
      default: null,
    },
  },
  computed: {
    componentType() {
      if (!this.$registry) {
        return null
      }
      const formulaType = this.$registry.get(
        'formula_type',
        this.field.formula_type
      )
      return formulaType.getFunctionalGridViewFieldComponent()
    },
  },
}
</script>
