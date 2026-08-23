## How to run locally

```bash
cd e2e-tests
# This will do all the yarn installs for you
./run-e2e-tests-locally.sh 
# Once done you can easily just re-run the following:
yarn run test
```

The tests point at `http://localhost:3000` (web-frontend) and
`http://localhost:8000` (backend) unless `PUBLIC_WEB_FRONTEND_URL` and
`PUBLIC_BACKEND_URL` say otherwise.

Run them one at a time against a dev stack:

```bash
yarn run test --workers=1
```

The Nuxt dev server grows as it renders, and a full run gets close to its heap
ceiling. Past it, every page returns a 500 ("Worker terminated due to reaching
memory limit: JS heap out of memory") and the rest of the run fails for reasons
that have nothing to do with the tests. Three parallel browsers get there well
before the suite finishes, which is why `run-e2e-tests-locally.sh` and CI run
single threaded.

`docker-compose.dev.yml` gives the dev frontend
`NODE_OPTIONS=--max-old-space-size=4096` (override with
`JADAWEL_WEB_FRONTEND_NODE_OPTIONS`), which fits a full run. Keep
`JADAWEL_WEB_FRONTEND_MEM_LIMIT` comfortably above it — 6g works — and restart
`web-frontend` before a long run if it has been serving all day.

### Test users

Nearly every test creates its own throwaway user over the API and deletes it
again afterwards, so the tests stay independent and leave no data behind.

The exception is `tests/auth/session.spec.ts`, which signs in through the real
login form with an account that already exists on the instance. It defaults to
`test@test.com` / `test1234` and reads these environment variables when a
different instance is targeted:

```bash
export E2E_EXISTING_USER_EMAIL=someone@example.com
export E2E_EXISTING_USER_PASSWORD=...
```

That test only reads: it signs in and out again without touching the account's
data.

### Fork specific coverage

`tests/i18n/arabicRtl.spec.ts` covers what makes Jadawel a fork: Arabic as the
default locale, `<html dir="rtl">`, and the interface language switch. Because
the UI is translated, page objects anchor on icons and structure (for example
`.context__menu-item-link:has(.iconoir-log-out)`) instead of on button labels
wherever a test has to work in both languages.
### Production-shaped load gate

The default `just e2e test` run first sends 600 requests at concurrency 60 to
the production frontend's plain `/_health` Nitro route. It requires zero errors
and a p95 no higher than 1.5 seconds before Playwright starts. Override the
gate with `LOAD_TOTAL`, `LOAD_CONCURRENCY`, `LOAD_TIMEOUT_MS`,
`LOAD_MAX_ERROR_RATE`, `LOAD_MAX_P95_MS`, `LOAD_BASE_URL`, or comma-separated
`LOAD_PATHS`. `LOAD_BEARER_TOKEN` adds a Jadawel JWT header for authenticated
read-only endpoints. Only configure read-only paths.
