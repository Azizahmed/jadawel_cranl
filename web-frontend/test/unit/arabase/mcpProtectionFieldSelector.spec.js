import { mountSuspended } from '@nuxt/test-utils/runtime'
import { vi } from 'vitest'

import McpProtectionFieldSelector from '@jadawel/modules/arabase/mcp/components/McpProtectionFieldSelector'

const fetchAll = vi.fn()

vi.mock('@jadawel/modules/database/services/field', () => ({
  default: () => ({ fetchAll }),
}))

describe('McpProtectionFieldSelector', () => {
  beforeEach(() => {
    fetchAll.mockReset()
  })

  test('loads a table lazily and selects fields by stable identity', async () => {
    fetchAll.mockResolvedValue({
      data: [
        { id: 41, name: 'National ID', type: 'text' },
        { id: 42, name: 'Active', type: 'boolean' },
      ],
    })
    const wrapper = await mountSuspended(McpProtectionFieldSelector, {
      props: {
        databases: [
          {
            id: 10,
            name: 'Customers',
            tables: [{ id: 20, name: 'People' }],
          },
        ],
        modelValue: [],
      },
      global: { mocks: { $client: {}, $t: (key) => key } },
    })

    await wrapper.get('[data-test-id="expand-table-20"]').trigger('click')
    await wrapper.get('[data-test-id="protected-field-41"]').setValue(true)

    expect(fetchAll).toHaveBeenCalledWith(20)
    expect(wrapper.emitted('update:modelValue')[0][0]).toStrictEqual([
      {
        id: 41,
        name: 'National ID',
        type: 'text',
        table: { id: 20, name: 'People' },
        database: { id: 10, name: 'Customers' },
      },
    ])
  })
})
