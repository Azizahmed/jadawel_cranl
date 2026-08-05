import {
  formatRecordValue,
  resolveDisplayedFields,
} from '@jadawel/modules/arabase/dashboard/recordValues'

describe('formatRecordValue', () => {
  test('empty values render as nothing rather than "null"', () => {
    expect(formatRecordValue(null)).toBe('')
    expect(formatRecordValue(undefined)).toBe('')
  })

  test('primitives pass through as text', () => {
    expect(formatRecordValue('Riyadh')).toBe('Riyadh')
    expect(formatRecordValue(42)).toBe('42')
    // Zero is a value, not an absence — it must not be swallowed.
    expect(formatRecordValue(0)).toBe('0')
  })

  test('booleans render as a tick or nothing', () => {
    expect(formatRecordValue(true)).toBe('✓')
    expect(formatRecordValue(false)).toBe('')
  })

  test('a single select object renders its value', () => {
    expect(formatRecordValue({ id: 1, value: 'Open', color: 'blue' })).toBe('Open')
  })

  test('link rows and collaborators render as a joined list', () => {
    expect(
      formatRecordValue([{ visible_name: 'Sara' }, { visible_name: 'Omar' }])
    ).toBe('Sara, Omar')
  })

  test('empty entries do not leave dangling separators', () => {
    expect(formatRecordValue([{ visible_name: 'Sara' }, null])).toBe('Sara')
  })
})

describe('resolveDisplayedFields', () => {
  const dataSource = {
    schema: {
      items: {
        properties: {
          id: { title: 'Id' },
          field_1: { title: 'Name' },
          field_2: { title: 'Amount' },
          field_3: { title: 'Region' },
          field_4: { title: 'Notes' },
        },
      },
    },
  }

  test('with nothing stored it falls back to the first fields', () => {
    expect(resolveDisplayedFields(dataSource, [])).toEqual([
      { id: 1, name: 'Name' },
      { id: 2, name: 'Amount' },
      { id: 3, name: 'Region' },
    ])
  })

  test('stored ids are honoured in their own order', () => {
    expect(resolveDisplayedFields(dataSource, [3, 1])).toEqual([
      { id: 3, name: 'Region' },
      { id: 1, name: 'Name' },
    ])
  })

  test('an id whose field was deleted is skipped, not rendered blank', () => {
    expect(resolveDisplayedFields(dataSource, [1, 99])).toEqual([
      { id: 1, name: 'Name' },
    ])
  })

  test('a data source with no schema yet yields nothing', () => {
    expect(resolveDisplayedFields(undefined, [])).toEqual([])
    expect(resolveDisplayedFields({}, [1])).toEqual([])
  })
})
