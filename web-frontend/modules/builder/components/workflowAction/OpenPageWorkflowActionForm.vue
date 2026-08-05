<template>
  <form @submit.prevent="submit">
    <LinkNavigationSelectionForm
      :default-values="defaultValues"
      @values-changed="emitChange($event)"
    />
  </form>
</template>

<script>
import LinkNavigationSelectionForm from '@jadawel/modules/builder/components/elements/components/forms/general/LinkNavigationSelectionForm'
import form from '@jadawel/modules/core/mixins/form'

export default {
  name: 'OpenPageWorkflowActionForm',
  components: { LinkNavigationSelectionForm },
  mixins: [form],
  data() {
    return {
      values: {},
    }
  },
}
</script>
