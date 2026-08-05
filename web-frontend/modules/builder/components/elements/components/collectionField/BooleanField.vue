<template>
  <ABCheckbox :model-value="value" :read-only="true" />
</template>

<script>
import ABCheckbox from '@jadawel/modules/builder/components/elements/baseComponents/ABCheckbox'
import collectionField from '@jadawel/modules/builder/mixins/collectionField'

export default {
  name: 'BooleanField',
  components: { ABCheckbox },
  mixins: [collectionField],
  props: {
    value: {
      type: Boolean,
      default: false,
    },
  },
}
</script>
