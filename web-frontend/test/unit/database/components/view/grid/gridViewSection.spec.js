import { nextTick } from 'vue'

import { TestApp } from '@jadawel/test/helpers/testApp'
import GridViewSection from '@jadawel/modules/database/components/view/grid/GridViewSection'

describe('GridViewSection component', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
  })

  afterEach(async () => {
    await testApp.afterEach()
  })

  test('renders fields at a negative RTL scroll offset', async () => {
    const fields = Array.from({ length: 8 }, (_, index) => ({
      id: index + 1,
      name: `Field ${index + 1}`,
      type: 'text',
      primary: index === 0,
    }))

    await testApp.store.dispatch(
      'page/view/grid/forceUpdateAllFieldOptions',
      Object.fromEntries(
        fields.map((field) => [field.id, { width: 200, hidden: false }])
      )
    )

    const wrapper = await testApp.mount(GridViewSection, {
      props: {
        visibleFields: fields,
        allVisibleFields: fields,
        allFieldsInTable: fields,
        decorationsByPlace: {},
        database: { id: 1, workspace: { id: 1 } },
        table: { id: 1, data_sync: null },
        view: { id: 1, group_bys: [] },
        readOnly: true,
        storePrefix: 'page/',
      },
      global: {
        stubs: {
          HorizontalResize: true,
          GridViewHead: true,
          GridViewPlaceholder: true,
          GridViewGroups: true,
          GridViewRowAdd: true,
          GridViewFieldFooter: true,
          GridViewRows: {
            props: ['renderedFields', 'leftOffset'],
            template: `
              <div class="test-grid-row" :data-left-offset="leftOffset">
                <div
                  v-for="field in renderedFields"
                  :key="field.id"
                  class="test-grid-cell"
                  :data-field-id="field.id"
                />
              </div>
            `,
          },
        },
      },
    })

    Object.defineProperties(wrapper.element, {
      clientWidth: { configurable: true, value: 1127 },
      scrollWidth: { configurable: true, value: 1600 },
      scrollLeft: { configurable: true, value: -437 },
    })
    wrapper.element.style.direction = 'rtl'

    await wrapper.trigger('scroll')
    await new Promise((resolve) => setTimeout(resolve, 60))
    await nextTick()

    expect(
      wrapper
        .findAll('.test-grid-cell')
        .map((cell) => Number(cell.attributes('data-field-id')))
    ).toEqual([2, 3, 4, 5, 6, 7, 8])
    expect(wrapper.find('.test-grid-row').attributes('data-left-offset')).toBe(
      '-200'
    )
  })
})
