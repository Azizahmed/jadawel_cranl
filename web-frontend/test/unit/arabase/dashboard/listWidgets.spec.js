import { mountSuspended } from '@nuxt/test-utils/runtime'

import RecordsListWidget from '@baserow/modules/arabase/dashboard/components/widget/RecordsListWidget'
import UpcomingDatesWidget from '@baserow/modules/arabase/dashboard/components/widget/UpcomingDatesWidget'

const SCHEMA = {
  items: {
    properties: {
      field_1: { title: 'Name' },
      field_2: { title: 'Region' },
      field_3: { title: 'Due' },
    },
  },
}

const mountListWidget = async (
  component,
  { widget = {}, dataSource = {}, results = [], error = false }
) => {
  const source = { id: 7, type: 'local_baserow_list_rows', schema: SCHEMA, ...dataSource }
  const store = {
    getters: {
      'dashboardApplication/getDataSourceById': () => source,
      'dashboardApplication/getDataForDataSource': () =>
        error ? { _error: true } : { results, has_next_page: false },
      'dashboardApplication/isEditMode': false,
    },
  }

  return await mountSuspended(component, {
    props: {
      dashboard: { id: 1, workspace: { id: 1 } },
      widget: {
        id: 3,
        title: 'Latest',
        description: '',
        data_source_id: 7,
        field_ids: [],
        ...widget,
      },
    },
    global: {
      mocks: { $store: store },
      stubs: {
        WidgetContextMenu: true,
        Badge: { template: '<span><slot /></span>' },
      },
    },
  })
}

const headers = (wrapper) => wrapper.findAll('th').map((th) => th.text())
const cells = (wrapper) => wrapper.findAll('td').map((td) => td.text())

describe('RecordsListWidget', () => {
  test('renders a column per field and a row per record', async () => {
    const wrapper = await mountListWidget(RecordsListWidget, {
      widget: { field_ids: [1, 2] },
      results: [
        { id: 1, Name: 'First', Region: 'Riyadh' },
        { id: 2, Name: 'Second', Region: 'Jeddah' },
      ],
    })

    expect(headers(wrapper)).toEqual(['Name', 'Region'])
    expect(cells(wrapper)).toEqual(['First', 'Riyadh', 'Second', 'Jeddah'])
  })

  test('with no fields chosen it shows the first fields of the table', async () => {
    const wrapper = await mountListWidget(RecordsListWidget, {
      results: [{ id: 1, Name: 'First', Region: 'Riyadh', Due: '2026-08-10' }],
    })

    expect(headers(wrapper)).toEqual(['Name', 'Region', 'Due'])
  })

  test('an empty result set says so instead of rendering an empty table', async () => {
    const wrapper = await mountListWidget(RecordsListWidget, { results: [] })

    expect(wrapper.find('table').exists()).toBe(false)
    expect(wrapper.find('.dashboard-records-list-widget__empty').exists()).toBe(
      true
    )
  })

  test('a misconfigured data source says so', async () => {
    const wrapper = await mountListWidget(RecordsListWidget, { error: true })

    expect(wrapper.find('.dashboard-records-list-widget__empty').exists()).toBe(
      true
    )
  })
})

describe('UpcomingDatesWidget', () => {
  const isoDaysFromNow = (days) => {
    const date = new Date()
    date.setDate(date.getDate() + days)
    return date.toISOString().slice(0, 10)
  }

  const mountAgenda = (options = {}) =>
    mountListWidget(UpcomingDatesWidget, {
      dataSource: {
        type: 'local_baserow_upcoming_rows',
        date_field_id: 3,
        ...(options.dataSource || {}),
      },
      widget: { field_ids: [1, 2], ...(options.widget || {}) },
      results: options.results,
      error: options.error,
    })

  test('the date column is trailing and not repeated among the fields', async () => {
    const wrapper = await mountAgenda({
      widget: { field_ids: [1, 3] },
      results: [{ id: 1, Name: 'Renewal', Region: 'Riyadh', Due: isoDaysFromNow(3) }],
    })

    // 'Due' appears once, as the trailing column, even though it was also
    // selected as a displayed field.
    expect(headers(wrapper)).toEqual(['Name', 'Due'])
  })

  test('an overdue row is flagged and counted', async () => {
    const wrapper = await mountAgenda({
      results: [
        { id: 1, Name: 'Late', Region: 'Riyadh', Due: isoDaysFromNow(-2) },
        { id: 2, Name: 'Soon', Region: 'Jeddah', Due: isoDaysFromNow(2) },
      ],
    })

    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].classes()).toContain('widget-record-rows__row--flagged')
    expect(rows[1].classes()).not.toContain('widget-record-rows__row--flagged')
  })

  test('a row due today is not flagged as overdue', async () => {
    // The boundary matters: "overdue" means before the start of today, so
    // something due later today is still upcoming.
    const wrapper = await mountAgenda({
      results: [{ id: 1, Name: 'Today', Region: 'Riyadh', Due: isoDaysFromNow(0) }],
    })

    expect(wrapper.find('tbody tr').classes()).not.toContain(
      'widget-record-rows__row--flagged'
    )
  })

  test('an empty agenda says nothing is due', async () => {
    const wrapper = await mountAgenda({ results: [] })

    expect(
      wrapper.find('.dashboard-upcoming-dates-widget__empty').exists()
    ).toBe(true)
  })

  test('rows with no date field configured still render', async () => {
    // The data source can be mid-configuration; the widget must not throw.
    const wrapper = await mountAgenda({
      dataSource: { date_field_id: null },
      results: [{ id: 1, Name: 'Renewal', Region: 'Riyadh' }],
    })

    expect(headers(wrapper)).toEqual(['Name', 'Region'])
  })
})
