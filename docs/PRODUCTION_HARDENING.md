# Production hardening — findings and what is left to do

Audit of `https://jadawel.azoz.cloud` performed 2026-07-29 against the live
deployment. Everything below was measured against production, not inferred from
the source.

Findings split into three groups: **fixed in this repo** (deploy to apply),
**you must change in the admin panel or Coolify** (I cannot reach either), and
**needs data from the server** (the self-reload problem).

---

## 1. Fixed in the repo

### 1.1 Every page shipped the entire stylesheet inline — 1.8 MB, uncacheable

The single biggest cause of the app feeling slow.

Nuxt inlines CSS into the SSR response by default. That is a good trade for a
small stylesheet. Jadawel's is **1,870,576 bytes**, so every document request
re-sent ~188 KB gzipped of CSS that the browser could not cache, and the browser
re-parsed all of it before first paint. Production was serving
`entry.tn0RQdqM.css` at **0 bytes** — proof that all of it had moved inline.

Fixed with `features.inlineStyles: false` in `config/nuxt.config.prod.ts`. A
verification build now emits `entry.*.css` as a real 1.8 MB file under `/_nuxt/`,
which already carries `Cache-Control: public, max-age=31536000, immutable`.

Expect the HTML for `/login` to drop from ~1.88 MB to roughly 50 KB, and repeat
navigations to stop paying for CSS at all.

### 1.2 Complete original source code was downloadable

`https://jadawel.azoz.cloud/_nuxt/DtultdTW.js.map` returned **200 with 4.2 MB**
of source maps — the readable original of the whole frontend, including the
`arabase` module.

Two changes, because either alone is insufficient:

- `sourcemap.client: 'hidden'` strips the `sourceMappingURL` pointer from all 81
  chunks. Verified: 81 maps still emitted (so they can be uploaded to an error
  tracker) and 0 references remain.
- Caddy returns 404 for `/_nuxt/*.map` and `/static/*.map`. `hidden` only
  removes the *pointer*; the files stay on disk and remain fetchable by anyone
  who guesses the URL. This is what actually closes it.

The map rule is scoped to build output, so a user who uploads a file called
`something.map` can still download their own file.

### 1.3 No security headers at all

Production sent none of `Strict-Transport-Security`, `X-Content-Type-Options`,
`Referrer-Policy` or `Permissions-Policy`, and advertised `X-Powered-By: Nuxt`.

Added to the `Caddyfile`, so they survive a change of edge proxy and a local
bring-up behaves like production.

> **HSTS is sticky.** A browser that sees `max-age=31536000` will refuse plain
> HTTP for this host for a year, even if the header is later removed. This is
> safe here because Traefik already redirects HTTP to HTTPS unconditionally and
> the Let's Encrypt certificate is valid to 2026-10-25 — but know that it is a
> one-way door.

No global `Content-Security-Policy` is set. Nuxt serves inline bootstrap
scripts, so a useful policy needs nonces or hashes; a guessed one would break the
app silently. Uploaded files under `/media/` keep their existing, much stricter
`sandbox` policy, which is where an injected script would actually be dangerous.

### 1.4 Clickjacking — the whole app could be framed by any site

`frame-ancestors 'self'` plus `X-Frame-Options: SAMEORIGIN` now apply to the
signed-in application, and deliberately **not** to `/form/*` and `/public/*`,
which are the shared links customers embed in their own sites.

`'self'` rather than `'none'` because clickjacking requires a *third-party* page
to do the framing, and the application builder previews pages in a same-origin
iframe that `'none'` would break.

The headers use Caddy's `>` replace prefix. Without it, a request that returns an
upstream error through this route ends up with two conflicting `X-Frame-Options`
values, because Django sends its own `DENY` — this was observed in testing, not
theorised.

> **Worth verifying with a real form.** Production returns
> `X-Frame-Options: DENY` on `/form/<unknown-slug>`. That is Django's header
> leaking through an error response, but it means embedding may *already* be
> blocked for real forms too. My change cannot make this worse — it adds nothing
> to those paths — but if you rely on embedding, test one real form in an iframe.

### 1.5 No rate limiting on login

Twelve failed logins sent back to back all returned `401`. Never a `429`.
Baserow's own throttle (`BASEROW_MAX_CONCURRENT_USER_REQUESTS`) defaults to off,
and it throttles concurrency per user rather than attempts per IP, so it is the
wrong tool for credential stuffing.

Added a Traefik rate-limit middleware on `docker-compose.yml`, on a dedicated
higher-priority router matching only the credential endpoints:

| Endpoint | Why |
|---|---|
| `/api/user/token-auth/` | login |
| `/api/user/token-refresh/` | token refresh |
| `/api/user/send-reset-password-email/` | reset-email flooding |
| `/api/user/reset-password/` | reset-token guessing |

5 requests/second average, burst 20, per client IP. A real person signing in
never sees it; guessing a password stops being practical.

`ipstrategy.depth=1` reads the client IP from `X-Forwarded-For` rather than the
socket. Without it every request shares one bucket and the whole site would rate
limit together.

---

## 2. You need to change these — I cannot reach the admin panel or Coolify

### 2.1 Sign-ups are open to the internet (highest priority)

`GET /api/settings/` returns, unauthenticated:

```json
{"allow_new_signups": true, "email_verification": "no_verification",
 "captcha": {"enabled": false}, "allow_global_workspace_creation": true}
```

Anyone who finds the domain can create an account, with no email verification
and no CAPTCHA. You chose **open but verified**, which needs three things:

1. **Admin → Settings → email verification: `enforced`.** This does nothing
   until SMTP works, so do step 2 first or nobody can register at all.
2. **SMTP configured in Coolify.** `docs/DEPLOYMENT.md` §3 has the variable
   list. Send yourself a password reset to confirm before enabling enforcement.
3. **CAPTCHA.** Set in Coolify, then enable in the admin panel:
   ```
   BASEROW_ENABLE_CAPTCHA=true
   BASEROW_CAPTCHA_PROVIDER=cloudflare_turnstile
   BASEROW_CLOUDFLARE_TURNSTILE_SITE_KEY=<site key>
   BASEROW_CLOUDFLARE_TURNSTILE_SECRET_KEY=<secret key>
   ```
   Email verification alone stops neither scripted signup nor disposable
   addresses; the CAPTCHA is what stops the bot.

Until all three are in place, consider `allow_new_signups: false` — invitations
still work with it off.

### 2.2 JWT signing key is not separated from `SECRET_KEY`

`SIGNING_KEY` falls back to `SECRET_KEY` when `BASEROW_JWT_SIGNING_KEY` is
unset, and the deployment guide never listed it. The consequence is operational:
rotating a leaked signing key means rotating `SECRET_KEY`, which invalidates far
more than sessions.

Set a distinct random value in Coolify:

```bash
echo "BASEROW_JWT_SIGNING_KEY=$(tr -dc 'a-z0-9' </dev/urandom | head -c50)"
```

Setting it logs every user out once. Do it before you have real users.

### 2.3 `BASEROW_ENABLE_SECURE_PROXY_SSL_HEADER` is not set

Django cannot tell that requests arrived over HTTPS, because TLS terminates at
Traefik. Set it to `yes` in Coolify. It also makes the entrypoint pass
`--forwarded-allow-ips='*'` to gunicorn, which is what lets the rate limiting
above see real client IPs rather than the proxy's.

### 2.4 Template sync runs on every backend start, for up to 30 minutes

`SYNC_TEMPLATES_ON_STARTUP` defaults to `true` and
`BASEROW_SYNC_TEMPLATES_TIME_LIMIT` to `1800` seconds. Every deploy and every
restart re-imports the full template library, saturating Postgres while it runs.
On a small VPS this alone makes the app feel broken for a long stretch after
each deploy.

Set `SYNC_TEMPLATES_ON_STARTUP=false` in Coolify and run it deliberately when
you actually change templates:

```bash
docker exec <backend-container> ./baserow.sh backend-cmd manage sync_templates
```

### 2.5 Postgres backups

Coolify can schedule them; `docs/DEPLOYMENT.md` covers the two traps
(`pg_dump` excludes uploaded files, and never restore a dev dump — it contains
staff accounts whose password is public in Baserow's repository).

---

## 3. Not yet diagnosed — the app reloading while you work

I could not reproduce this from outside, and I ruled out the obvious causes
rather than guessing:

| Suspected cause | Measured | Verdict |
|---|---|---|
| Websockets failing, so the client gives up and reloads | `101 Switching Protocols` in 0.44 s; anonymous auth frame returns `success: true` | **Not the cause** |
| Backend slow or timing out | `/api/_health/` 0.28–0.36 s, `/api/settings/` 0.32 s across 5 runs | **Not the cause** |
| TLS or redirect loop | Single clean redirect, TLS 1.3, valid certificate | **Not the cause** |
| Containers restarting (OOM) | Cannot be observed remotely | **Untested — most likely** |
| Slow first paint being *perceived* as a reload | `/login` took 1.03–2.08 s for 1.88 MB | **Contributing; §1.1 addresses it** |

Run `docs/diagnose-production.sh` on the VPS and send back the output:

```bash
bash docs/diagnose-production.sh > jadawel-diagnostics.txt 2>&1
```

It is read-only — it restarts nothing and changes nothing. The decisive sections
are the kernel OOM log and the container restart counts. If those are clean, the
reload is happening in the browser and the next place to look is the devtools
console with "Preserve log" enabled.

---

## 4. Noted, not acted on

- **`CORS_ORIGIN_ALLOW_ALL = True`** (upstream default). Lower risk than it
  looks because tokens live in `localStorage`, not cookies, so a hostile origin
  cannot read them — but it does mean any site can call the API from a browser.
- **JWT passed in the websocket query string** (`/ws/core/?jwt_token=…`).
  Upstream design. Query strings land in proxy access logs, so treat Traefik and
  Caddy logs as containing credentials, and keep their retention short.
- **`/api/schema.json` returns 500.** Consequence: `/api/redoc/` serves a broken
  spec. Almost certainly fallout from the premium/enterprise strip. Cosmetic,
  but it is a public endpoint throwing an unhandled error.
- **`deploy/*/.env.testing` files are committed** with `SECRET_KEY=baserow`.
  They are upstream test fixtures for the nginx/apache recipes and are not used
  by the Coolify deployment — but do not copy one as a starting point.
- **Anonymous websocket connections are accepted.** Default Baserow behaviour,
  required for public views. Set
  `DISABLE_ANONYMOUS_PUBLIC_VIEW_WS_CONNECTIONS=yes` if you never share views
  publicly.
- **`BASEROW_CACHALOT_ENABLED` is off.** Baserow's own ORM query cache. Worth
  trying once the reload problem is understood — not before, so you can tell
  which change did what.
