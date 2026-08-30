<template>
  <div
    v-if="visible && state && state.artifact_state !== 'unmanaged'"
    class="mcp-artifact-approval"
    role="status"
    aria-live="polite"
  >
    <span class="mcp-artifact-approval__label">
      {{ $t('mcpArtifactApproval.label') }}
    </span>
    <span class="mcp-artifact-approval__state">
      {{ stateLabel }}
    </span>
    <button
      v-if="state.artifact_state === 'pending_approval' && state.draft_id"
      type="button"
      class="button button--small button--primary"
      :disabled="saving"
      :data-test-id="'approve-mcp-artifact'"
      @click="approve"
    >
      {{
        saving
          ? $t('mcpArtifactApproval.approving')
          : $t('mcpArtifactApproval.approve')
      }}
    </button>
  </div>
</template>

<script>
import ArtifactApprovalService from '@jadawel/modules/arabase/mcp/services/artifactApproval'

export default {
  name: 'McpArtifactApprovalPanel',
  props: {
    view: { type: Object, required: true },
    readOnly: { type: Boolean, required: true },
    canUpdate: { type: Boolean, required: true },
  },
  emits: ['approved', 'state'],
  data() {
    return {
      state: null,
      saving: false,
    }
  },
  computed: {
    visible() {
      return !this.readOnly && this.canUpdate
    },
    stateLabel() {
      if (!this.state) {
        return ''
      }
      return this.$t(`mcpArtifactApproval.states.${this.state.artifact_state}`)
    },
  },
  watch: {
    'view.id'() {
      this.load()
    },
  },
  mounted() {
    this.load()
  },
  methods: {
    async load() {
      if (!this.visible) {
        this.state = null
        return
      }
      try {
        const { data } = await ArtifactApprovalService(this.$client).fetchState(
          this.view.id
        )
        this.state = data
        this.$emit('state', data)
      } catch {
        // A page without an MCP artifact is the normal path. Keep this panel
        // silent when the state endpoint is unavailable to a read-only user.
        this.state = null
      }
    },
    async approve() {
      if (!this.state?.draft_id) {
        return
      }
      this.saving = true
      try {
        const { data } = await ArtifactApprovalService(
          this.$client
        ).approveDraft(this.state.draft_id)
        this.state = data
        this.$emit('state', data)
        this.$emit('approved')
      } finally {
        this.saving = false
      }
    },
  },
}
</script>
