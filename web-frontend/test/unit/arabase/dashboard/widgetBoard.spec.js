import { mountSuspended } from '@nuxt/test-utils/runtime'

import WidgetBoard from '@jadawel/modules/dashboard/components/WidgetBoard'

const dashboard = { id: 1, workspace: { id: 1 } }

const mountBoard = async (
  widgets,
  { isEditMode = false, hasPermission = false } = {}
) => {
  const store = {
    getters: {
      'dashboardApplication/getWidgets': widgets,
      'dashboardApplication/isEditMode': isEditMode,
      'dashboardApplication/getSelectedWidgetId': null,
      'dashboardApplication/getData': {},
    },
    dispatch: vi.fn().mockResolvedValue(),
  }
  // The widget component itself is irrelevant here; the board test only cares
  // about the frame's grid spans. The header div exists because the globally
  // registered v-grid-sortable directive uses it as the drag handle.
  const widgetType = {
    name: 'Stub',
    isLoading: () => false,
    component: {
      template:
        '<div><div class="widget__header"></div><div class="widget-stub"></div></div>',
    },
  }

  return await mountSuspended(WidgetBoard, {
    props: { dashboard },
    global: {
      mocks: {
        $store: store,
        $registry: { get: () => widgetType },
        $hasPermission: () => hasPermission,
      },
      directives: { gridSortable: {} },
    },
  })
}

describe('WidgetBoard grid layout', () => {
  test('renders each widget with span styles matching its width/height', async () => {
    const wrapper = await mountBoard([
      { id: 1, type: 'stub', order: '1', width: 2, height: 1 },
      { id: 2, type: 'stub', order: '2', width: 1, height: 3 },
    ])

    const frames = wrapper.findAll('.dashboard-widget')
    expect(frames).toHaveLength(2)
    expect(frames[0].attributes('style')).toContain('grid-column: span 2')
    expect(frames[0].attributes('style')).toContain('grid-row: span 1')
    expect(frames[1].attributes('style')).toContain('grid-column: span 1')
    expect(frames[1].attributes('style')).toContain('grid-row: span 3')
  })

  test('a widget without width/height falls back to 3x2', async () => {
    const wrapper = await mountBoard([{ id: 1, type: 'stub', order: '1' }])

    const frame = wrapper.find('.dashboard-widget')
    expect(frame.attributes('style')).toContain('grid-column: span 3')
    expect(frame.attributes('style')).toContain('grid-row: span 2')
  })

  test('drag is offered in edit mode with update permission', async () => {
    const wrapper = await mountBoard(
      [{ id: 1, type: 'stub', order: '1', width: 3, height: 2 }],
      { isEditMode: true, hasPermission: true }
    )

    expect(wrapper.find('.widget-board').classes()).toContain(
      'widget-board--draggable'
    )
  })

  test('drag is disabled below the grid breakpoint', async () => {
    const originalWidth = window.innerWidth
    window.innerWidth = 500
    try {
      const wrapper = await mountBoard(
        [{ id: 1, type: 'stub', order: '1', width: 3, height: 2 }],
        { isEditMode: true, hasPermission: true }
      )

      expect(wrapper.find('.widget-board').classes()).not.toContain(
        'widget-board--draggable'
      )
    } finally {
      window.innerWidth = originalWidth
    }
  })
})
