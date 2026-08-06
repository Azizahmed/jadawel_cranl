# Deploying Jadawel with Coolify

> Deploying to **CranL** instead? None of this applies — it has no Docker
> Compose build pack and cannot build this repo at all. See
> [DEPLOY_CRANL.md](DEPLOY_CRANL.md).

Jadawel is deployed through **Coolify**. Traefik (managed by Coolify) terminates
TLS and routes to the app's Caddy container; Caddy handles internal routing to
the backend, web-frontend and media files.

Do **not** run `docker compose up` by hand on the server. `docker-compose.yml`
joins an external Docker network named `coolify`, which only exists once Coolify
has created it — a manual bring-up fails immediately.

Production domain: **jadawel.azoz.cloud**

## How the routing fits together

```
internet -> Traefik (Coolify, TLS via letsencrypt)
              -> caddy      (expose: 80, no published ports)
                   -> web-frontend:3000   (UI)
                   -> backend:8000        (/api, /ws, /mcp, /assistant)
                   -> /baserow/media      (uploaded files)
```

Two consequences worth internalising:

- **Caddy does not issue certificates here.** Traefik does, via its
  `letsencrypt` certresolver. `JADAWEL_CADDY_ADDRESSES` should stay at its `:80`
  default — setting it to an `https://` URL would make Caddy try to obtain its
  own certificate on a port it cannot reach, and the deploy will hang.
- **Ports 80/443 are not published by this stack.** Only Traefik binds them. Do
  not open app ports in the VPS firewall.

## 1. Prerequisites

- A VPS with **Coolify installed** and reachable on its dashboard port.
- A DNS **A record** for `jadawel.azoz.cloud` pointing at the VPS IPv4. Traefik
  cannot issue a certificate until this resolves publicly.
- Enough RAM to *build*. The Nuxt production build regularly peaks above 4 GB —
  well beyond what the app needs at rest. On a 4 GB VPS add swap before the
  first deploy or the build is OOM-killed with no useful error:

```bash
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 2. Create the resource in Coolify

1. **Project → New Resource → Private Repository (with GitHub App)**, or
   *Public Repository* + a deploy key. The repo is private, so anonymous clone
   will not work.
2. Repository `Azizahmed/Jadawel`, branch **`codex/hostinger-coolify-deploy`**
   (this is the branch carrying the Coolify configuration).
3. **Build Pack: `Docker Compose`**.
4. Docker Compose location: `/docker-compose.yml`.

Coolify builds the `jadawel/backend`, `jadawel/web-frontend` and `jadawel/caddy`
images from source on each deploy. They are not published to any registry, so
there is nothing to pull and no registry credentials to configure.

## 3. Environment variables

Set these in the resource's **Environment Variables** tab. The three secrets must
each be a distinct random value:

```bash
for n in SECRET_KEY DATABASE_PASSWORD REDIS_PASSWORD; do echo "$n=$(tr -dc 'a-z0-9' </dev/urandom | head -c50)"; done
```

| Variable | Value | Notes |
|---|---|---|
| `SECRET_KEY` | *generated* | Rotating this invalidates all sessions. |
| `DATABASE_PASSWORD` | *generated* | |
| `REDIS_PASSWORD` | *generated* | |
| `JADAWEL_PUBLIC_URL` | `https://jadawel.azoz.cloud` | Must match the browser URL exactly — scheme included, no trailing slash. |
| `DATABASE_USER` | `baserow` | |
| `DATABASE_NAME` | `baserow` | |

`JADAWEL_PUBLIC_URL` is the one people get wrong. It is baked into API calls,
websocket URLs and outbound email links. If it disagrees with the address in the
browser, the UI loads but the grid never populates and realtime silently dies.

Optional — outbound email (password resets, invitations) simply does not work
until SMTP is set:

```
EMAIL_SMTP=yes
EMAIL_SMTP_HOST=smtp.hostinger.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USE_TLS=yes
EMAIL_SMTP_USER=no-reply@azoz.cloud
EMAIL_SMTP_PASSWORD=<mailbox password>
FROM_EMAIL=no-reply@azoz.cloud
```

## 4. Domain

The domain is **hardcoded in the Traefik labels** on the `caddy` service in
`docker-compose.yml`, in two router rules:

```
traefik.http.routers.jadawel-http.rule=Host(`jadawel.azoz.cloud`) && PathPrefix(`/`)
traefik.http.routers.jadawel-https.rule=Host(`jadawel.azoz.cloud`) && PathPrefix(`/`)
```

To move to another domain you must edit both lines and commit — setting a
different domain in Coolify's UI alone will not route, because Traefik matches
on these labels. Update `JADAWEL_PUBLIC_URL` to match at the same time.

## 5. Deploy

Hit **Deploy**. The first build compiles three images and takes roughly 15–30
minutes; later deploys reuse layers and are much faster. Database migrations run
automatically on backend startup.

Watch the deploy log, then the backend container log, until the backend reports
it is listening.

## 6. Create the first admin account

Open `https://jadawel.azoz.cloud` and **sign up through the web form**. The first
account created becomes staff automatically.

Do **not** use `createsuperuser` for the first account. The instance flag
`show_admin_signup_page` is only cleared by the signup API, so an account made
through the CLI leaves it set — and `/login` then permanently redirects to
`/signup`, with no way in through the UI.

## 7. Updating

Push to `codex/hostinger-coolify-deploy` and press **Redeploy** (or enable
automatic deploys on push). Coolify rebuilds and restarts with no manual steps.

## Backups

Coolify can schedule Postgres backups for the `db` service — use it. Two caveats:

- A `pg_dump` does **not** include uploaded files. They live in the `media`
  Docker volume and must be backed up separately.
- Never restore the local development database onto production. It contains
  `dev@baserow.io` and `e2e@baserow.io` — staff accounts whose password
  (`testpassword`) is hardcoded in Baserow's public repository. Production
  settings never create them, so a clean install is safe; a restored dev dump is
  not.

Manual media backup:

```bash
docker run --rm -v jadawel_media:/m -v ~:/out alpine tar czf /out/jadawel-media-$(date +%F).tar.gz -C /m .
```

## Troubleshooting

**`network coolify declared as external, but could not be found`** — the stack is
being brought up outside Coolify. Deploy through Coolify instead.

**Traefik returns 404 for the domain** — the `Host()` rules in the compose labels
do not match the domain you are requesting. See §4.

**Certificate never issues** — the A record must resolve publicly to this VPS
*before* Traefik can complete the ACME challenge. Check the Traefik/proxy logs
from Coolify's dashboard.

**UI loads but the grid stays empty, websockets fail** — `JADAWEL_PUBLIC_URL`
does not exactly match the browser URL.

**Deploy hangs while starting Caddy** — `JADAWEL_CADDY_ADDRESSES` was set to an
`https://` value. Leave it unset; Traefik owns TLS.

**Build killed with no error** — out of memory. Add swap (§1) and redeploy.

**English UI instead of Arabic** — expected for browsers sending
`Accept-Language: en`; Nuxt's language detection writes a cookie that overrides
the default. See [CONFIGURATION.md](CONFIGURATION.md).
