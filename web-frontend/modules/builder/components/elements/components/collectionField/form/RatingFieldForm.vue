<template>
  <form @submit.prevent @keydown.enter.prevent>
    <FormGroup
      small-label
      :label="$t('ratingFieldForm.value')"
      class="margin-bottom-2"
      horizontal
      required
    >
      <InjectedFormulaInput v-model="values.value" />
    </FormGroup>
    <RatingFormFields
      :default-values="defaultValues"
      horizontal
      :color-variables="colorVariables"
      @values-changed="emitChange"
    />
  </form>
</template>

<script>
import collectionFieldForm from '@jadawel/modules/builder/mixins/collectionFieldForm'
import InjectedFormulaInput from '@jadawel/modules/core/components/formula/InjectedFormulaInput'
import RatingFormFields from '@jadawel/modules/builder/components/elements/components/forms/RatingFormFields'

export default {
  name: 'RatingFieldForm',
  components: {
    InjectedFormulaInput,
    RatingFormFields,
  },
  mixins: [collectionFieldForm],
  data() {
    return {
      allowedValues: ['value'],
      values: {
        value: {},
      },
    }
  },
}
</script>
