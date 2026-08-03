import { mountSuspended } from '@nuxt/test-utils/runtime'

import ProgressWidget from '@baserow/modules/arabase/dashboard/components/widget/ProgressWidget'

describe('ProgressWidget', () => {
  const dashboard = { id: 1, workspace: { id: 1 } }

  const mountWidget = async ({ widget = {}, result = '50', error = false }) => {
    const dataSource = { id: 7, type: 'local_baserow_aggregate_rows' }
    const store = {
      getters: {
        'dashboardApplication/getDataSourceById': () => dataSource,
        'dashboardApplication/getDataForDataSource': () =>
          error ? { _error: true } : { result },
        'dashboardApplication/isEditMode': false,
      },
    }

    return await mountSuspended(ProgressWidget, {
      props: {
        dashboard,
        widget: {
          id: 3,
          title: 'Collections',
          description: '',
          type: 'progress',
          data_source_id: 7,
          target_value: '100',
          display_style: 'bar',
          warning_threshold: 50,
          success_threshold: 100,
          ...widget,
        },
      },
      global: {
        mocks: {
          $store: store,
          $registry: {
            get: () => ({ getResult: (ds, data) => data.result }),
          },
        },
        stubs: {
          WidgetContextMenu: true,
          Badge: { template: '<span><slot /></span>' },
        },
      },
    })
  }

  const percentage = (wrapper) =>
    wrapper.find('.dashboard-progress-widget__percentage').text()

  const fillWidth = (wrapper) =>
    wrapper.find('.dashboard-progress-widget__fill').element.style.width

  test('the percentage is the result over the target', async () => {
    const wrapper = await mountWidget({ result: '25' })

    expect(percentage(wrapper)).toBe('25%')
    expect(fillWidth(wrapper)).toBe('25%')
  })

  test('overshooting shows above 100% but the bar stops at full', async () => {
    // A bar wider than its track escapes the widget frame, while the number is
    // exactly the information the user wants.
    const wrapper = await mountWidget({ result: '250' })

    expect(percentage(wrapper)).toBe('250%')
    expect(fillWidth(wrapper)).toBe('100%')
  })

  test('the colour follows the thresholds', async () => {
    const danger = await mountWidget({ result: '10' })
    expect(danger.find('.dashboard-progress-widget__fill').classes()).toContain(
      'dashboard-progress-widget--danger'
    )

    const warning = await mountWidget({ result: '60' })
    expect(warning.find('.dashboard-progress-widget__fill').classes()).toContain(
      'dashboard-progress-widget--warning'
    )

    const success = await mountWidget({ result: '100' })
    expect(success.find('.dashboard-progress-widget__fill').classes()).toContain(
      'dashboard-progress-widget--success'
    )
  })

  test('a non-numeric result shows a dash instead of NaN', async () => {
    const wrapper = await mountWidget({ result: null })

    expect(percentage(wrapper)).toBe('—')
  })

  test('a zero target shows a dash instead of Infinity', async () => {
    // The API rejects it, but an imported or API-edited widget could carry one.
    const wrapper = await mountWidget({ widget: { target_value: '0' } })

    expect(percentage(wrapper)).toBe('—')
  })

  test('the ring style draws an arc instead of a bar', async () => {
    const wrapper = await mountWidget({
      widget: { display_style: 'ring' },
      result: '50',
    })

    expect(wrapper.find('.dashboard-progress-widget__fill').exists()).toBe(false)
    const arc = wrapper.find('.dashboard-progress-widget__ring-value')
    const [drawn, total] = arc
      .attributes('stroke-dasharray')
      .split(' ')
      .map(Number)
    // Half the target, so half the circumference is stroked.
    expect(drawn / total).toBeCloseTo(0.5, 5)
  })

  test('nothing is drawn when the data source is misconfigured', async () => {
    const wrapper = await mountWidget({ error: true })

    expect(wrapper.find('.dashboard-progress-widget__empty').exists()).toBe(true)
    expect(wrapper.find('.dashboard-progress-widget__fill').exists()).toBe(false)
  })
})
