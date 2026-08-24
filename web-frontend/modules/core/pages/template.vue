<template>
  <TemplatePreview v-if="template" :template="template" />
  <div v-else>error</div>
</template>

<script setup>
import TemplatePreview from '@jadawel/modules/core/components/template/TemplatePreview'
import TemplateService from '@jadawel/modules/core/services/template'
import { getPageErrorStatus } from '@jadawel/modules/core/utils/error'

const route = useRoute()
const { $client } = useNuxtApp()
const slug = route.params.slug

const { data: template, error } = await useAsyncData(
  `public-template-${slug}`,
  async () => {
    const { data } = await TemplateService($client).fetch(slug)
    return data
  }
)

if (error.value) {
  const statusCode = getPageErrorStatus(error.value)
  throw createError({
    statusCode,
    statusMessage:
      statusCode === 404 ? 'Template not found' : 'Failed to load template',
  })
}
</script>
