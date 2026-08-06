import pkg from '../../../package.json'

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.provide('jadawelVersion', pkg.version)
})
