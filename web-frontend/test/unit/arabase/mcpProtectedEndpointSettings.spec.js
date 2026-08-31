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

  test('keeps each protection action with the endpoint it edits', async () => {
    fetchAll.mockResolvedValue({
      data: [
        { id: 1, name: 'Jadawel MCP' },
        { id: 2, name: 'Data' },
      ],
    })
    const wrapper = await mountSuspended(McpProtectedEndpointSettings, {
      global: {
        mocks: {
          $client: {},
          $t: (key, values) => (values?.name ? `${key}:${values.name}` : key),
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
          McpProtectionPolicyEditor: {
            props: ['endpoint'],
            template:
              '<div :data-test-id="`policy-editor-${endpoint.id}`"></div>',
          },
        },
      },
    })

    const endpointGroups = wrapper.findAll(
      '.mcp-protected-endpoint-settings__item'
    )
    expect(endpointGroups).toHaveLength(2)
    expect(
      endpointGroups[0].findAll('[data-test-id^="edit-protection-"]')
    ).toHaveLength(1)
    expect(
      endpointGroups[1].findAll('[data-test-id^="edit-protection-"]')
    ).toHaveLength(1)
    expect(endpointGroups[0].get('button').text()).toBe(
      'mcpProtection.editEndpointAction:Jadawel MCP'
    )
    expect(endpointGroups[1].get('button').text()).toBe(
      'mcpProtection.editEndpointAction:Data'
    )
    expect(endpointGroups[0].get('button').classes()).toContain(
      'margin-bottom-1'
    )

    await endpointGroups[1]
      .get('[data-test-id="edit-protection-2"]')
      .trigger('click')
    expect(
      endpointGroups[1].get('[data-test-id="policy-editor-2"]').exists()
    ).toBe(true)
    expect(
      endpointGroups[0].find('[data-test-id="policy-editor-1"]').exists()
    ).toBe(false)
  })
})
