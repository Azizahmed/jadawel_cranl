import { registerRealtimeEvents } from '@jadawel/modules/database/realtime'

export default defineNuxtPlugin({
  name: 'database-realtime',
  dependsOn: ['realtime'],
  async setup(nuxtApp) {
    registerRealtimeEvents(nuxtApp.$realtime)
  },
})
