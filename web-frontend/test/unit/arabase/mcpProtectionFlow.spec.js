import { mountSuspended } from '@nuxt/test-utils/runtime'
import { vi } from 'vitest'

import McpProtectionFlow from '@jadawel/modules/arabase/mcp/components/McpProtectionFlow'

const createEndpoint = vi.fn()

vi.mock('@jadawel/modules/arabase/mcp/services/protectionPolicy', () => ({
  default: () => ({ createEndpoint }),
}))

describe('McpProtectionFlow', () => {
  beforeEach(() => {
    createEndpoint.mockReset()
  })

  test('reviews the exact selected policy before creating the endpoint', async () => {
    createEndpoint.mockResolvedValue({ data: { id: 9, key: 'secret-key' } })
    const wrapper = await mountSuspended(McpProtectionFlow, {
      props: {
        workspaces: [{ id: 1, name: 'Operations' }],
        applications: [],
      },
      global: {
        mocks: { $client: {}, $t: (key) => key },
        stubs: {
          McpProtectionFieldSelector: {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template:
              "<button data-test-id=\"choose-field\" @click=\"$emit('update:modelValue', [{ id: 41, name: 'National ID', type: 'text', table: { id: 20, name: 'People' }, database: { id: 10, name: 'Customers' } }])\">choose</button>",
          },
        },
      },
    })

    await wrapper.get('[data-test-id="endpoint-name"]').setValue('Assistant')
    await wrapper.get('[data-test-id="workspace-id"]').setValue('1')
    await wrapper.get('[data-test-id="next-details"]').trigger('click')
    await wrapper.get('[data-test-id="choose-field"]').trigger('click')
    await wrapper.get('[data-test-id="next-fields"]').trigger('click')

    expect(wrapper.text()).toContain('National ID')
    expect(wrapper.text()).toContain('Customers / People')

    await wrapper
      .get('[data-test-id="create-protected-endpoint"]')
      .trigger('click')

    expect(createEndpoint).toHaveBeenCalledWith(
      {
        name: 'Assistant',
        workspace_id: 1,
        protected_field_ids: [41],
        confirm_empty_policy: false,
      },
      expect.any(String)
    )
    expect(wrapper.emitted('created')[0][0]).toStrictEqual({
      id: 9,
      key: 'secret-key',
    })
  })
})
