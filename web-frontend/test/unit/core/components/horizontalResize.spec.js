import { mountSuspended } from '@nuxt/test-utils/runtime'
import HorizontalResize from '@baserow/modules/core/components/HorizontalResize.vue'

describe('HorizontalResize', () => {
  const mountComponent = ({ props = {} }) => {
    return mountSuspended(HorizontalResize, { props })
  }

  /**
   * Simulates a drag by starting on the handle and moving the pointer to the
   * given x coordinate. The direction is forced by stubbing the resolved style
   * because jsdom doesn't inherit `dir` into `getComputedStyle`.
   */
  const drag = async (wrapper, { from, to, rtl = false }) => {
    const original = window.getComputedStyle
    window.getComputedStyle = (element) => ({
      ...original(element),
      direction: rtl ? 'rtl' : 'ltr',
    })

    try {
      await wrapper.trigger('mousedown', { clientX: from })
      wrapper.element.moveEvent({ clientX: to, preventDefault() {} })
      wrapper.element.upEvent({ clientX: to, preventDefault() {} })
    } finally {
      window.getComputedStyle = original
    }
  }

  const lastMove = (wrapper) => {
    const moves = wrapper.emitted('move')
    return moves[moves.length - 1][0]
  }

  test('dragging toward the inline-end widens in LTR', async () => {
    const wrapper = await mountComponent({ props: { width: 200 } })

    await drag(wrapper, { from: 500, to: 560 })

    expect(lastMove(wrapper)).toBe(260)
    expect(wrapper.emitted('update')[0][0]).toEqual({
      width: 260,
      oldWidth: 200,
    })
  })

  test('dragging toward the inline-end widens in RTL', async () => {
    const wrapper = await mountComponent({ props: { width: 200 } })

    // In RTL the inline-end edge is on the left, so the pointer moves left.
    await drag(wrapper, { from: 500, to: 440, rtl: true })

    expect(lastMove(wrapper)).toBe(260)
    expect(wrapper.emitted('update')[0][0]).toEqual({
      width: 260,
      oldWidth: 200,
    })
  })

  test('dragging toward the inline-start narrows in RTL', async () => {
    const wrapper = await mountComponent({ props: { width: 200 } })

    await drag(wrapper, { from: 500, to: 560, rtl: true })

    expect(lastMove(wrapper)).toBe(140)
  })

  test('the min width is respected in RTL', async () => {
    const wrapper = await mountComponent({ props: { width: 200, min: 150 } })

    await drag(wrapper, { from: 500, to: 800, rtl: true })

    expect(lastMove(wrapper)).toBe(150)
  })

  test('the max width is respected on commit', async () => {
    const wrapper = await mountComponent({ props: { width: 200, max: 250 } })

    await drag(wrapper, { from: 500, to: 800 })

    expect(lastMove(wrapper)).toBe(250)
    expect(wrapper.emitted('update')[0][0].width).toBe(250)
  })

  test('a right handle is inverted relative to a normal handle in RTL', async () => {
    const wrapper = await mountComponent({
      props: { width: 200, right: true },
    })

    // Mirror of the "widens in RTL" case, so the same movement narrows instead.
    await drag(wrapper, { from: 500, to: 440, rtl: true })

    expect(lastMove(wrapper)).toBe(140)
  })
})
