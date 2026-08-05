<template>
  <div style="position: absolute">
    <ApplicationContext
      ref="context"
      :application="application"
      :workspace="workspace"
    >
      <template #additional-context-items></template>
    </ApplicationContext>
  </div>
</template>

<script>
import ApplicationContext from '@jadawel/modules/core/components/application/ApplicationContext.vue'
import applicationContext from '@jadawel/modules/core/mixins/applicationContext'

export default {
  components: {
    ApplicationContext,
  },
  mixins: [applicationContext],
  props: {
    application: {
      type: Object,
      required: true,
    },
    workspace: {
      type: Object,
      required: true,
    },
  },
}
</script>
