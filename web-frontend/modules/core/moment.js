// Moment should always be imported from here. This will enforce that the timezone
// is always included. There were some problems when Jadawel is installed as a
// dependency and then moment-timezone does not work. Still will resolve that issue.
import moment from 'moment-timezone'
// Every locale the app offers needs an explicit import. A bundler cannot follow
// moment's internal lazy `require`, so a locale that is not imported here simply
// does not exist at runtime — and `moment.locale()` reports no error when asked
// for one. It returns the locale it is *still* on and carries on.
//
// `ar` was the one missing, which is why every date in the product rendered in
// Ukrainian: `uk` was the last import and therefore moment's active locale, and
// the `moment.locale('ar')` call in `plugins/i18n.js` was a silent no-op. August
// came out as `серп`. Arabic is this fork's default language, so the omission
// was visible on the very first screen.
import 'moment/dist/locale/ar'
import 'moment/dist/locale/fr'
import 'moment/dist/locale/nl'
import 'moment/dist/locale/de'
import 'moment/dist/locale/es'
import 'moment/dist/locale/it'
import 'moment/dist/locale/pl'
import 'moment/dist/locale/ko'
import 'moment/dist/locale/uk'

// moment's stock `ar` locale rewrites every digit into its Arabic-Indic form —
// 25 becomes ٢٥ — through a `postformat` hook. AGENTS.md requires Western digits
// (0–9) verbatim throughout the product, and the rest of the interface already
// follows that, so a date is the one place they would have diverged. Dropping
// the digit substitution keeps month and day *names* Arabic, which is the part
// that was actually missing.
//
// The Arabic comma is kept: it is punctuation, not a digit.
moment.updateLocale('ar', {
  postformat: (string) => string.replace(/,/g, '،'),
})

// Importing a locale file makes it moment's *current* locale as a side effect, so
// without this the starting locale is whichever import happens to be last — an
// ordering accident, and the reason every date rendered in Ukrainian.
//
// Pinned to `en` rather than to the product default: `plugins/i18n.js` owns the
// real locale and sets it from the user's, so this is only the baseline before
// that runs. Choosing `ar` here instead would make this module disagree with
// whatever locale the app is actually in whenever the plugin has not run —
// which is exactly the situation in tests, where the app locale is `en`.
moment.locale('en')

export default moment
