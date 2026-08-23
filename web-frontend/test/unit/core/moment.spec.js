import moment from '@jadawel/modules/core/moment'
// The source text, not the module: the import list is what determines whether a
// locale exists in the bundle, and that cannot be observed at runtime here.
import source from '@jadawel/modules/core/moment.js?raw'

/**
 * A moment locale that is not imported does not exist in the browser bundle — a
 * bundler cannot follow moment's internal lazy `require`. The dangerous part is
 * that `moment.locale('xx')` reports no error for a missing locale: it returns
 * the locale it is still on and carries on formatting in it.
 *
 * That is how every date in an Arabic-first product came out in Ukrainian. `uk`
 * was the last import and therefore moment's active locale, `ar` was never
 * imported, and the `moment.locale('ar')` call in `plugins/i18n.js` silently did
 * nothing. August rendered as `серп`.
 *
 * Note these tests run in Node, where moment *can* resolve a missing locale off
 * disk. So a runtime `moment.locale('ar')` check passes here whether or not the
 * import exists — it cannot reproduce the bundled failure. The import list is
 * therefore asserted against the source text, which is environment-independent.
 */
describe('moment locales', () => {
  // Every locale AGENTS.md says stays selectable, plus `ar` as the default.
  // `en` is built into moment itself and needs no import.
  const OFFERED = ['ar', 'fr', 'nl', 'de', 'es', 'it', 'pl', 'ko', 'uk']

  test.each(OFFERED)(
    'imports the %s locale so the bundle contains it',
    (locale) => {
      expect(source).toContain(`import 'moment/dist/locale/${locale}'`)
    }
  )

  test('sets the starting locale explicitly rather than inheriting it', () => {
    expect(source).toMatch(/^moment\.locale\('en'\)$/m)
  })

  test('strips the Arabic-Indic digit substitution', () => {
    expect(source).toContain("moment.updateLocale('ar'")
    expect(source).toContain('postformat')
  })

  test('renders Arabic month names, not Ukrainian ones', () => {
    moment.locale('ar')
    const august = moment('2026-08-15').format('MMM D')

    expect(august).not.toContain('серп')
    expect(august).toMatch(/[؀-ۿ]/)
  })

  test('keeps Western digits under the Arabic locale', () => {
    // moment's stock `ar` locale rewrites digits into Arabic-Indic form — 25
    // becomes ٢٥ — which AGENTS.md forbids: Western digits (0–9) verbatim. The
    // rest of the interface already follows that, so dates were the one place
    // they would have diverged.
    moment.locale('ar')

    expect(moment('2025-11-03').format('DD/MM/YYYY')).toBe('03/11/2025')
    expect(moment('2025-11-06 11:30:30').format('HH:mm:ss')).toBe('11:30:30')
    expect(moment('2026-08-15').format('MMM D')).not.toMatch(/[٠-٩]/)
  })
})
