import { mountSuspended } from '@nuxt/test-utils/runtime'

import WidgetContext from '@jadawel/modules/dashboard/components/widget/WidgetContext'
import WidgetSizeContext from '@jadawel/modules/arabase/dashboard/components/widget/WidgetSizeContext'
import Context from '@jadawel/modules/core/components/Context'

const dashboard = { id: 1, workspace: { id: 1 } }

describe('WidgetContext size menu item', () => {
  const mountContext = async (hasPermission) => {
    const wrapper = await mountSuspended(WidgetContext, {
      props: { dashboard, widget: { id: 3, title: 'Sales' } },
      global: {
        mocks: {
          $store: { dispatch: vi.fn().mockResolvedValue() },
          $hasPermission: () => hasPermission,
        },
      },
    })
    // Context only renders its slot once it has been opened.
    await wrapper
      .findComponent(Context)
      .setData({ openedOnce: true, open: true })
    return wrapper
  }

  test('the size item is hidden without update permission', async () => {
    const wrapper = await mountContext(false)

    expect(wrapper.text()).not.toContain('widgetContext.size')
    expect(wrapper.findComponent(WidgetSizeContext).exists()).toBe(false)
  })

  test('the size item is visible with update permission', async () => {
    const wrapper = await mountContext(true)

    expect(wrapper.text()).toContain('widgetContext.size')
    expect(wrapper.findComponent(WidgetSizeContext).exists()).toBe(true)
  })
})

describe('WidgetSizeContext', () => {
  const mountPicker = async (widget = {}) => {
    const dispatch = vi.fn().mockResolvedValue()
    const wrapper = await mountSuspended(WidgetSizeContext, {
      props: {
        dashboard,
        widget: { id: 3, title: 'Sales', width: 3, height: 2, ...widget },
      },
      global: { mocks: { $store: { dispatch } } },
    })
    // Context only renders its slot once it has been opened.
    await wrapper
      .findComponent(Context)
      .setData({ openedOnce: true, open: true })
    return { wrapper, dispatch }
  }

  test('clicking a cell patches width/height through updateWidget', async () => {
    const { wrapper, dispatch } = await mountPicker()

    // Cells run (1,1) (2,1) (3,1) (1,2) (2,2) …: index 1 is 2 wide × 1 tall.
    await wrapper.findAll('.widget-size-context__cell')[1].trigger('click')

    expect(dispatch).toHaveBeenCalledWith('dashboardApplication/updateWidget', {
      widgetId: 3,
      values: { width: 2, height: 1 },
      originalValues: { width: 3, height: 2 },
    })
  })

  test('a widget without width/height falls back to 3x2', async () => {
    const { wrapper, dispatch } = await mountPicker({
      width: undefined,
      height: undefined,
    })

    await wrapper.findAll('.widget-size-context__cell')[0].trigger('click')

    expect(dispatch).toHaveBeenCalledWith('dashboardApplication/updateWidget', {
      widgetId: 3,
      values: { width: 1, height: 1 },
      originalValues: { width: 3, height: 2 },
    })
  })

  test('hovering a cell previews that rectangle', async () => {
    const { wrapper } = await mountPicker()
    const cells = wrapper.findAll('.widget-size-context__cell')

    // Hover (2,2): everything up to 2 wide and 2 tall is highlighted.
    await cells[4].trigger('mouseenter')

    const previewed = cells.filter((cell) =>
      cell.classes().includes('widget-size-context__cell--preview')
    )
    expect(previewed).toHaveLength(4)
    expect(wrapper.find('.widget-size-context__preview').text()).toBe(
      'widgetContext.sizePreview'
    )
  })

  test('the current size is marked', async () => {
    const { wrapper } = await mountPicker()
    const cells = wrapper.findAll('.widget-size-context__cell')

    // (3,2) is index 5.
    expect(cells[5].classes()).toContain('widget-size-context__cell--current')
  })
})
