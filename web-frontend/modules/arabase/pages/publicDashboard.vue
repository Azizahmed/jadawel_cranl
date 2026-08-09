<template>
  <div class="public-dashboard">
    <Toasts></Toasts>
    <DashboardContent
      v-if="dashboard"
      :dashboard="dashboard"
      store-prefix="public/"
    />
  </div>
</template>

<script setup>
import { computed, ref, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import {
  useAsyncData,
  useNuxtApp,
  useState,
  createError,
  navigateTo,
} from '#app'
import { useHead } from '#imports'

import Toasts from '@jadawel/modules/core/components/toasts/Toasts'
import DashboardContent from '@jadawel/modules/dashboard/components/DashboardContent'
import { PUBLIC_PLACEHOLDER_ENTITY_ID } from '@jadawel/modules/database/utils/constants'

definePageMeta({
  middleware: ['settings'],
})

const route = useRoute()
const nuxtApp = useNuxtApp()
const { $store, $i18n } = nuxtApp

// A visitor has no account and therefore no language preference to read; follow
// the browser like the public view pages do, and restore on the way out so a
// logged-in owner previewing the link keeps their own locale.
const originalLanguageBeforeDetect = ref($i18n.locale.value)
const detectedLocale = useState('public-dashboard-detected-locale', () => {
  return $i18n.getBrowserLocale() || $i18n.defaultLocale
})
$i18n.locale.value = detectedLocale.value
await $i18n.loadLocaleMessages(detectedLocale.value)

const { data, error } = await useAsyncData(
  `arabase-public-dashboard-${route.params.slug}`,
  async () => {
    const slug = route.params.slug
    const authToken = await $store.dispatch(
      'page/view/public/setAuthTokenFromCookiesIfNotSet',
      { slug }
    )

    try {
      const dashboard = await $store.dispatch(
        'public/dashboardApplication/fetchInitial',
        { slug, authToken }
      )

      return {
        dashboard: {
          ...dashboard,
          // `DashboardContent` and every widget ask `$hasPermission(...,
          // dashboard.workspace.id)`. The placeholder id belongs to no
          // workspace, so every permission check resolves to false and the
          // page renders read-only.
          workspace: { id: PUBLIC_PLACEHOLDER_ENTITY_ID },
        },
      }
    } catch (e) {
      const statusCode = e.response?.status
      if (statusCode === 401) {
        return {
          redirect: {
            name: 'arabase-public-dashboard-auth',
            params: { slug },
            query: { original: route.path },
          },
        }
      } else if (statusCode === 404) {
        throw createError({ statusCode: 404, message: 'Dashboard not found.' })
      }
      throw createError({
        statusCode: 500,
        message: e.message || 'Error loading dashboard.',
        fatal: true,
      })
    }
  }
)

if (error.value) {
  throw error.value
}

if (data.value?.redirect) {
  await navigateTo(data.value.redirect)
}

const dashboard = computed(() => data.value?.dashboard)

useHead(() => ({ title: dashboard.value?.name || '' }))

onBeforeUnmount(() => {
  $i18n.locale.value = originalLanguageBeforeDetect.value
  $store.dispatch('public/dashboardApplication/reset')
})
</script>
