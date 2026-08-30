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
        <McpEndpoint
          v-for="endpoint in endpoints"
          :key="endpoint.id"
          :endpoint="endpoint"
          @deleted="deleteEndpoint(endpoint.id)"
        />
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

export default {
  name: 'McpProtectedEndpointSettings',
  components: { McpEndpoint, McpProtectionFlow },
  mixins: [error],
  data() {
    return { page: 'list', endpoints: [], listLoading: true }
  },
  computed: {
    ...mapState({
      workspaces: (state) => state.workspace.items,
      applications: (state) => state.application.items,
    }),
  },
  async mounted() {
    try {
      const { data } = await McpEndpointService(this.$client).fetchAll()
      this.endpoints = data
    } catch (error) {
      this.handleError(error, 'endpoint')
    } finally {
      this.listLoading = false
    }
  },
  methods: {
    endpointCreated(endpoint) {
      this.endpoints.push(endpoint)
      this.page = 'list'
    },
    deleteEndpoint(endpointId) {
      this.endpoints = this.endpoints.filter(
        (endpoint) => endpoint.id !== endpointId
      )
    },
  },
}
</script>
