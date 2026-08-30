<template>
  <section class="mcp-protection-editor" aria-live="polite">
    <div v-if="loading" class="loading"></div>
    <template v-else-if="policy">
      <h3>{{ $t('mcpProtection.editTitle') }}</h3>
      <p>{{ $t('mcpProtection.editHelp') }}</p>
      <p
        v-if="policy.lifecycle_status !== 'active'"
        class="mcp-protection-editor__status"
      >
        {{ $t('mcpProtection.protectionSuspended') }}
        <button
          type="button"
          class="button button--small"
          :disabled="saving"
          @click="reactivate"
        >
          {{ $t('mcpProtection.reactivate') }}
        </button>
      </p>
      <McpProtectionFieldSelector
        v-model="selectedFields"
        :databases="databases"
      />
      <label
        v-if="removedFieldIds.length"
        class="mcp-protection-editor__confirm"
      >
        <input v-model="confirmRemoval" type="checkbox" />
        {{ $t('mcpProtection.confirmRemoval') }}
      </label>
      <Error :error="error"></Error>
      <div class="mcp-protection-flow__actions">
        <button type="button" class="button" @click="$emit('cancel')">
          {{ $t('mcpProtection.cancel') }}
        </button>
        <button
          type="button"
          class="button button--primary"
          :disabled="saving || (removedFieldIds.length > 0 && !confirmRemoval)"
          @click="save"
        >
          {{ $t('mcpProtection.saveChanges') }}
        </button>
      </div>
    </template>
  </section>
</template>

<script>
import { uuid } from '@jadawel/modules/core/utils/string'
import error from '@jadawel/modules/core/mixins/error'
import McpProtectionFieldSelector from '@jadawel/modules/arabase/mcp/components/McpProtectionFieldSelector'
import ProtectionPolicyService from '@jadawel/modules/arabase/mcp/services/protectionPolicy'

export default {
  name: 'McpProtectionPolicyEditor',
  components: { McpProtectionFieldSelector },
  mixins: [error],
  props: {
    endpoint: { type: Object, required: true },
    applications: { type: Array, required: true },
  },
  emits: ['cancel', 'saved'],
  data() {
    return {
      policy: null,
      selectedFields: [],
      loading: true,
      saving: false,
      confirmRemoval: false,
      idempotencyKey: uuid(),
    }
  },
  computed: {
    databases() {
      return this.applications.filter(
        (application) =>
          application.type === 'database' &&
          (application.workspace?.id || application.workspace_id) ===
            this.endpoint.workspace_id
      )
    },
    removedFieldIds() {
      const selected = new Set(this.selectedFields.map((field) => field.id))
      return (this.policy?.fields || [])
        .map((field) => field.id)
        .filter((fieldId) => !selected.has(fieldId))
    },
  },
  async mounted() {
    try {
      const { data } = await ProtectionPolicyService(this.$client).fetchPolicy(
        this.endpoint.id
      )
      this.policy = data
      this.selectedFields = data.fields.map((field) => ({
        id: field.id,
        name: field.name,
        type: field.type,
        table: field.table,
        database: field.database,
      }))
    } catch (loadError) {
      this.handleError(loadError, 'endpoint')
    } finally {
      this.loading = false
    }
  },
  methods: {
    async save() {
      this.saving = true
      this.hideError()
      try {
        const { data } = await ProtectionPolicyService(
          this.$client
        ).replacePolicy(
          this.endpoint.id,
          {
            protected_field_ids: this.selectedFields.map((field) => field.id),
            expected_revision: this.policy.revision,
            confirm_remove_field_ids: this.removedFieldIds,
          },
          this.idempotencyKey
        )
        this.$emit('saved', data)
      } catch (saveError) {
        this.handleError(saveError, 'endpoint')
      } finally {
        this.saving = false
      }
    },
    async reactivate() {
      this.saving = true
      this.hideError()
      try {
        const { data } = await ProtectionPolicyService(
          this.$client
        ).reactivatePolicy(this.endpoint.id, this.policy.revision)
        this.$emit('saved', data)
      } catch (reactivationError) {
        this.handleError(reactivationError, 'endpoint')
      } finally {
        this.saving = false
      }
    },
  },
}
</script>
