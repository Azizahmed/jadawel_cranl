<template>
  <div class="control__elements">
    <div v-show="field.error" class="error">
      {{ field.error }}
    </div>
  </div>
</template>

<script>
import rowEditField from '@jadawel/modules/database/mixins/rowEditField'
import rowEditFieldInput from '@jadawel/modules/database/mixins/rowEditFieldInput'

export default {
  mixins: [rowEditField, rowEditFieldInput],
}
</script>
