import { registerRealtimeEvents } from '@jadawel/modules/builder/realtime'

export default defineNuxtPlugin({
  name: 'builder-realtime',
  dependsOn: ['realtime'],
  async setup(nuxtApp) {
    registerRealtimeEvents(nuxtApp.$realtime)
  },
})
