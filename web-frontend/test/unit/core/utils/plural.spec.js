import { pluralCategory, pluralKeys } from '@jadawel/modules/core/utils/plural'

describe('plural category selection', () => {
  test('picks the six Arabic CLDR categories, not the English two', () => {
    // The reason this module exists: vue-i18n applied the English rule to
    // Arabic, so everything above one collapsed into a single form.
    expect(pluralCategory('ar', 0)).toBe('zero')
    expect(pluralCategory('ar', 1)).toBe('one')
    expect(pluralCategory('ar', 2)).toBe('two')
    expect(pluralCategory('ar', 3)).toBe('few')
    expect(pluralCategory('ar', 10)).toBe('few')
    expect(pluralCategory('ar', 11)).toBe('many')
    expect(pluralCategory('ar', 24)).toBe('many')
    expect(pluralCategory('ar', 99)).toBe('many')
    expect(pluralCategory('ar', 100)).toBe('other')
    expect(pluralCategory('ar', 200)).toBe('other')
  })

  test('the counts on the dashboard cards land in the right categories', () => {
    // 200 rows must read "٢٠٠ صف" and 24 columns "٢٤ عمودًا"; both were "صفوف"
    // and "أعمدة" before, which is the mistake this guards against.
    expect(pluralCategory('ar', 200)).toBe('other')
    expect(pluralCategory('ar', 24)).toBe('many')
    expect(pluralCategory('ar', 13)).toBe('many')
    expect(pluralCategory('ar', 6)).toBe('few')
  })

  test('English keeps its two categories plus the explicit zero', () => {
    expect(pluralCategory('en', 0)).toBe('zero')
    expect(pluralCategory('en', 1)).toBe('one')
    expect(pluralCategory('en', 2)).toBe('other')
    expect(pluralCategory('en', 200)).toBe('other')
  })

  test('an unknown locale falls back rather than throwing', () => {
    expect(pluralCategory('not-a-locale', 5)).toBe('other')
  })

  test('keys fall back to other so a locale need not define every category', () => {
    // English has no `many`, so an Arabic-shaped lookup must still resolve.
    expect(pluralKeys('a.rowCount', 'ar', 24)).toStrictEqual([
      'a.rowCount.many',
      'a.rowCount.other',
    ])
    expect(pluralKeys('a.rowCount', 'en', 24)).toStrictEqual(['a.rowCount.other'])
  })
})
