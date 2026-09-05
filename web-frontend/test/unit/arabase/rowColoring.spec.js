import { mount } from '@vue/test-utils'

import BackgroundColorDecorator from '@jadawel/modules/arabase/components/BackgroundColorDecorator'
import { BackgroundColorDecoratorType } from '@jadawel/modules/arabase/decorators/backgroundColor'
import { SingleSelectColorValueProviderType } from '@jadawel/modules/arabase/valueProviders/singleSelectColor'

/**
 * Row coloring resolves entirely client-side from loaded row values, so that
 * is what is asserted: option color in, color string out, and nothing rendered
 * when the configuration points nowhere.
 */
const app = { $i18n: { t: (key) => key } }

const fields = [
  { id: 10, name: 'Status', type: 'single_select' },
  { id: 11, name: 'Notes', type: 'text' },
]

describe('SingleSelectColorValueProviderType', () => {
  const provider = new SingleSelectColorValueProviderType({ app })

  test('resolves the option color of the configured field', () => {
    const row = { id: 1, field_10: { id: 5, value: 'Open', color: 'blue' } }
    expect(provider.getValue({ options: { field_id: 10 }, fields, row })).toBe(
      'blue'
    )
  })

  test('returns null when the field is unknown', () => {
    const row = { id: 1, field_10: { id: 5, value: 'Open', color: 'blue' } }
    expect(provider.getValue({ options: { field_id: 999 }, fields, row })).toBe(
      null
    )
  })

  test('returns null when the row has no value or no color', () => {
    expect(
      provider.getValue({ options: { field_id: 10 }, fields, row: { id: 1 } })
    ).toBe(null)
    expect(
      provider.getValue({
        options: { field_id: 10 },
        fields,
        row: { id: 1, field_10: { id: 5, value: 'Open' } },
      })
    ).toBe(null)
  })

  test('rejects values outside the option palette', () => {
    const row = { id: 1, field_10: { id: 5, value: 'X', color: 'red;evil' } }
    expect(provider.getValue({ options: { field_id: 10 }, fields, row })).toBe(
      null
    )
  })

  test('defaults to the first single select field', () => {
    expect(provider.getDefaultConfiguration({ fields, view: {} })).toEqual({
      field_id: 10,
    })
    expect(
      provider.getDefaultConfiguration({
        fields: [{ id: 11, type: 'text' }],
        view: {},
      })
    ).toEqual({ field_id: null })
  })
})

describe('BackgroundColorDecoratorType', () => {
  const decorator = new BackgroundColorDecoratorType({ app })

  test('is grid-only', () => {
    expect(decorator.isCompatible({ type: 'grid' })).toBe(true)
    expect(decorator.isCompatible({ type: 'gallery' })).toBe(false)
  })

  test('allows a single background decoration per view', () => {
    expect(decorator.canAdd({ view: { decorations: [] } })[0]).toBe(true)
    const [canAdd] = decorator.canAdd({
      view: { decorations: [{ type: 'background_color' }] },
    })
    expect(canAdd).toBe(false)
  })

  test('renders at the row wrapper place', () => {
    expect(decorator.getPlace()).toBe('wrapper')
  })
})

describe('BackgroundColorDecorator', () => {
  test('applies the palette class for a known color', () => {
    const wrapper = mount(BackgroundColorDecorator, {
      props: { value: 'blue' },
    })
    expect(wrapper.classes()).toContain('background-color--blue')
  })

  test('renders plain rows for missing or unsafe values', () => {
    for (const value of [null, undefined, 'red;evil']) {
      const wrapper = mount(BackgroundColorDecorator, {
        props: { value },
      })
      expect(
        wrapper.classes().some((c) => c.startsWith('background-color--'))
      ).toBe(false)
    }
  })
})
