import { defineComponent, h, nextTick } from 'vue'

import Scrollbars from '@jadawel/modules/core/components/Scrollbars'
import { TestApp } from '@jadawel/test/helpers/testApp'

const createScrollableParent = (direction) =>
  defineComponent({
    name: 'ScrollableParent',
    methods: {
      getHorizontalScrollbarElement() {
        return this.$refs.scrollable
      },
      horizontalScroll(left) {
        this.$refs.scrollable.scrollLeft = left
      },
    },
    render() {
      return h('div', { style: { direction } }, [
        h('div', { ref: 'scrollable', class: 'test-scrollable' }),
        h(Scrollbars, {
          horizontal: 'getHorizontalScrollbarElement',
          onHorizontal: this.horizontalScroll,
        }),
      ])
    },
  })

describe('Scrollbars component', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
  })

  afterEach(async () => {
    await testApp.afterEach()
  })

  const mountComponent = async (direction, scrollLeft) => {
    const wrapper = await testApp.mount(createScrollableParent(direction))
    const scrollable = wrapper.find('.test-scrollable').element

    Object.defineProperties(scrollable, {
      clientWidth: { configurable: true, value: 500 },
      scrollWidth: { configurable: true, value: 1000 },
    })
    scrollable.scrollLeft = scrollLeft
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    return { wrapper, scrollable }
  }

  test('keeps the RTL horizontal handle visible after scrolling', async () => {
    const { wrapper } = await mountComponent('rtl', -250)
    const handle = wrapper.find('.scrollbars__horizontal')

    expect(handle.exists()).toBe(true)
    expect(handle.attributes('style')).toContain('inset-inline-start: 25%')
    expect(handle.attributes('style')).not.toContain('left: -25%')
  })

  test('drags the RTL horizontal handle toward inline-end', async () => {
    const { wrapper, scrollable } = await mountComponent('rtl', -250)
    const handle = wrapper.find('.scrollbars__horizontal')

    await handle.trigger('mousedown', { clientX: 400 })
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 300 }))
    await nextTick()

    expect(scrollable.scrollLeft).toBe(-450)
  })

  test('keeps LTR horizontal positioning unchanged', async () => {
    const { wrapper } = await mountComponent('ltr', 250)
    const handle = wrapper.find('.scrollbars__horizontal')

    expect(handle.attributes('style')).toContain('inset-inline-start: 25%')
  })
})
