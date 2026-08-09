<template>
  <div class="auth__wrapper">
    <h2 class="auth__head-title">
      {{ $t('publicDashboardAuthLogin.title') }}
    </h2>
    <div>
      <Error :error="error"></Error>
      <form @submit.prevent="authorizeDashboard">
        <FormGroup
          small-label
          required
          :helper-text="$t('publicDashboardAuthLogin.description')"
          :error="fieldHasErrors('password')"
          class="margin-bottom-2"
        >
          <FormInput
            ref="passwordInput"
            v-model="v$.values.password.$model"
            size="large"
            :error="fieldHasErrors('password')"
            type="password"
          ></FormInput>

          <template #error>
            <span>
              {{ v$.values.password.$errors[0]?.$message }}
            </span>
          </template>
        </FormGroup>

        <div class="public-view-auth__actions">
          <Button
            type="primary"
            size="large"
            :loading="loading"
            :disabled="loading"
          >
            {{ $t('publicDashboardAuthLogin.enter') }}
          </Button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHead, useState } from '#imports'
import { useVuelidate } from '@vuelidate/core'
import { required, helpers } from '@vuelidate/validators'

import Error from '@jadawel/modules/core/components/Error'
import { isRelativeUrl } from '@jadawel/modules/core/utils/url'
import DashboardShareService from '@jadawel/modules/arabase/services/dashboardShare'

definePageMeta({
  layout: 'login',
})

const route = useRoute()
const router = useRouter()
const nuxtApp = useNuxtApp()
const { $store, $client, $i18n } = nuxtApp

const originalLanguageBeforeDetect = ref($i18n.locale.value)
const detectedLocale = useState(
  'public-dashboard-login-detected-locale',
  () => {
    return $i18n.getBrowserLocale() || $i18n.defaultLocale
  }
)
$i18n.locale.value = detectedLocale.value
await $i18n.loadLocaleMessages(detectedLocale.value)

useHead({ title: 'Password protected dashboard' })

const loading = ref(false)
const error = ref({ visible: false, title: '', message: '' })
const passwordInput = ref(null)

const values = reactive({ password: '' })
const rules = {
  values: {
    password: {
      required: helpers.withMessage($i18n.t('error.requiredField'), required),
    },
  },
}
const v$ = useVuelidate(rules, { values }, { $lazy: true })

function fieldHasErrors(fieldName) {
  return v$.value.values[fieldName]?.$error || false
}

function showError(title, message) {
  error.value = { visible: true, title, message }
}

function hideError() {
  error.value = { visible: false, title: '', message: '' }
}

async function authorizeDashboard() {
  hideError()
  loading.value = true

  try {
    const slug = route.params.slug
    const rsp = await DashboardShareService($client).authenticate(
      slug,
      values.password
    )

    // Same per-slug cookie the shared views use, so the visitor is not asked
    // again on the next visit until the slug or password is rotated.
    await $store.dispatch('page/view/public/setAuthToken', {
      slug,
      token: rsp.data.access_token,
    })

    const { original } = route.query
    if (original && isRelativeUrl(original)) {
      router.push(original)
    } else {
      router.push({ name: 'arabase-public-dashboard', params: { slug } })
    }
  } catch (e) {
    const statusCode = e.response?.status
    if (statusCode === 401) {
      $store.dispatch('toast/setAuthorizationError', false)
      showError(
        $i18n.t('publicDashboardAuthLogin.error.incorrectPasswordTitle'),
        $i18n.t('publicDashboardAuthLogin.error.incorrectPasswordText')
      )
    } else {
      showError(
        $i18n.t('error.errorTitle'),
        e.message || $i18n.t('error.errorMessage')
      )
    }
    loading.value = false
  }
}

onMounted(() => {
  nextTick(() => {
    passwordInput.value?.focus()
  })
})

onBeforeUnmount(() => {
  $i18n.locale.value = originalLanguageBeforeDetect.value
})
</script>
