<template>
  <TemplatePreview v-if="template" :template="template" />
  <div v-else>error</div>
</template>

<script setup>
import TemplatePreview from '@jadawel/modules/core/components/template/TemplatePreview'
import TemplateService from '@jadawel/modules/core/services/template'

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
  throw createError({
    statusCode: 404,
    statusMessage: 'Template not found',
  })
}
</script>
