<template>
  <div class="public-page-view">
    <Toasts></Toasts>
    <HtmlPageView
      v-if="ready"
      :database="database"
      :table="table"
      :view="view"
      :fields="fields"
      :read-only="true"
      store-prefix="page/"
    ></HtmlPageView>
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
import HtmlPageView from '@jadawel/modules/arabase/views/components/HtmlPageView'
import ViewService from '@jadawel/modules/database/services/view'
import { PUBLIC_PLACEHOLDER_ENTITY_ID } from '@jadawel/modules/database/utils/constants'
import { DatabaseApplicationType } from '@jadawel/modules/database/applicationTypes'

/**
 * The public face of a page view.
 *
 * Deliberately not core's `pages/publicView.vue`: that renders the whole
 * `<Table>` shell — view sidebar, filter bar, row modal — which is the right
 * frame for a shared grid and the wrong one for a page that is supposed to look
 * like a document. The data loading below is the same sequence, minus the
 * chrome.
 *
 * The password gate needs no code here. `fetchPublicViewInfo` answers 401 for a
 * protected view without a valid token, and core's generic
 * `database-public-view-auth` page takes the visitor from there.
 */
definePageMeta({
  middleware: ['settings'],
})

const route = useRoute()
const nuxtApp = useNuxtApp()
const { $store, $i18n } = nuxtApp

// A visitor has no account and so no stored language preference; follow the
// browser like the other public pages do, and restore on the way out so a
// signed-in owner previewing their own link keeps their locale.
const originalLanguageBeforeDetect = ref($i18n.locale.value)
const detectedLocale = useState('public-page-view-detected-locale', () => {
  return $i18n.getBrowserLocale() || $i18n.defaultLocale
})
$i18n.locale.value = detectedLocale.value
await $i18n.loadLocaleMessages(detectedLocale.value)

const { data, error } = await useAsyncData(
  `arabase-public-page-view-${route.params.slug}`,
  async () => {
    const nuxt = useNuxtApp()
    const { $client, $registry, runWithContext } = nuxt
    const slug = route.params.slug

    const publicAuthToken = await $store.dispatch(
      'page/view/public/setAuthTokenFromCookiesIfNotSet',
      { slug }
    )

    try {
      await $store.dispatch('page/view/public/setIsPublic', true)

      const { data: info } = await ViewService($client).fetchPublicViewInfo(
        slug,
        publicAuthToken
      )

      const { applications } = await runWithContext(() =>
        $store.dispatch('application/forceSetAll', {
          applications: [
            {
              id: PUBLIC_PLACEHOLDER_ENTITY_ID,
              type: DatabaseApplicationType.getType(),
              tables: [{ id: PUBLIC_PLACEHOLDER_ENTITY_ID }],
              workspace: { id: PUBLIC_PLACEHOLDER_ENTITY_ID },
            },
          ],
        })
      )

      const database = applications[0]
      const table = database.tables[0]
      await runWithContext(() =>
        $store.dispatch('application/select', database)
      )
      await runWithContext(() =>
        $store.dispatch('table/forceSelect', { database, table })
      )

      const { fields } = await runWithContext(() =>
        $store.dispatch('field/forceSetFields', { fields: info.fields })
      )

      info.view.filters_disabled = false
      info.view.filter_type = 'AND'
      const { view } = await runWithContext(() =>
        $store.dispatch('view/forceCreate', { data: info.view })
      )
      await runWithContext(() => $store.dispatch('view/select', view))

      const viewType = $registry.get('view', view.type)
      await runWithContext(() =>
        viewType.fetch(
          { store: $store, app: nuxt },
          database,
          view,
          fields,
          'page/'
        )
      )

      return { database, table, view, fields }
    } catch (e) {
      const statusCode = e.response?.status
      if (statusCode === 401) {
        return {
          redirect: {
            name: 'database-public-view-auth',
            params: { slug },
            query: { original: route.path },
          },
        }
      } else if (statusCode === 404) {
        throw createError({ statusCode: 404, message: 'Page not found.' })
      }
      throw createError({
        statusCode: 500,
        message: e.message || 'Error loading page.',
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

const database = computed(() => data.value?.database)
const table = computed(() => data.value?.table)
const view = computed(() => data.value?.view)
const fields = computed(() => data.value?.fields || [])
const ready = computed(() => !!view.value)

useHead(() => ({ title: view.value?.name || '' }))

onBeforeUnmount(() => {
  $i18n.locale.value = originalLanguageBeforeDetect.value
  $store.dispatch('page/view/html_page/reset')
})
</script>
