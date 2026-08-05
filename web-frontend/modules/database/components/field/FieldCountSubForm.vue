<template>
  <div>
    <FieldSelectThroughFieldSubForm
      :fields="allFieldsInTable"
      :database="database"
      :default-values="defaultValues"
    ></FieldSelectThroughFieldSubForm>
  </div>
</template>

<script>
import form from '@jadawel/modules/core/mixins/form'
import fieldSubForm from '@jadawel/modules/database/mixins/fieldSubForm'
import FieldSelectThroughFieldSubForm from '@jadawel/modules/database/components/field/FieldSelectThroughFieldSubForm'

export default {
  name: 'FieldCountSubForm',
  components: { FieldSelectThroughFieldSubForm },
  mixins: [form, fieldSubForm],
  data() {
    return {
      allowedValues: [],
      values: {},
    }
  },
}
</script>
