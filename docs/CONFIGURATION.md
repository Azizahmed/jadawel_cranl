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
| `JADAWEL_DEFAULT_LOCALE` | The default locale assigned to newly created users and used as the fallback UI language. Must be one of the codes in `settings.LANGUAGES` (`ar`, `en`, `fr`, `nl`, `de`, `es`, `it`, `pl`, `ko`, `uk`). Set to `en` to bring the stack up in English/LTR. | `ar` |
| `NUXT_DEFAULT_LOCALE` | The web-frontend default UI locale, used before a user-specific language is known (for example on the login and signup screens). Drives `dir="rtl"` on `<html>`. Should mirror `JADAWEL_DEFAULT_LOCALE`; set both to `en` for English/LTR. | `ar` |

> The `BASEROW_` prefix is retained because the underlying engine reads these names
> directly. Renaming the prefix would require touching every deployment recipe and the
> container entrypoints, so it is deliberately left alone.

## Security and rate limiting

| Variable | Description | Default |
|---|---|---|
| `JADAWEL_ENABLE_SECURE_PROXY_SSL_HEADER` | Tells Django it sits behind a TLS-terminating proxy. Also switches on `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` and HSTS. Leave it on for any deployment reached over HTTPS; turn it off only for plain-HTTP local work. | `yes` |
| `JADAWEL_NUM_PROXIES` | How many reverse proxies rewrite `X-Forwarded-For` in front of the app. This is what makes per-client rate limiting countable: unset, DRF keys throttles on the whole forwarded header, which the caller controls, so a limit can be bypassed by varying it. | `1` |
| `JADAWEL_SECURE_HSTS_SECONDS` | `Strict-Transport-Security` max-age. Only applied when the proxy header above is enabled. | `31536000` |
| `JADAWEL_SECURE_HSTS_INCLUDE_SUBDOMAINS` | Adds `includeSubDomains` to HSTS. | `true` |
| `JADAWEL_SECURE_HSTS_PRELOAD` | Adds `preload` to HSTS. Do not enable until you intend to submit the domain. | off |
| `JADAWEL_CONTACT_FORM_RATE` | DRF rate for the public contact endpoint, e.g. `5/hour`. An unparseable value is ignored with a warning rather than failing every request. | `5/hour` |
| `JADAWEL_DASHBOARD_AUTH_RATE` | DRF rate for guessing a public dashboard's share password, keyed per link and caller. | `10/hour` |
| `JADAWEL_DASHBOARD_SHARE_TOKEN_HOURS` | How long the token issued after entering a share password stays valid. | `168` |

## Database backups

Read by `arabase.backup` and the `arabase.tasks.backup_database` Celery task. All of
these must be present in the `x-backend-variables` block of the compose file, or the
backend and `celery-beat` containers never see them and the job silently does nothing.
See `docs/BACKUP_RESTORE.md` for the full procedure.

| Variable | Description | Default |
|---|---|---|
| `JADAWEL_BACKUP_ENABLED` | Master switch. Off means the scheduled task is never registered. | off |
| `JADAWEL_BACKUP_S3_BUCKET` | Destination bucket. Required. | — |
| `JADAWEL_BACKUP_S3_PREFIX` | Key prefix. **Must not be empty**: retention lists and deletes under this prefix, so an empty one means the whole bucket. Validation rejects it. | `postgres/` |
| `JADAWEL_BACKUP_S3_ENDPOINT_URL` | For S3-compatible providers. | AWS |
| `JADAWEL_BACKUP_S3_REGION` | Bucket region. | — |
| `JADAWEL_BACKUP_S3_ACCESS_KEY_ID` | Required. Keep separate from the `AWS_*` user-file credentials — the media bucket is public-read. | — |
| `JADAWEL_BACKUP_S3_SECRET_ACCESS_KEY` | Required. | — |
| `JADAWEL_BACKUP_S3_SSE` | Server-side encryption header, e.g. `AES256`. Empty disables it. | off |
| `JADAWEL_BACKUP_RETENTION_DAYS` | Age after which a backup is deleted. Only objects named `jadawel-<timestamp>.dump` are ever removed. | `14` |
| `JADAWEL_BACKUP_CRONTAB` | Schedule. Default is 23:00 UTC = 02:00 Riyadh. | `0 23 * * *` |
| `JADAWEL_BACKUP_TIMEOUT_SECONDS` | pg_dump timeout. The Celery soft limit is derived from this. | `3600` |
| `JADAWEL_BACKUP_INCLUDE_MEDIA` | Archive user-uploaded files alongside the dump, stamped with the same timestamp so the two restore together. Defaults on unless `AWS_STORAGE_BUCKET_NAME` is set, in which case the files are already in object storage. | on |

## Resource limits

Every compose service takes a `mem_limit` from an env var so caps can be matched to the
host without editing the compose file: `JADAWEL_BACKEND_MEM_LIMIT` (`1g`),
`JADAWEL_WEB_FRONTEND_MEM_LIMIT` (`768m`), `JADAWEL_CELERY_MEM_LIMIT` (`768m`),
`JADAWEL_CELERY_EXPORT_MEM_LIMIT` (`768m`), `JADAWEL_CELERY_BEAT_MEM_LIMIT` (`384m`),
`JADAWEL_DB_MEM_LIMIT` (`1g`), `JADAWEL_REDIS_MEM_LIMIT` (`256m`),
`JADAWEL_CADDY_MEM_LIMIT` (`192m`), `JADAWEL_FIXER_MEM_LIMIT` (`64m`).

## Notes

- Anonymous visitors may still be served English if their browser sends
  `Accept-Language: en`, because Nuxt's `detectBrowserLanguage` writes an
  `i18n-language` cookie. Setting `NUXT_DEFAULT_LOCALE` alone does not override that.
- When adding a new backend setting backed by an env var, follow the
  `add-django-config-env-var` skill in `.agents/skills/` and add a row here.
