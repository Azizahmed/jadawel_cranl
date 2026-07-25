import {
  parseLocaleJson,
  validateLocalePair,
} from '../../../../scripts/check-locale-parity.mjs'

describe('locale parity checker', () => {
  test('reports missing and unexpected translation keys', () => {
    const result = validateLocalePair(
      { save: 'Save', nested: { cancel: 'Cancel' } },
      { save: 'حفظ', extra: 'إضافي' }
    )

    expect(result.issues).toStrictEqual([
      { type: 'missing', key: 'nested.cancel' },
      { type: 'unexpected', key: 'extra' },
    ])
  })

  test('protects interpolation, linked keys, HTML, and escaped characters', () => {
    const result = validateLocalePair(
      { message: 'Hello {name}, @:common.save <strong>now</strong>\\n' },
      { message: 'مرحباً {user}، @:common.save <strong>الآن</strong>' }
    )

    expect(result.issues).toStrictEqual([
      {
        type: 'token-mismatch',
        key: 'message',
        englishTokens: [
          '</strong>',
          '<strong>',
          '@:common.save',
          '\\n',
          '{name}',
        ],
        arabicTokens: ['</strong>', '<strong>', '@:common.save', '{user}'],
      },
    ])
  })

  test('rejects blank, temporary, and unchanged English values', () => {
    const result = validateLocalePair(
      { blank: 'Blank', pending: 'Pending', unchanged: 'Save', api: 'API' },
      {
        blank: '  ',
        pending: 'translation pending',
        unchanged: 'Save',
        api: 'API',
      }
    )

    expect(result.issues.map(({ type, key }) => ({ type, key }))).toStrictEqual(
      [
        { type: 'blank', key: 'blank' },
        { type: 'marker', key: 'pending' },
        { type: 'identical-to-english', key: 'unchanged' },
        { type: 'missing-arabic-script', key: 'unchanged' },
      ]
    )
  })

  test('rejects sentinel keys and malformed JSON', () => {
    const result = validateLocalePair(
      { save: 'Save' },
      { save: 'حفظ', _note: 'TODO' }
    )

    expect(result.issues.map(({ type, key }) => ({ type, key }))).toStrictEqual(
      [
        { type: 'unexpected', key: '_note' },
        { type: 'sentinel', key: '_note' },
      ]
    )
    expect(() => parseLocaleJson('{not json}', 'ar.json')).toThrow(
      'ar.json is not valid JSON'
    )
  })
})
