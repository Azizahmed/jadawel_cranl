import { computed } from 'vue'
import gridSortable from './directives/gridSortable'

/**
 * Arabase (Jadawel) frontend plugin.
 *
 * Runs once at app startup. Its first responsibility (Phase 1.1) is to make the
 * document direction follow the active locale: Arabic (and any other `dir: 'rtl'`
 * locale declared in config/locales.js) renders the whole app RTL, English LTR.
 *
 * We drive `<html dir>` / `<html lang>` from the locale's `dir` field via useHead
 * so it is correct during SSR (no first-paint flash) and stays reactive when the
 * user switches language. Setting `dir` on the root <html> is also what makes RTL
 * propagate into Teleported DOM (modals, dropdowns, tooltips) — they mount under
 * <body>, which inherits direction from <html>. See docs/AUDIT.md §9.4.
 *
 * Later phases register RTL-aware field components and other Arabic-first
 * behaviour here.
 */
export default defineNuxtPlugin({
  name: 'arabase',
  // Ensure i18n is set up before we read the active locale.
  dependsOn: ['i18n'],
  setup(nuxtApp) {
    // Grid-aware drag & drop for the dashboard widget board. Registered here
    // (rather than in core's global.js) to keep the fork additive.
    nuxtApp.vueApp.directive('gridSortable', gridSortable)

    const i18n = nuxtApp.$i18n
    if (!i18n) {
      return
    }

    const dirFor = (code) => {
      const locales = unref(i18n.locales) || []
      const match = locales.find((l) => (l.code || l) === code)
      return (match && match.dir) || 'ltr'
    }

    const htmlAttrs = computed(() => {
      const code = unref(i18n.locale)
      return { lang: code, dir: dirFor(code) }
    })

    useHead({ htmlAttrs })
  },
})
