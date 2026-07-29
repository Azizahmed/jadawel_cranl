/**
 * Plural selection that is actually correct in Arabic.
 *
 * vue-i18n's pipe-separated plurals use the English rule: one form for 1 and one
 * for everything else. Arabic needs six categories, and the difference shows on
 * ordinary numbers — 24 columns is `24 عمودًا`, 200 rows is `200 صف`, and
 * `24 أعمدة` / `200 صفوف` read as machine translation to anyone fluent.
 *
 * Supplying a custom rule to vue-i18n does not work here: this build of
 * @nuxtjs/i18n honours neither `pluralizationRules` (legacy) nor `pluralRules`
 * (composition) from `i18n.config.ts` — both were tried, and the runtime kept
 * applying its own rule, which silently returned the dual form for every count
 * above one. So the category is resolved outside vue-i18n and used to pick a
 * plain, non-plural message key.
 *
 * `Intl.PluralRules` ships the CLDR tables in the browser, so there is no
 * hand-written rule to get wrong or to keep in sync with a locale we add later.
 */

/**
 * The message key suffix for `count` in `locale`.
 *
 * Zero is special-cased ahead of `Intl`: English has no `zero` category, but the
 * interface still wants "No rows" rather than "0 rows", and Arabic wants
 * "لا صفوف". Every other count comes from CLDR.
 */
export function pluralCategory(locale, count) {
  if (count === 0) {
    return 'zero'
  }

  try {
    return new Intl.PluralRules(locale).select(count)
  } catch {
    // An unknown locale tag is not a reason to render nothing.
    return 'other'
  }
}

/**
 * Candidate keys for `count`, most specific first.
 *
 * A locale only defines the categories it uses — English has `one` and `other`,
 * Arabic has all six — so callers walk this list and take the first key that
 * exists. That way an Arabic-only category never has to be duplicated into the
 * English file just to keep the two in step.
 */
export function pluralKeys(base, locale, count) {
  const category = pluralCategory(locale, count)
  return category === 'other'
    ? [`${base}.other`]
    : [`${base}.${category}`, `${base}.other`]
}
