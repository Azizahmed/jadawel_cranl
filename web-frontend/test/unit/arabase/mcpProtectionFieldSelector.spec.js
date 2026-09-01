import { mountSuspended } from '@nuxt/test-utils/runtime'
import { vi } from 'vitest'
import flushPromises from 'flush-promises'

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

  test('requires scope confirmation before selecting a whole database', async () => {
    fetchAll.mockImplementation(async (tableId) => ({
      data: [{ id: tableId + 100, name: `Field ${tableId}`, type: 'text' }],
    }))
    const wrapper = await mountSuspended(McpProtectionFieldSelector, {
      props: {
        databases: [
          {
            id: 10,
            name: 'Customers',
            tables: [
              { id: 20, name: 'People' },
              { id: 21, name: 'Companies' },
            ],
          },
        ],
        modelValue: [],
      },
      global: { mocks: { $client: {}, $t: (key) => key } },
    })

    await wrapper.get('[data-test-id="select-database-10"]').trigger('click')
    expect(wrapper.find('[data-test-id="confirm-database-10"]').exists()).toBe(
      true
    )
    await wrapper
      .find('.mcp-protection-selector__scope-confirmation input')
      .setValue(true)
    await wrapper.get('[data-test-id="confirm-database-10"]').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('update:modelValue')[0][0]).toHaveLength(2)
    expect(fetchAll).toHaveBeenCalledWith(20)
    expect(fetchAll).toHaveBeenCalledWith(21)
  })

  test('offers an explicit retry after a metadata load failure', async () => {
    fetchAll.mockRejectedValueOnce(new Error('temporary failure'))
    const wrapper = await mountSuspended(McpProtectionFieldSelector, {
      props: {
        databases: [
          { id: 10, name: 'Customers', tables: [{ id: 20, name: 'People' }] },
        ],
        modelValue: [],
      },
      global: { mocks: { $client: {}, $t: (key) => key } },
    })

    await wrapper.get('[data-test-id="expand-table-20"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-test-id="retry-fields-20"]').exists()).toBe(true)

    fetchAll.mockResolvedValueOnce({
      data: [{ id: 41, name: 'National ID', type: 'text' }],
    })
    await wrapper.get('[data-test-id="retry-fields-20"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-test-id="protected-field-41"]').exists()).toBe(
      true
    )
  })
})
