<template>
  <div>
    <SidebarApplication
      ref="sidebarApplication"
      :workspace="workspace"
      :application="application"
      :highlighted="isAppSelected(application)"
      @selected="selected"
    >
      <template v-if="isAppSelected(application)" #body></template>
    </SidebarApplication>
  </div>
</template>

<script>
import SidebarApplication from '@jadawel/modules/core/components/sidebar/SidebarApplication'
import { mapGetters } from 'vuex'
import { notifyIf } from '@jadawel/modules/core/utils/error'
import { pageFinished } from '@jadawel/modules/core/utils/routing'
import { nextTick, useNuxtApp } from '#imports'

export default {
  name: 'SidebarComponentDashboard',
  components: {
    SidebarApplication,
  },
  props: {
    application: {
      type: Object,
      required: true,
    },
    workspace: {
      type: Object,
      required: true,
    },
  },
  setup() {
    const nuxtApp = useNuxtApp()
    return { nuxtApp }
  },
  computed: {
    ...mapGetters({
      isAppSelected: 'application/isSelected',
    }),
  },
  methods: {
    async selected(application) {
      try {
        this.$store.dispatch('application/select', application)
        await this.$router.push({
          name: 'dashboard-application',
          params: {
            dashboardId: this.application.id,
          },
        })
        await pageFinished(this.nuxtApp)
        await nextTick()
      } catch (error) {
        if (error.name !== 'NavigationDuplicated') {
          notifyIf(error, 'workspace')
        }
      }
    },
  },
}
</script>
