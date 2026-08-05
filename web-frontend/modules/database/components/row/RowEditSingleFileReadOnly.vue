<template>
  <RowEditFieldFile
    :read-only="true"
    :field="field"
    :value="[value]"
    :workspace-id="workspaceId"
  >
  </RowEditFieldFile>
</template>

<script>
import baseField from '@jadawel/modules/database/mixins/baseField'
import RowEditFieldFile from '@jadawel/modules/database/components/row/RowEditFieldFile.vue'

export default {
  components: { RowEditFieldFile },
  mixins: [baseField],
}
</script>
