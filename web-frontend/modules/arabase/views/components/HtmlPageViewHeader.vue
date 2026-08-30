<template>
  <ul v-if="!tableLoading" class="header__filter header__filter--full-width">
    <li class="header__filter-item">
      <a class="header__filter-link" @click="refresh">
        <i class="header__filter-icon iconoir-refresh-double"></i>
        <span class="header__filter-name">{{
          $t('htmlPageViewHeader.refresh')
        }}</span>
      </a>
    </li>
    <li class="header__filter-item">
      <a class="header__filter-link" @click="$refs.sourceModal.show()">
        <i class="header__filter-icon iconoir-code"></i>
        <span class="header__filter-name">{{
          $t('htmlPageViewHeader.source')
        }}</span>
      </a>
      <HtmlPageSourceModal
        ref="sourceModal"
        :view="view"
        :read-only="readOnly || !canUpdate"
        @save="updateHtml"
      ></HtmlPageSourceModal>
    </li>
    <li class="header__filter-item">
      <a
        ref="settingsLink"
        class="header__filter-link"
        @click="
          $refs.settingsContext.toggle($refs.settingsLink, 'bottom', 'left', 4)
        "
      >
        <i class="header__filter-icon iconoir-settings"></i>
        <span class="header__filter-name">{{
          $t('htmlPageViewHeader.settings')
        }}</span>
      </a>
      <HtmlPageSettingsContext
        ref="settingsContext"
        :view="view"
        :read-only="readOnly || !canUpdate"
        @update="updateSettings"
      ></HtmlPageSettingsContext>
    </li>
    <li v-if="truncated" class="header__filter-item">
      <span class="html-page-view__truncated">
        {{ $t('htmlPageViewHeader.truncated', { count, limit: rowLimit }) }}
      </span>
    </li>
  </ul>
  <McpArtifactApprovalPanel
    :view="view"
    :read-only="readOnly"
    :can-update="canUpdate"
    @approved="refresh"
    @state="artifactState = $event"
  ></McpArtifactApprovalPanel>
</template>

<script>
import { mapState } from 'vuex'

import ArtifactApprovalService from '@jadawel/modules/arabase/mcp/services/artifactApproval'
import { notifyIf } from '@jadawel/modules/core/utils/error'
import HtmlPageSettingsContext from '@jadawel/modules/arabase/views/components/HtmlPageSettingsContext'
import HtmlPageSourceModal from '@jadawel/modules/arabase/views/components/HtmlPageSourceModal'
import McpArtifactApprovalPanel from '@jadawel/modules/arabase/views/components/McpArtifactApprovalPanel'

export default {
  name: 'HtmlPageViewHeader',
  components: {
    HtmlPageSettingsContext,
    HtmlPageSourceModal,
    McpArtifactApprovalPanel,
  },
  props: {
    database: { type: Object, required: true },
    table: { type: Object, required: true },
    view: { type: Object, required: true },
    fields: { type: Array, required: true },
    readOnly: { type: Boolean, required: true },
    storePrefix: { type: String, required: true },
  },
  emits: ['refresh'],
  data() {
    return {
      artifactState: null,
    }
  },
  computed: {
    ...mapState({
      tableLoading: (state) => state.table.loading,
    }),
    count() {
      return this.$store.getters[this.storePrefix + 'view/html_page/getCount']
    },
    rowLimit() {
      return this.$store.getters[
        this.storePrefix + 'view/html_page/getRowLimit'
      ]
    },
    truncated() {
      return this.$store.getters[
        this.storePrefix + 'view/html_page/getTruncated'
      ]
    },
    canUpdate() {
      return this.$hasPermission(
        'database.table.view.update',
        this.view,
        this.database.workspace.id
      )
    },
  },
  methods: {
    refresh() {
      this.$emit('refresh')
    },
    updateHtml(html) {
      this.update({ html })
    },
    updateSettings(values) {
      this.update(values)
    },
    async update(values) {
      try {
        // A source edit on a managed MCP page is a new candidate, never a
        // direct write. The state endpoint is content-blind and provides only
        // the stable endpoint/manifest needed to submit the draft.
        if (values.html !== undefined) {
          const { data: state } = await ArtifactApprovalService(
            this.$client
          ).fetchState(this.view.id)
          this.artifactState = state
          if (
            state.artifact_state !== 'unmanaged' &&
            state.endpoint_id !== null
          ) {
            await ArtifactApprovalService(this.$client).createDraft({
              endpoint_id: state.endpoint_id,
              view_id: this.view.id,
              html: values.html,
              protected_field_ids: state.protected_field_ids || [],
              audience: state.audience || 'authenticated',
              pending_view_values: Object.fromEntries(
                Object.entries(values).filter(([key]) => key !== 'html')
              ),
            })
            return
          }
        }
        await this.$store.dispatch('view/update', {
          view: this.view,
          values,
          readOnly: this.readOnly,
        })
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
  },
}
</script>
