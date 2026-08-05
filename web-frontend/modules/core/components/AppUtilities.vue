<template>
  <!--
    Jadawel: workspace utilities pinned to the top inline-end corner of the
    content area — the top-left in Arabic. Rendered once by the app layout
    rather than by each page header, because there are five separate header
    components (table, dashboard, automation, builder, workspace home) and the
    group has to appear on all of them. `.layout__col-2-1` and
    `.dashboard__header` reserve the band with a padding, so this never lands on
    top of the header's own controls.

    There is deliberately no search icon here: the view header already carries
    one, and two magnifiers in the same bar is exactly the duplication this
    layout is meant to remove. Global search stays on Ctrl/⌘ K.
  -->
  <div class="app-utilities">
    <a
      v-tooltip="$t('sidebar.notifications')"
      class="app-utilities__item"
      :aria-label="$t('sidebar.notifications')"
      @click="$refs.notificationPanel.toggle($event.currentTarget)"
    >
      <i class="iconoir-bell"></i>
      <BadgeCounter
        v-show="unreadNotificationCount"
        class="app-utilities__badge"
        :count="unreadNotificationCount"
        :limit="10"
      >
      </BadgeCounter>
    </a>

    <nuxt-link
      v-if="
        $hasPermission(
          'workspace.list_workspace_users',
          workspace,
          workspace.id
        )
      "
      v-slot="{ href, navigate, isExactActive }"
      custom
      :to="{
        name: 'settings-members',
        params: { workspaceId: workspace.id },
      }"
    >
      <a
        v-tooltip="membersTooltip"
        :href="href"
        class="app-utilities__item"
        :class="{ 'app-utilities__item--active': isExactActive }"
        :aria-label="membersTooltip"
        data-highlight="members"
        @click="navigate"
      >
        <i class="iconoir-group"></i>
      </a>
    </nuxt-link>

    <a
      v-if="
        $hasPermission('workspace.create_invitation', workspace, workspace.id)
      "
      v-tooltip="$t('sidebar.inviteOthers')"
      class="app-utilities__item"
      :aria-label="$t('sidebar.inviteOthers')"
      @click="$refs.inviteModal.show()"
    >
      <i class="iconoir-add-user"></i>
    </a>

    <a
      v-tooltip="$t('sidebar.trash')"
      class="app-utilities__item"
      :aria-label="$t('sidebar.trash')"
      @click="$refs.trashModal.show()"
    >
      <i class="iconoir-bin"></i>
    </a>

    <NotificationPanel ref="notificationPanel" />
    <WorkspaceMemberInviteModal
      ref="inviteModal"
      :workspace="workspace"
      @invite-submitted="handleInvite"
    />
    <TrashModal ref="trashModal" :initial-workspace="workspace"></TrashModal>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

import TrashModal from '@jadawel/modules/core/components/trash/TrashModal'
import NotificationPanel from '@jadawel/modules/core/components/NotificationPanel'
import WorkspaceMemberInviteModal from '@jadawel/modules/core/components/workspace/WorkspaceMemberInviteModal'
import BadgeCounter from '@jadawel/modules/core/components/BadgeCounter'

export default {
  name: 'AppUtilities',
  components: {
    TrashModal,
    NotificationPanel,
    WorkspaceMemberInviteModal,
    BadgeCounter,
  },
  props: {
    workspace: {
      type: Object,
      required: true,
    },
  },
  computed: {
    /**
     * The member count used to sit next to a text label. An icon has no room
     * for it, so it moves into the tooltip rather than being dropped.
     */
    membersTooltip() {
      const label = this.$t('sidebar.members')
      const count = this.workspace.users?.length
      return count ? `${label} (${count})` : label
    },
    ...mapGetters({
      unreadNotificationCount: 'notification/getUnreadCount',
    }),
  },
  methods: {
    handleInvite() {
      if (this.$route.name !== 'settings-invites') {
        this.$router.push({
          name: 'settings-invites',
          params: { workspaceId: this.workspace.id },
        })
      }
    },
  },
}
</script>
