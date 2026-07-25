# Jadawel configuration

Environment variables introduced or changed by Jadawel. Variables inherited unchanged
from the upstream engine are documented inline in the `x-backend-variables` block of
`docker-compose.yml`.

Keep local overrides in `.env.local` — never commit secrets.

## Locale and direction

Jadawel is Arabic-first: the default locale drives both the UI language and the
`dir="rtl"` attribute on `<html>`. The backend and web-frontend each have their own
variable and the two should always be set together.

| Variable | Description | Default |
|---|---|---|
| `BASEROW_DEFAULT_LOCALE` | The default locale assigned to newly created users and used as the fallback UI language. Must be one of the codes in `settings.LANGUAGES` (`ar`, `en`, `fr`, `nl`, `de`, `es`, `it`, `pl`, `ko`, `uk`). Set to `en` to bring the stack up in English/LTR. | `ar` |
| `NUXT_DEFAULT_LOCALE` | The web-frontend default UI locale, used before a user-specific language is known (for example on the login and signup screens). Drives `dir="rtl"` on `<html>`. Should mirror `BASEROW_DEFAULT_LOCALE`; set both to `en` for English/LTR. | `ar` |

> The `BASEROW_` prefix is retained because the underlying engine reads these names
> directly. Renaming the prefix would require touching every deployment recipe and the
> container entrypoints, so it is deliberately left alone.

## Notes

- Anonymous visitors may still be served English if their browser sends
  `Accept-Language: en`, because Nuxt's `detectBrowserLanguage` writes an
  `i18n-language` cookie. Setting `NUXT_DEFAULT_LOCALE` alone does not override that.
- When adding a new backend setting backed by an env var, follow the
  `add-django-config-env-var` skill in `.agents/skills/` and add a row here.
