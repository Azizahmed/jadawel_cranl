import { mount } from '@vue/test-utils'
import { vi } from 'vitest'
import Context from '@jadawel/modules/core/components/Context'

describe('Context.vue', () => {
  it('renders the slot content when openedOnce is true', () => {
    const wrapper = mount(Context, {
      data() {
        return {
          openedOnce: true,
        }
      },
      slots: {
        default: 'Test Content',
      },
    })

    expect(wrapper.text()).toContain('Test Content')
  })

  it('does not render the slot content when openedOnce is false', () => {
    const wrapper = mount(Context, {
      data() {
        return {
          openedOnce: false,
        }
      },
      slots: {
        default: 'Test Content',
      },
    })

    expect(wrapper.text()).not.toContain('Test Content')
  })

  it('adds the visibility-hidden class when open or updatedOnce is false', () => {
    const wrapper = mount(Context, {
      data() {
        return {
          open: false,
          updatedOnce: false,
        }
      },
    })

    expect(wrapper.classes()).toContain('visibility-hidden')
  })

  it('does not add the visibility-hidden class when open and updatedOnce are true', () => {
    const wrapper = mount(Context, {
      data() {
        return {
          open: true,
          updatedOnce: true,
        }
      },
    })

    expect(wrapper.classes()).not.toContain('visibility-hidden')
  })

  it('adds the context--overflow-scroll class when overflowScroll prop is true', () => {
    const wrapper = mount(Context, {
      propsData: {
        overflowScroll: true,
      },
    })

    expect(wrapper.classes()).toContain('context--overflow-scroll')
  })

  it('does not add the context--overflow-scroll class when overflowScroll prop is false', () => {
    const wrapper = mount(Context, {
      propsData: {
        overflowScroll: false,
      },
    })

    expect(wrapper.classes()).not.toContain('context--overflow-scroll')
  })

  it('sets the correct default props', () => {
    const wrapper = mount(Context)

    expect(wrapper.props('hideOnClickOutside')).toBe(true)
    expect(wrapper.props('overflowScroll')).toBe(false)
    expect(typeof wrapper.props('maxHeightIfOutsideViewport')).toBe('boolean')
    expect(wrapper.props('maxHeightIfOutsideViewport')).toBe(false)
  })

  it('toggles the open state when the toggle method is called', async () => {
    const wrapper = mount(Context)
    const target = document.createElement('div')

    expect(wrapper.vm.open).toBe(false)

    wrapper.vm.toggle(target)
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.open).toBe(true)
  })

  it('sets the opener when the toggle method is called with a target', async () => {
    const wrapper = mount(Context)
    const target = document.createElement('div')

    expect(wrapper.vm.opener).toBe(null)

    wrapper.vm.toggle(target)
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.opener).toBe(target)
  })

  it('keeps resize positioning safe when Vue replaces the root node', async () => {
    const removeEventListener = vi.spyOn(window, 'removeEventListener')
    const wrapper = mount(Context, {
      slots: {
        default: 'Test Content',
      },
    })
    const target = document.createElement('button')
    document.body.appendChild(target)
    target.getBoundingClientRect = vi.fn(() => ({
      top: 10,
      right: 100,
      bottom: 30,
      left: 80,
    }))
    wrapper.vm.$el.getBoundingClientRect = vi.fn(() => ({
      width: 120,
      height: 80,
    }))

    await wrapper.vm.show(target, 'bottom', 'left')

    const contextElement = wrapper.vm.contextElement
    const resizeHandler = wrapper.vm.updatePositionViaResizeEvent
    const originalRoot = wrapper.vm.$.vnode.el
    wrapper.vm.$.vnode.el = document.createComment('replaced root')

    expect(() => window.dispatchEvent(new Event('resize'))).not.toThrow()

    // Restore Vue's root reference before unmounting so MoveToBody can perform
    // its normal DOM cleanup; the resize callback above still exercised the
    // replaced-root path.
    wrapper.vm.$.vnode.el = originalRoot

    await wrapper.unmount()
    expect(removeEventListener).toHaveBeenCalledWith(
      'resize',
      resizeHandler
    )
    expect(contextElement.isConnected).toBe(false)
    expect(() => window.dispatchEvent(new Event('resize'))).not.toThrow()
    target.remove()
    removeEventListener.mockRestore()
  })

  it.each(['ltr', 'rtl'])(
    'positions at viewport edges in %s without throwing',
    (direction) => {
      const wrapper = mount(Context)
      const contextElement = wrapper.vm.$el
      const originalInnerWidth = window.innerWidth
      contextElement.getBoundingClientRect = vi.fn(() => ({
        width: 120,
        height: 80,
      }))
      Object.defineProperty(contextElement, 'scrollHeight', {
        configurable: true,
        value: 80,
      })
      Object.defineProperty(window, 'innerWidth', {
        configurable: true,
        value: 300,
      })
      document.documentElement.dir = direction

      let positions
      expect(() => {
        positions = wrapper.vm.calculatePositions(
          'left',
          'bottom',
          100,
          290,
          120,
          270,
          0,
          0
        )
      }).not.toThrow()
      expect(positions.right).toBe(10)

      wrapper.unmount()
      document.documentElement.dir = ''
      Object.defineProperty(window, 'innerWidth', {
        configurable: true,
        value: originalInnerWidth,
      })
    }
  )
})
