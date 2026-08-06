/**
 * Shared locales configuration for all Jadawel modules.
 * This is the single source of truth for supported languages.
 *
 * Jadawel ships Arabic and English only. The upstream project's other
 * translations were removed deliberately: they were partial, unreviewed, and
 * carried the same machine-translation defects the Arabic pass had to correct.
 * Keep this list in sync with `LANGUAGES` in
 * `backend/src/jadawel/config/settings/base.py` — the backend validates the
 * user's language choice against that list.
 *
 * To add a language:
 * 1. Add the locale entry here and to the backend `LANGUAGES`
 * 2. Add a migration altering `UserProfile.language` choices
 * 3. Create the corresponding .json translation files in each module's locales/ directory
 */
export const locales = [
  // Jadawel fork: Arabic is the primary, first-class locale. `dir: 'rtl'` is the
  // single source of truth consumed by the arabase direction plugin to set
  // <html dir/lang>. Keep it first so it reads as the default in language menus.
  { code: 'ar', name: 'العربية', file: 'ar.json', dir: 'rtl' },
  { code: 'en', name: 'English', file: 'en.json', dir: 'ltr' },
]
