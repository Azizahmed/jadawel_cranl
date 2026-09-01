<template>
  <div>
    <template v-if="page === 'list'">
      <h2 class="box__title">{{ $t('mcpEndpointSettings.title') }}</h2>
      <div class="align-right">
        <button class="button button--primary" @click="page = 'create'">
          {{ $t('mcpEndpointSettings.createEndpoint') }}
          <i class="iconoir-plus"></i>
        </button>
      </div>
      <Error :error="error"></Error>
      <div v-if="listLoading" class="loading"></div>
      <div v-else>
        <p v-if="endpoints.length === 0" class="margin-top-3">
          {{ $t('mcpEndpointSettings.noEndpointsMessage') }}
        </p>
        <div
          v-for="endpoint in endpoints"
          :key="endpoint.id"
          class="mcp-protected-endpoint-settings__item"
        >
          <McpEndpoint
            :endpoint="endpoint"
            @deleted="deleteEndpoint(endpoint.id)"
          />
          <dl
            class="mcp-protected-endpoint-settings__status"
            aria-live="polite"
          >
            <div>
              <dt>{{ $t('mcpProtection.protectedCountLabel') }}</dt>
              <dd>
                {{
                  $t('mcpProtection.protectedCount', {
                    count: protectedFieldCount(endpoint),
                  })
                }}
              </dd>
            </div>
            <div>
              <dt>{{ $t('mcpProtection.lifecycleLabel') }}</dt>
              <dd :data-status="lifecycleStatus(endpoint)">
                {{ $t(`mcpProtection.lifecycle.${lifecycleStatus(endpoint)}`) }}
              </dd>
            </div>
          </dl>
          <button
            type="button"
            class="button margin-top-1 margin-bottom-1"
            :data-test-id="`edit-protection-${endpoint.id}`"
            @click="editingEndpointId = endpoint.id"
          >
            {{
              $t('mcpProtection.editEndpointAction', {
                name: endpoint.name,
              })
            }}
          </button>
          <McpProtectionPolicyEditor
            v-if="editingEndpointId === endpoint.id"
            :endpoint="endpoint"
            :applications="applications"
            @cancel="editingEndpointId = null"
            @saved="policySaved"
          />
        </div>
      </div>
    </template>
    <template v-else>
      <h2 class="box__title">{{ $t('mcpEndpointSettings.createNewTitle') }}</h2>
      <McpProtectionFlow
        :workspaces="workspaces"
        :applications="applications"
        @created="endpointCreated"
      />
      <button class="button margin-top-2" @click="page = 'list'">
        {{ $t('mcpEndpointSettings.backToOverview') }}
      </button>
    </template>
  </div>
</template>

<script>
import { mapState } from 'vuex'

import error from '@jadawel/modules/core/mixins/error'
import McpEndpoint from '@jadawel/modules/core/components/settings/McpEndpoint'
import McpEndpointService from '@jadawel/modules/core/services/mcpEndpoint'
import McpProtectionFlow from '@jadawel/modules/arabase/mcp/components/McpProtectionFlow'
import McpProtectionPolicyEditor from '@jadawel/modules/arabase/mcp/components/McpProtectionPolicyEditor'
import ProtectionPolicyService from '@jadawel/modules/arabase/mcp/services/protectionPolicy'

export default {
  name: 'McpProtectedEndpointSettings',
  components: { McpEndpoint, McpProtectionFlow, McpProtectionPolicyEditor },
  mixins: [error],
  data() {
    return {
      page: 'list',
      endpoints: [],
      listLoading: true,
      editingEndpointId: null,
    }
  },
  computed: {
    ...mapState({
      workspaces: (state) => state.workspace.items,
      applications: (state) => state.application.items,
    }),
  },
  async mounted() {
    try {
      const [{ data }, summariesResult] = await Promise.all([
        McpEndpointService(this.$client).fetchAll(),
        ProtectionPolicyService(this.$client)
          .fetchSummaries()
          .catch(() => ({ data: [] })),
      ])
      const summaries = new Map(
        summariesResult.data.map((summary) => [summary.endpoint_id, summary])
      )
      this.endpoints = data.map((endpoint) => ({
        ...endpoint,
        protection_summary: summaries.get(endpoint.id) || null,
      }))
    } catch (error) {
      this.handleError(error, 'endpoint')
    } finally {
      this.listLoading = false
    }
  },
  methods: {
    protectedFieldCount(endpoint) {
      return (
        endpoint.protection_summary?.protected_field_count ??
        endpoint.protection_policy?.protected_field_count ??
        0
      )
    },
    lifecycleStatus(endpoint) {
      return (
        endpoint.protection_summary?.lifecycle_status ??
        endpoint.protection_policy?.lifecycle_status ??
        'active'
      )
    },
    endpointCreated(endpoint) {
      this.endpoints.push(endpoint)
      this.page = 'list'
    },
    deleteEndpoint(endpointId) {
      this.endpoints = this.endpoints.filter(
        (endpoint) => endpoint.id !== endpointId
      )
    },
    policySaved(policy) {
      if (policy?.endpoint_id) {
        const endpoint = this.endpoints.find(
          (item) => item.id === policy.endpoint_id
        )
        if (endpoint) {
          endpoint.protection_policy = policy
          endpoint.protection_summary = {
            ...(endpoint.protection_summary || {}),
            endpoint_id: policy.endpoint_id,
            protected_field_count: policy.protected_field_count,
            lifecycle_status: policy.lifecycle_status,
            safe_reason_code: policy.safe_reason_code,
          }
        }
      }
      this.editingEndpointId = null
    },
  },
}
</script>
