import {
  LocalJadawelListRowsServiceType,
  LocalJadawelGetRowServiceType,
  LocalJadawelTableServiceType,
  LocalJadawelAggregateRowsServiceType,
  LocalJadawelCreateRowWorkflowServiceType,
  LocalJadawelDeleteRowWorkflowServiceType,
} from '@jadawel/modules/integrations/localJadawel/serviceTypes'
import { TestApp } from '@jadawel/test/helpers/testApp'

describe('Local jadawel service types', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('Get service should prepareValuePath', () => {
    const fakeApp = {}
    const serviceType = new LocalJadawelGetRowServiceType(fakeApp)

    const service = {
      schema: {
        properties: { id: { title: 'Id' }, field_42: { title: 'Field 42' } },
      },
    }

    expect(serviceType.prepareValuePath(service, [])).toEqual([])
    expect(serviceType.prepareValuePath(service, [0])).toEqual([0])
    expect(serviceType.prepareValuePath(service, ['id'])).toEqual(['id'])
    expect(serviceType.prepareValuePath(service, ['field_42'])).toEqual([
      'Field 42',
    ])
    expect(
      serviceType.prepareValuePath(service, ['field_42', 'value'])
    ).toEqual(['Field 42', 'value'])
  })

  test('List service should prepareValuePath', () => {
    const fakeApp = {}
    const serviceType = new LocalJadawelListRowsServiceType(fakeApp)

    const service = {
      schema: {
        items: {
          properties: { id: { title: 'Id' }, field_42: { title: 'Field 42' } },
        },
      },
    }

    expect(serviceType.prepareValuePath(service, [])).toEqual([])
    expect(serviceType.prepareValuePath(service, [0])).toEqual([0])
    expect(serviceType.prepareValuePath(service, ['id'])).toEqual(['id'])
    expect(serviceType.prepareValuePath(service, ['field_42'])).toEqual([
      'Field 42',
    ])
    expect(
      serviceType.prepareValuePath(service, ['field_42', 'value'])
    ).toEqual(['Field 42', 'value'])
  })

  test('List service should resolve correctly in builder data provider', () => {
    const dataProvider = testApp
      .getRegistry()
      .get('builderDataProvider', 'data_source')

    const service = {
      id: 1,
      type: 'local_jadawel_list_rows',
      schema: {
        items: {
          properties: { id: { title: 'Id' }, field_42: { title: 'Field 42' } },
        },
      },
    }

    dataProvider.getDataSourceContent = vi.fn(() => [
      { id: 1, 'Field 42': 'Field 42 content row 1' },
      { id: 2, 'Field 42': 'Field 42 content row 2' },
    ])

    const page = { id: 2, dataSources: [service] }

    const applicationContext = {
      builder: {
        pages: [{ id: 1, shared: true, dataSources: [] }, page],
      },
      page,
    }

    expect(dataProvider.getDataChunk(applicationContext, ['1'])).toEqual([
      { id: 1, 'Field 42': 'Field 42 content row 1' },
      { id: 2, 'Field 42': 'Field 42 content row 2' },
    ])
    expect(dataProvider.getDataChunk(applicationContext, ['1', '0'])).toEqual({
      id: 1,
      'Field 42': 'Field 42 content row 1',
    })
    expect(dataProvider.getDataChunk(applicationContext, ['1', '1'])).toEqual({
      id: 2,
      'Field 42': 'Field 42 content row 2',
    })
    expect(
      dataProvider.getDataChunk(applicationContext, ['1', '1', 'id'])
    ).toEqual(2)
    expect(
      dataProvider.getDataChunk(applicationContext, ['1', '1', 'field_42'])
    ).toEqual('Field 42 content row 2')
    expect(
      dataProvider.getDataChunk(applicationContext, ['1', '*', 'field_42'])
    ).toEqual(['Field 42 content row 1', 'Field 42 content row 2'])
  })

  test('Get service should resolve correctly in builder data provider', () => {
    const dataProvider = testApp
      .getRegistry()
      .get('builderDataProvider', 'data_source')

    const service = {
      id: 1,
      type: 'local_jadawel_get_row',
      schema: {
        properties: { id: { title: 'Id' }, field_42: { title: 'Field 42' } },
      },
    }

    dataProvider.getDataSourceContent = vi.fn(() => ({
      id: 1,
      'Field 42': 'Field 42 content',
    }))

    const page = { id: 2, dataSources: [service] }

    const applicationContext = {
      builder: {
        pages: [{ id: 1, shared: true, dataSources: [] }, page],
      },
      page,
    }

    expect(dataProvider.getDataChunk(applicationContext, ['1'])).toEqual({
      id: 1,
      'Field 42': 'Field 42 content',
    })
    expect(dataProvider.getDataChunk(applicationContext, ['1', 'id'])).toEqual(
      1
    )
    expect(
      dataProvider.getDataChunk(applicationContext, ['1', 'field_42'])
    ).toEqual('Field 42 content')
  })

  test('LocalJadawelTableServiceType supportedTables returns all tables it is given.', () => {
    const fakeApp = {}
    const serviceType = new LocalJadawelTableServiceType(fakeApp)

    const tables = [
      {
        id: 1,
        name: 'Table 1',
        is_data_sync: false,
        is_two_way_data_sync: false,
      },
      {
        id: 2,
        name: 'Table 2',
        is_data_sync: true,
        is_two_way_data_sync: false,
      },
      {
        id: 3,
        name: 'Table 3',
        is_data_sync: true,
        is_two_way_data_sync: true,
      },
    ]

    const result = serviceType.supportedTables(tables)
    expect(result).toEqual(tables)
    expect(result.length).toBe(3)
  })

  test('Aggregate rows service returns the raw public result when private formatting context is omitted', () => {
    const serviceType = new LocalJadawelAggregateRowsServiceType({})

    expect(serviceType.getResult({ schema: {} }, { result: '42' })).toBe('42')
  })

  test('Aggregate rows service formats private results when formatting context is available', () => {
    const fieldType = {}
    const aggregationType = { formatValue: vi.fn(() => '42 formatted') }
    const registry = {
      get: vi.fn((namespace) =>
        namespace === 'field' ? fieldType : aggregationType
      ),
    }
    const serviceType = new LocalJadawelAggregateRowsServiceType({
      app: { $registry: registry },
    })
    const field = { type: 'number' }

    expect(
      serviceType.getResult(
        { context_data: { field }, aggregation_type: 'sum' },
        { result: 42 }
      )
    ).toBe('42 formatted')
    expect(aggregationType.formatValue).toHaveBeenCalledWith(42, {
      field,
      fieldType,
    })
  })

  test('LocalJadawelCreateRowWorkflowServiceType supportedTables returns non data-synced tables or two-way data-synced tables.', () => {
    const fakeApp = {}
    const serviceType = new LocalJadawelCreateRowWorkflowServiceType(fakeApp)

    const tables = [
      {
        id: 1,
        name: 'Table 1',
        is_data_sync: false,
        is_two_way_data_sync: false,
      },
      {
        id: 2,
        name: 'Table 2',
        is_data_sync: true,
        is_two_way_data_sync: false,
      },
      {
        id: 3,
        name: 'Table 3',
        is_data_sync: true,
        is_two_way_data_sync: true,
      },
    ]

    const result = serviceType.supportedTables(tables)
    expect(result).toEqual([
      {
        id: 1,
        name: 'Table 1',
        is_data_sync: false,
        is_two_way_data_sync: false,
      },
      {
        id: 3,
        name: 'Table 3',
        is_data_sync: true,
        is_two_way_data_sync: true,
      },
    ])
    expect(result.length).toBe(2)
  })

  test('LocalJadawelDeleteRowWorkflowServiceType supportedTables returns non data-synced tables or two-way data-synced tables', () => {
    const fakeApp = {}
    const serviceType = new LocalJadawelDeleteRowWorkflowServiceType(fakeApp)

    const tables = [
      {
        id: 1,
        name: 'Table 1',
        is_data_sync: false,
        is_two_way_data_sync: false,
      },
      {
        id: 2,
        name: 'Table 2',
        is_data_sync: true,
        is_two_way_data_sync: false,
      },
      {
        id: 3,
        name: 'Table 3',
        is_data_sync: true,
        is_two_way_data_sync: true,
      },
    ]

    const result = serviceType.supportedTables(tables)
    expect(result).toEqual([
      {
        id: 1,
        name: 'Table 1',
        is_data_sync: false,
        is_two_way_data_sync: false,
      },
      {
        id: 3,
        name: 'Table 3',
        is_data_sync: true,
        is_two_way_data_sync: true,
      },
    ])
    expect(result.length).toBe(2)
  })
})
