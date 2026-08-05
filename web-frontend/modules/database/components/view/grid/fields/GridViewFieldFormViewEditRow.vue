<template>
  <div ref="cell" class="grid-view__cell active">
    <div class="grid-field-button">
      <Button
        v-if="value"
        tag="a"
        type="secondary"
        size="tiny"
        :href="value"
        target="_blank"
      >
        {{ $t('editRowLink.editRow') }}
      </Button>
      <Button v-else type="secondary" size="tiny" disabled>
        {{ $t('editRowLink.editRow') }}
      </Button>
    </div>
  </div>
</template>

<script>
import gridField from '@jadawel/modules/database/mixins/gridField'
import gridFieldInput from '@jadawel/modules/database/mixins/gridFieldInput'

export default {
  name: 'GridViewFieldFormViewEditRow',
  mixins: [gridField, gridFieldInput],
}
</script>
