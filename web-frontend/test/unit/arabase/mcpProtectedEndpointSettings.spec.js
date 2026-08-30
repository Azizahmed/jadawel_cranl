import { mountSuspended } from '@nuxt/test-utils/runtime'
import { vi } from 'vitest'

import McpProtectedEndpointSettings from '@jadawel/modules/arabase/mcp/components/McpProtectedEndpointSettings'
import { McpProtectedEndpointSettingsType } from '@jadawel/modules/arabase/mcp/settingsTypes'

const fetchAll = vi.fn()

vi.mock('@jadawel/modules/core/services/mcpEndpoint', () => ({
  default: () => ({ fetchAll }),
}))

describe('McpProtectedEndpointSettings', () => {
  beforeEach(() => {
    fetchAll.mockReset()
  })

  test('replaces the core settings type and keeps endpoint list state current', async () => {
    const existing = { id: 1, name: 'Existing endpoint' }
    fetchAll.mockResolvedValue({ data: [existing] })
    const wrapper = await mountSuspended(McpProtectedEndpointSettings, {
      global: {
        mocks: {
          $client: {},
          $t: (key) => key,
          $store: {
            state: {
              workspace: { items: [{ id: 7, name: 'Operations' }] },
              application: { items: [] },
            },
          },
        },
        stubs: {
          Error: true,
          McpEndpoint: true,
          McpProtectionFlow: true,
        },
      },
    })

    expect(fetchAll).toHaveBeenCalledOnce()
    expect(wrapper.vm.endpoints).toStrictEqual([existing])

    const created = { id: 2, name: 'Protected endpoint' }
    wrapper.vm.page = 'create'
    wrapper.vm.endpointCreated(created)
    expect(wrapper.vm.page).toBe('list')
    expect(wrapper.vm.endpoints).toStrictEqual([existing, created])

    wrapper.vm.deleteEndpoint(existing.id)
    expect(wrapper.vm.endpoints).toStrictEqual([created])

    const settingsType = new McpProtectedEndpointSettingsType({})
    expect(McpProtectedEndpointSettingsType.getType()).toBe('mcp-endpoint')
    expect(settingsType.getComponent()).toBe(McpProtectedEndpointSettings)
  })
})
