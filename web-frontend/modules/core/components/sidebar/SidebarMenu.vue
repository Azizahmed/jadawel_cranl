<template>
  <div class="sidebar__section" ph-autocapture="sidebar" data-highlight="menu">
    <!--
      Jadawel: the workspace utilities (search, notifications, members, invite,
      trash) are destinations you dip into, not places you navigate to and stay.
      Rendering them as five labelled rows cost ~170px at the top of every page
      and pushed the actual content — the databases — below the fold. They are
      icon buttons here instead. Every one carries a tooltip and an aria-label,
      because without the label the icon alone is a guess.
    -->
    <div class="sidebar__utilities">
      <a
        v-tooltip="searchTooltip"
        class="sidebar__utility"
        :aria-label="searchTooltip"
        @click="openWorkspaceSearch"
      >
        <i class="iconoir-search"></i>
      </a>

      <a
        v-tooltip="$t('sidebar.notifications')"
        class="sidebar__utility"
        :aria-label="$t('sidebar.notifications')"
        @click="$refs.notificationPanel.toggle($event.currentTarget)"
      >
        <i class="iconoir-bell"></i>
        <BadgeCounter
          v-show="unreadNotificationCount"
          class="sidebar__utility-badge"
          :count="unreadNotificationCount"
          :limit="10"
        >
        </BadgeCounter>
      </a>

      <nuxt-link
        v-if="
          $hasPermission(
            'workspace.list_workspace_users',
            selectedWorkspace,
            selectedWorkspace.id
          )
        "
        v-slot="{ href, navigate, isExactActive }"
        custom
        :to="{
          name: 'settings-members',
          params: {
            workspaceId: selectedWorkspace.id,
          },
        }"
      >
        <a
          v-tooltip="membersTooltip"
          :href="href"
          class="sidebar__utility"
          :class="{ 'sidebar__utility--active': isExactActive }"
          :aria-label="membersTooltip"
          data-highlight="members"
          @click="navigate"
        >
          <i class="iconoir-group"></i>
        </a>
      </nuxt-link>

      <a
        v-if="
          $hasPermission(
            'workspace.create_invitation',
            selectedWorkspace,
            selectedWorkspace.id
          )
        "
        v-tooltip="$t('sidebar.inviteOthers')"
        class="sidebar__utility"
        :aria-label="$t('sidebar.inviteOthers')"
        @click="$refs.inviteModal.show()"
      >
        <i class="iconoir-add-user"></i>
      </a>

      <a
        v-tooltip="$t('sidebar.trash')"
        class="sidebar__utility"
        :aria-label="$t('sidebar.trash')"
        @click="$refs.trashModal.show()"
      >
        <i class="iconoir-bin"></i>
      </a>
    </div>

    <ul class="tree">
      <nuxt-link
        v-slot="{ href, navigate, isExactActive }"
        custom
        :to="{
          name: 'workspace',
          params: {
            workspaceId: selectedWorkspace.id,
          },
        }"
      >
        <li
          class="tree__item"
          :class="{
            active: isExactActive,
          }"
        >
          <div class="tree__action sidebar__action">
            <a :href="href" class="tree__link" @click="navigate">
              <i class="tree__icon iconoir-home-simple"></i>
              <span class="tree__link-text">
                <span class="sidebar__item-name">{{ $t('sidebar.home') }}</span>
              </span>
            </a>
          </div>
        </li>
      </nuxt-link>

      <component
        :is="component"
        v-for="(component, index) in sidebarWorkspaceComponents"
        :key="'sidebarWorkspaceComponents' + index"
        :workspace="selectedWorkspace"
        :right-sidebar-open="rightSidebarOpen"
      ></component>
    </ul>

    <!--
      Kept out of the icon row itself: these render fixed/absolute overlays, so
      leaving them as children of the flex row only invites layout surprises.
      Refs resolve regardless of where they sit in the template.
    -->
    <NotificationPanel ref="notificationPanel" />
    <WorkspaceMemberInviteModal
      ref="inviteModal"
      :workspace="selectedWorkspace"
      @invite-submitted="handleInvite"
    />
    <TrashModal ref="trashModal" :initial-workspace="selectedWorkspace">
    </TrashModal>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

import TrashModal from '@baserow/modules/core/components/trash/TrashModal'
import NotificationPanel from '@baserow/modules/core/components/NotificationPanel'
import WorkspaceMemberInviteModal from '@baserow/modules/core/components/workspace/WorkspaceMemberInviteModal'
import BadgeCounter from '@baserow/modules/core/components/BadgeCounter'
import { isMac } from '@baserow/modules/core/utils/events'

export default {
  name: 'SidebarMenu',
  components: {
    TrashModal,
    NotificationPanel,
    WorkspaceMemberInviteModal,
    BadgeCounter,
  },
  props: {
    selectedWorkspace: {
      type: Object,
      required: true,
    },
    rightSidebarOpen: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  emits: ['open-workspace-search'],
  data() {
    return {
      // Resolved after mount, never during SSR: the server has no navigator, so
      // deriving it in a computed would render 'Ctrl' server-side and '⌘' on a
      // Mac client, and the aria-label would mismatch on hydration.
      isMacClient: false,
    }
  },
  computed: {
    sidebarWorkspaceComponents() {
      return Object.values(this.$registry.getAll('plugin'))
        .flatMap((plugin) =>
          plugin.getSidebarWorkspaceComponents(this.selectedWorkspace)
        )
        .filter((component) => component !== null)
    },
    /**
     * The Ctrl/⌘ K hint lived in the search box that this row replaces. Folding
     * it into the tooltip is what keeps the shortcut discoverable now that the
     * only affordance is an icon.
     */
    searchTooltip() {
      return this.$t('sidebar.searchTooltip', { shortcut: this.modifierKey })
    },
    modifierKey() {
      return this.isMacClient ? '⌘' : 'Ctrl'
    },
    /**
     * The member count used to sit next to the label. The icon has no room for
     * it, so it moves into the tooltip rather than being dropped.
     */
    membersTooltip() {
      const label = this.$t('sidebar.members')
      const count = this.selectedWorkspace.users?.length
      return count ? `${label} (${count})` : label
    },
    ...mapGetters({
      unreadNotificationCount: 'notification/getUnreadCount',
    }),
  },
  mounted() {
    this.isMacClient = isMac()
  },
  methods: {
    openWorkspaceSearch() {
      this.$emit('open-workspace-search')
    },

    handleInvite(event) {
      if (this.$route.name !== 'settings-invites') {
        this.$router.push({
          name: 'settings-invites',
          params: {
            workspaceId: this.selectedWorkspace.id,
          },
        })
      }
    },
  },
}
</script>
