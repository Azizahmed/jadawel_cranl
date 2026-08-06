<template>
  <UpsertRowWorkflowActionForm enable-row-id v-bind="$attrs" />
</template>

<script>
import UpsertRowWorkflowActionForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelUpsertRowServiceForm'

export default {
  name: 'LocalJadawelUpdateRowServiceForm',
  components: { UpsertRowWorkflowActionForm },
}
</script>
