import MockAdapter from 'axios-mock-adapter'
import flushPromises from 'flush-promises'

describe('dashboardApplication store (grid layout)', () => {
  let store = null
  let mock = null

  const seedWidget = (widget) =>
    store.commit('dashboardApplication/ADD_WIDGET', {
      id: 1,
      title: 'Sales',
      type: 'summary',
      order: '1',
      width: 3,
      height: 2,
      ...widget,
    })

  const getWidget = (widgetId) =>
    store.getters['dashboardApplication/getWidgetById'](widgetId)

  beforeEach(() => {
    vi.useFakeTimers()
    const { $store, $client } = useNuxtApp()
    store = $store
    mock = new MockAdapter($client, { onNoMatch: 'throwException' })
    store.commit('dashboardApplication/RESET')
  })

  afterEach(() => {
    mock.restore()
    vi.useRealTimers()
  })

  test('a width/height/order update merges and the response refreshes the widget', async () => {
    seedWidget()
    mock.onPatch('/dashboard/widgets/1/').reply(200, {
      id: 1,
      title: 'Sales',
      type: 'summary',
      order: '1.50000000000000000000',
      width: 1,
      height: 3,
    })

    const promise = store.dispatch('dashboardApplication/updateWidget', {
      widgetId: 1,
      values: { order: '1.5', width: 1, height: 3 },
      originalValues: { order: '1', width: 3, height: 2 },
    })

    // Optimistic merge.
    expect(getWidget(1).order).toBe('1.5')

    await vi.advanceTimersByTimeAsync(1000)
    await promise

    expect(JSON.parse(mock.history.patch[0].data)).toEqual({
      order: '1.5',
      width: 1,
      height: 3,
    })
    // The exact values the backend computed are committed back.
    expect(getWidget(1).order).toBe('1.50000000000000000000')
    expect(getWidget(1).width).toBe(1)
    expect(getWidget(1).height).toBe(3)
    expect(getWidget(1).title).toBe('Sales')
  })

  test('a drag followed within a second by a resize is one merged PATCH', async () => {
    seedWidget()
    mock.onPatch('/dashboard/widgets/1/').reply(200, { id: 1 })

    // The first (cancelled) dispatch never settles; the second carries both
    // changes.
    store.dispatch('dashboardApplication/updateWidget', {
      widgetId: 1,
      values: { order: '2.5' },
      originalValues: { order: '1' },
    })
    const resize = store.dispatch('dashboardApplication/updateWidget', {
      widgetId: 1,
      values: { width: 1, height: 1 },
      originalValues: { width: 3, height: 2 },
    })

    await vi.advanceTimersByTimeAsync(1000)
    await resize

    expect(mock.history.patch).toHaveLength(1)
    expect(JSON.parse(mock.history.patch[0].data)).toEqual({
      order: '2.5',
      width: 1,
      height: 1,
    })
    // Both changes are visible locally.
    expect(getWidget(1).order).toBe('2.5')
    expect(getWidget(1).width).toBe(1)
  })

  test('an update for another widget flushes the pending one instead of dropping it', async () => {
    seedWidget()
    seedWidget({ id: 2, title: 'Stock', order: '2' })
    mock.onPatch('/dashboard/widgets/1/').reply(200, { id: 1 })
    mock.onPatch('/dashboard/widgets/2/').reply(200, { id: 2 })

    const first = store.dispatch('dashboardApplication/updateWidget', {
      widgetId: 1,
      values: { order: '1.5' },
      originalValues: { order: '1' },
    })
    const second = store.dispatch('dashboardApplication/updateWidget', {
      widgetId: 2,
      values: { width: 2 },
      originalValues: { width: 3 },
    })

    await vi.advanceTimersByTimeAsync(1000)
    await Promise.all([first, second])

    expect(mock.history.patch).toHaveLength(2)
    expect(JSON.parse(mock.history.patch[0].data)).toEqual({ order: '1.5' })
    expect(JSON.parse(mock.history.patch[1].data)).toEqual({ width: 2 })
  })

  test('a realtime widget update merges width/height/order', async () => {
    seedWidget()

    await store.dispatch('dashboardApplication/handleWidgetUpdated', {
      id: 1,
      order: '7',
      width: 2,
      height: 1,
    })

    expect(getWidget(1).order).toBe('7')
    expect(getWidget(1).width).toBe(2)
    expect(getWidget(1).height).toBe(1)
    expect(getWidget(1).title).toBe('Sales')
  })
  test('does not dispatch an unconfigured data source on initial fetch', async () => {
    mock.onGet('/dashboard/123/data-sources/').reply(200, [
      {
        id: 1,
        type: 'local_jadawel_grouped_aggregate_rows',
        table_id: null,
        schema: null,
        context_data: {},
      },
    ])
    mock.onPost('/dashboard/data-sources/1/dispatch/').reply(400)

    await store.dispatch('dashboardApplication/fetchNewDataSources', 123)
    await flushPromises()

    expect(mock.history.post).toHaveLength(0)
    expect(
      store.getters['dashboardApplication/getDataForDataSource'](1)
    ).toEqual({ _error: true })
  })

  test('does not dispatch an aggregate source without series', async () => {
    mock.onGet('/dashboard/123/data-sources/').reply(200, [
      {
        id: 1,
        type: 'local_jadawel_grouped_aggregate_rows',
        table_id: 1,
        schema: { type: 'object' },
        context_data: { series: [] },
        aggregation_series: [],
      },
    ])
    mock.onPost('/dashboard/data-sources/1/dispatch/').reply(400)

    await store.dispatch('dashboardApplication/fetchNewDataSources', 123)
    await flushPromises()

    expect(mock.history.post).toHaveLength(0)
    expect(
      store.getters['dashboardApplication/getDataForDataSource'](1)
    ).toEqual({ _error: true })
  })

  test('dispatches a configured data source on initial fetch', async () => {
    mock.onGet('/dashboard/123/data-sources/').reply(200, [
      {
        id: 1,
        type: 'local_jadawel_grouped_aggregate_rows',
        table_id: 1,
        schema: { type: 'object' },
        context_data: { series: [] },
        aggregation_series: [
          { field_id: 1, aggregation_type: 'sum' },
        ],
      },
    ])
    mock.onPost('/dashboard/data-sources/1/dispatch/').reply(200, {
      result: { rows: [] },
    })

    await store.dispatch('dashboardApplication/fetchNewDataSources', 123)
    await flushPromises()

    expect(mock.history.post).toHaveLength(1)
    expect(
      store.getters['dashboardApplication/getDataForDataSource'](1)
    ).toEqual({ result: { rows: [] } })
  })
})

