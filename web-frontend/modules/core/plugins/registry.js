import { defineNuxtPlugin } from '#app'
import { Registry } from '@jadawel/modules/core/registry'

export default defineNuxtPlugin({
  name: 'registry',
  setup(nuxtApp) {
    const registry = new Registry()
    nuxtApp.provide('registry', registry)
  },
})
