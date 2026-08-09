<template>
  <Modal ref="modal">
    <h2 class="box__title">{{ $t('dashboardRotateSlugModal.title') }}</h2>
    <Error :error="error"></Error>
    <div>
      <p>
        {{
          $t('dashboardRotateSlugModal.refreshWarning', {
            dashboardName: dashboard.name,
          })
        }}
      </p>
      <div class="actions">
        <div class="align-right">
          <Button
            type="primary"
            size="large"
            :loading="loading"
            :disabled="loading"
            @click="rotateSlug()"
          >
            {{ $t('dashboardRotateSlugModal.generateNewURL') }}
          </Button>
        </div>
      </div>
    </div>
  </Modal>
</template>

<script>
import modal from '@jadawel/modules/core/mixins/modal'
import error from '@jadawel/modules/core/mixins/error'
import DashboardShareService from '@jadawel/modules/arabase/services/dashboardShare'

export default {
  name: 'DashboardRotateSlugModal',
  mixins: [modal, error],
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
  },
  emits: ['rotated'],
  data() {
    return {
      loading: false,
    }
  },
  methods: {
    async rotateSlug() {
      this.hideError()
      this.loading = true

      try {
        const { data } = await DashboardShareService(this.$client).rotateSlug(
          this.dashboard.id
        )
        this.$emit('rotated', data)
        this.hide()
      } catch (error) {
        this.handleError(error, 'dashboard')
      }

      this.loading = false
    },
  },
}
</script>
