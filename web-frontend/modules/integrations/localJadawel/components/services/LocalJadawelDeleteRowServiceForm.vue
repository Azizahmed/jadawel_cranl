<template>
  <LocalJadawelServiceForm
    ref="form"
    enable-row-id
    v-bind="$attrs"
    :enable-view-picker="false"
  />
</template>

<script>
import LocalJadawelServiceForm from '@jadawel/modules/integrations/localJadawel/components/services/LocalJadawelServiceForm'

export default {
  name: 'LocalJadawelDeleteRowServiceForm',
  components: {
    LocalJadawelServiceForm,
  },
  methods: {
    isFormValid() {
      return this.$refs.form.isFormValid()
    },
  },
}
</script>
