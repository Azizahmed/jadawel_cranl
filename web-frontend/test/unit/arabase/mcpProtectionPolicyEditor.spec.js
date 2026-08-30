import { mountSuspended } from '@nuxt/test-utils/runtime'
import { vi } from 'vitest'

import McpProtectionPolicyEditor from '@jadawel/modules/arabase/mcp/components/McpProtectionPolicyEditor'

const fetchPolicy = vi.fn()
const replacePolicy = vi.fn()
const reactivatePolicy = vi.fn()

vi.mock('@jadawel/modules/arabase/mcp/services/protectionPolicy', () => ({
  default: () => ({ fetchPolicy, replacePolicy, reactivatePolicy }),
}))

describe('McpProtectionPolicyEditor', () => {
  beforeEach(() => {
    fetchPolicy.mockReset()
    replacePolicy.mockReset()
    reactivatePolicy.mockReset()
  })

  test('offers explicit reactivation for a suspended policy', async () => {
    const policy = {
      revision: 4,
      lifecycle_status: 'suspended',
      fields: [
        {
          id: 41,
          name: 'National ID',
          type: 'text',
          table: { id: 20, name: 'People' },
          database: { id: 10, name: 'Customers' },
        },
      ],
    }
    fetchPolicy.mockResolvedValue({ data: policy })
    reactivatePolicy.mockResolvedValue({
      data: { ...policy, revision: 5, lifecycle_status: 'active' },
    })

    const wrapper = await mountSuspended(McpProtectionPolicyEditor, {
      props: {
        endpoint: { id: 9, workspace_id: 1 },
        applications: [],
      },
      global: {
        mocks: { $client: {}, $t: (key) => key },
        stubs: {
          Error: true,
          McpProtectionFieldSelector: true,
        },
      },
    })

    await wrapper.get('button.button--small').trigger('click')

    expect(reactivatePolicy).toHaveBeenCalledWith(9, 4)
    expect(wrapper.emitted('saved')[0][0]).toStrictEqual({
      ...policy,
      revision: 5,
      lifecycle_status: 'active',
    })
  })
})
