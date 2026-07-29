<template>
  <ApplicationContext
    ref="context"
    :application="application"
    :workspace="workspace"
  >
    <template #additional-context-items>
      <li class="context__menu-item">
        <nuxt-link
          :to="{
            name: 'database-api-docs-detail',
            params: {
              databaseId: application.id,
            },
          }"
          class="context__menu-item-link"
        >
          <i class="context__menu-item-icon iconoir-book"></i>
          {{ $t('sidebar.viewAPI') }}
        </nuxt-link>
      </li>
      <li
        v-if="
          $hasPermission(
            'application.read',
            application,
            application.workspace.id
          )
        "
        class="context__menu-item"
      >
        <a class="context__menu-item-link" @click="openExportModal()">
          <i class="context__menu-item-icon iconoir-download"></i>
          {{ $t('sidebarApplication.exportDatabase') }}
        </a>
      </li>
      <!--
        Lives inside this slot, not after it: core's ApplicationContext renders
        no default slot, so anything placed outside a named slot is dropped.
        SnapshotsModal sits in the same position for the same reason.
      -->
      <ExportWorkspaceModal
        ref="exportModal"
        :workspace="workspace"
        :application="application"
      ></ExportWorkspaceModal>
    </template>
  </ApplicationContext>
</template>

<script>
import ApplicationContext from '@baserow/modules/core/components/application/ApplicationContext.vue'
import ExportWorkspaceModal from '@baserow/modules/core/components/export/ExportWorkspaceModal'
import applicationContext from '@baserow/modules/core/mixins/applicationContext'

export default {
  components: {
    ApplicationContext,
    ExportWorkspaceModal,
  },
  mixins: [applicationContext],
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
  methods: {
    openExportModal() {
      // Hide the menu first: the modal renders inside it, and leaving an open
      // context behind the modal means the next outside-click closes both.
      this.$refs.context.hide()
      this.$refs.exportModal.show()
    },
  },
}
</script>
