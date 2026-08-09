<template>
  <Modal ref="modal" :small="true">
    <h2 class="box__title">{{ $t(titleText) }}</h2>
    <Error :error="error"></Error>
    <form @submit.prevent="setPassword">
      <p class="box__description">{{ $t(descriptionText) }}</p>
      <FormGroup :error="fieldHasErrors('password')">
        <PasswordInput
          v-model="v$.values.password.$model"
          :validation-state="v$.values.password"
          :show-password-icon="true"
          :disabled="loading"
        />
      </FormGroup>
      <div class="actions">
        <ul class="action__links">
          <li>
            <a :disabled="loading" @click.prevent="hide()">{{
              $t('action.cancel')
            }}</a>
          </li>
        </ul>
        <Button
          type="primary"
          :loading="loading"
          :disabled="loading || v$.$invalid"
        >
          {{ $t(saveText) }}
        </Button>
      </div>
    </form>
  </Modal>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { reactive, computed } from 'vue'
import form from '@jadawel/modules/core/mixins/form'
import modal from '@jadawel/modules/core/mixins/modal'
import error from '@jadawel/modules/core/mixins/error'
import { passwordValidation } from '@jadawel/modules/core/validators'
import PasswordInput from '@jadawel/modules/core/components/helpers/PasswordInput'
import DashboardShareService from '@jadawel/modules/arabase/services/dashboardShare'

export default {
  name: 'DashboardSharePasswordModal',
  components: { PasswordInput },
  mixins: [form, modal, error],
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    change: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  emits: ['updated'],
  setup() {
    const values = reactive({
      values: {
        password: '',
      },
    })

    const rules = computed(() => ({
      values: {
        password: passwordValidation,
      },
    }))

    return {
      values: values.values,
      v$: useVuelidate(rules, values, { $lazy: true }),
    }
  },
  data() {
    return {
      loading: false,
      allowedValues: ['password'],
    }
  },
  computed: {
    titleText() {
      return this.change
        ? 'dashboardSharePasswordModal.changePasswordTitle'
        : 'dashboardSharePasswordModal.newPasswordTitle'
    },
    descriptionText() {
      return this.change
        ? 'dashboardSharePasswordModal.changePasswordDescription'
        : 'dashboardSharePasswordModal.newPasswordDescription'
    },
    saveText() {
      return this.change
        ? 'dashboardSharePasswordModal.changePasswordSave'
        : 'dashboardSharePasswordModal.newPasswordSave'
    },
  },
  methods: {
    clearInput() {
      this.values.password = ''
      this.v$.$reset()
    },
    show(...args) {
      this.clearInput()
      modal.methods.show.call(this, ...args)
      this.$nextTick(() => {
        this.$el.querySelector('input')?.focus()
      })
    },
    async setPassword() {
      this.hideError()
      this.loading = true

      try {
        const { data } = await DashboardShareService(this.$client).setPassword(
          this.dashboard.id,
          this.values.password
        )
        this.$emit('updated', data)
        this.hide()
      } catch (error) {
        this.handleError(error, 'dashboard')
      }

      this.loading = false
    },
  },
}
</script>
