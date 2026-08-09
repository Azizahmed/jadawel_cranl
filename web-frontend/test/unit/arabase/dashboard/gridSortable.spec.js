import gridSortable from '@jadawel/modules/arabase/directives/gridSortable'

describe('grid sortable directive', () => {
  test('falls back to the widget element while a handle is not rendered', () => {
    const element = document.createElement('div')
    const binding = {
      dir: gridSortable,
      value: {
        id: 1,
        enabled: true,
        handle: '.widget__header',
      },
    }

    document.body.appendChild(element)

    expect(() => gridSortable.beforeMount(element, binding)).not.toThrow()
    expect(() => gridSortable.unmounted(element, binding)).not.toThrow()

    element.remove()
  })
})
