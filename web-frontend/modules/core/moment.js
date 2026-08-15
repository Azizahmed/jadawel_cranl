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

// Importing a locale file makes it moment's *current* locale as a side effect, so
// without this the starting locale is whichever import happens to be last — an
// ordering accident rather than a decision. Pinned to the product default, which
// mirrors `defaultLocale` in `config/nuxt.config.base.ts`. Hardcoded rather than
// read from there because that is build configuration, not a runtime module; the
// i18n plugin switches this per user as soon as it loads either way.
moment.locale('ar')

export default moment
