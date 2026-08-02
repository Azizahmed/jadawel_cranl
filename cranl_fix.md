# CranL deployment — what broke, why, and how to fix it again

Reference for the CranL deployment of Jadawel, written after getting it from
"nothing works" to a running app on 2026-08-02. Read
[docs/DEPLOY_CRANL.md](docs/DEPLOY_CRANL.md) for the procedure; this file is the
diagnostic history and the runbook for when it breaks.

Live at **https://jadawel-img0kf.cranl.net** (custom domain `jadawl.site`
pending DNS).

---

## The shape of it

CranL cannot build this repository. It offers Railpack (auto-detect) and
Dockerfile as build types — no Docker Compose — and its Pro plan gives 4 GB per
app, while the Nuxt production build peaks above that. So the build happens on a
GitHub runner and CranL only pulls the result:

```
Azizahmed/Jadawel  (source of truth, Coolify prod at jadawel.azoz.cloud)
   │  copied to
   ▼
Azizahmed/jadawel_cranl @ main   ← deployment repo, this one
   │  .github/workflows/publish-image.yml, on a 16 GB runner
   ▼
ghcr.io/azizahmed/jadawel_cranl:2.2.2   (public package, 437 MB, 19 layers)
   │  root Dockerfile: FROM that tag
   ▼
CranL app "jadawel"  →  Bunny CDN edge  →  container :80 (Caddy)
                                              ├── web-frontend :3000
                                              └── backend :8000
   external: jadawel-postgres, jadawel-redis, jadawel-media (all Riyadh / Saudi-4)
```

**Pushing code does not change what is deployed.** Publish a new image first.

The image is the `prod-lite` target — no embedded Postgres or Redis, because
CranL apps have no persistent volume and an embedded database would be destroyed
on every redeploy.

---

## The five failures, in the order they happened

### 1. `Railpack could not determine how to build the app`

Railpack looks for an application manifest at the repository root. This is a
monorepo whose manifests live in `backend/` and `web-frontend/`, so detection
failed before any build step.

**Fix:** build type **Dockerfile**, with a `Dockerfile` at the repository root.
It must be named exactly that and sit at the root regardless of what the
wizard's path field suggests.

**Note:** build type and branch can only be set at app creation — Settings
exposes only domain, port and delete, and there is no update-application API. A
wrong build type means deleting the app and recreating it.

### 2. `401 Unauthorized` pulling from ghcr.io

The GHCR package was private. CranL has nowhere to store a registry
credential — not in the create wizard, not in Settings.

**Fix:** make the *package* public. This is separate from repository visibility;
a package only inherits it at creation. The toggle lives at
`github.com/users/Azizahmed/packages/container/jadawel_cranl/settings` →
Danger Zone, **not** in the repository's settings.

Verify from anywhere, no credentials needed:

```bash
TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:azizahmed/jadawel_cranl:pull&service=ghcr.io" | jq -r .token)
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
  https://ghcr.io/v2/azizahmed/jadawel_cranl/manifests/2.2.2
# 200 = CranL can pull it. 401 = package is still private.
```

Checked before publishing: no credentials ship in the image (the only
secret-shaped files are `deploy/*/.env.testing`, whose every value is the
literal string `baserow`), and there is no license obstacle — this fork has zero
files under `premium/` or `enterprise/`, so it is MIT plus CC-BY-SA docs.

### 3. The log showed one line and stopped

The container log contained only Baserow's warning about running without a
mounted data folder, hiding everything after it.

**Fix:** `DISABLE_VOLUME_CHECK=yes`. Safe here because Postgres and Redis are
external; only media and Caddy state live in `/baserow/data`, and media belongs
in S3 anyway.

### 4. The real cause — `EADDRINUSE: address already in use :::80`

With the boot unblocked, the actual failure appeared: the Nuxt web-frontend
crash-looping on port 80, retrying four times, reaching supervisor `FATAL`, at
which point Baserow's watcher declared a crash and shut down the whole
container.

**Why:** Caddy owns `:80` inside the all-in-one image; the frontend belongs on
3000. CranL injects `PORT=80` into the container to match the app's routing
port, and Nitro reads `PORT` to decide where to listen — so the frontend kept
trying to take Caddy's socket.

**Fix:** set `PORT=3000` explicitly in the environment. `NITRO_PORT=3000` and
`BASEROW_WEB_FRONTEND_PORT=3000` alone did **not** win; `PORT` overrides them.
A runtime env var set on the app beats CranL's injected one, which is why this
works and why it cannot be baked into the image instead.

This is the failure most likely to recur, because it comes back the moment
`PORT` is cleared or the app is recreated.

**How it presents:** every path returns HTTP 502 from BunnyCDN in well under a
second. A fast 502 on `/`, `/api/settings/` and `/_health/` alike means nothing
is bound to :80 in the container — Caddy up but backends down would give slower,
path-dependent responses instead.

### 5. Container cycled a few times during first-boot migrations

Expected, not a fault. Django migrations resume where they left off, so the
restarts worked through them and it came up clean.

---

## Working environment variables

| Variable | Value | Why |
|---|---|---|
| `PORT` | `3000` | **Critical.** Overrides CranL's injected `PORT=80`, which otherwise makes Nuxt fight Caddy for the socket (§4). |
| `DISABLE_VOLUME_CHECK` | `yes` | Unblocks boot; no persistent volume by design (§3). |
| `SECRET_KEY` | *50 chars, generated* | Must be explicit — `baserow.sh:201` otherwise writes one to the ephemeral `/baserow/data/.secret`, so every redeploy would invalidate all sessions. |
| `BASEROW_JWT_SIGNING_KEY` | *50 chars, generated* | Same, via `.jwt_signing_key`. |
| `BASEROW_PUBLIC_URL` | current domain, no trailing slash | Baserow rejects requests on any host that does not match. Must be switched when the domain changes. |
| `DATABASE_URL` | internal, from `jadawel-postgres` | |
| `REDIS_URL` | internal, from `jadawel-redis` | Celery and websockets do not work without Redis; no BaaS replaces it. |
| `DISABLE_EMBEDDED_PSQL` | `yes` | Required on the lite image — the startup script otherwise runs `chown -R postgres:postgres` for a user that exists only in the full image. |
| `DISABLE_EMBEDDED_REDIS` | `yes` | Same, for `chown -R redis:redis`. |
| `BASEROW_RUN_MINIMAL` | `yes` | Folds the export worker into the main worker (`backend/docker/docker-entrypoint.sh:373-393`). |
| `BASEROW_AMOUNT_OF_WORKERS` | `1` | Required for the above to take effect. |
| `SYNC_TEMPLATES_ON_STARTUP` | `false` | Removes a step that can take 30 minutes from every boot. Templates can be synced later on demand. |

Leave `BASEROW_CADDY_ADDRESSES` unset. Its `:80` default is correct — CranL owns
TLS, and pointing Caddy at an `https://` address makes it try to obtain its own
certificate on a port it cannot reach, which hangs the deploy.

### Not yet set, and should be

| Variable | Why |
|---|---|
| `BASEROW_ENABLE_SECURE_PROXY_SSL_HEADER=yes` | TLS terminates at CranL's proxy, so Django cannot currently tell requests arrived over HTTPS. Also passes `--forwarded-allow-ips='*'` to gunicorn so real client IPs are visible. See `docs/PRODUCTION_HARDENING.md` §2.3. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL` | **Uploaded files are lost on every redeploy until these exist.** Blocked on a CranL bug: creating a bucket token returns "Quota limit exceeded. You can create no more than 50 tokens". Any S3-compatible provider works as a fallback, at the cost of files leaving Saudi Arabia. |

---

## App settings that cannot be changed later

| Setting | Value |
|---|---|
| Repository | `Azizahmed/jadawel_cranl` |
| Branch | `main` |
| Build path | `/` |
| Build type | Dockerfile, path `Dockerfile` |
| Port | **80** — the image serves through its bundled Caddy |

---

## Runbook

### Deploying a code change

1. Merge the change into `Azizahmed/jadawel_cranl` `main`. Feature work belongs
   in `Azizahmed/Jadawel`; this repo is a deployment copy, and committing
   directly here diverges the two trees.
2. Actions → **Publish all-in-one image** → Run workflow, with a new tag.
   Roughly 10 minutes.
3. Bump `ARG JADAWEL_IMAGE` in the root `Dockerfile` to that tag and commit.
   Leaving it at `latest` means a redeploy silently picks up whatever was
   published last.
4. Redeploy on CranL.

Skipping 2 or 3 redeploys the identical image.

### Changing only environment variables

Actions → **Reload**. It picks up env changes without a rebuild.

Note: **Deploy** returned "USA region is temporarily unavailable for new
deployments" on 2026-08-02, which is why Reload was used. Worth re-running a
real deploy once that clears.

### Moving to `jadawl.site`

1. Point the DNS at `jadawel-img0kf.cranl.net`. An apex `CNAME` is invalid DNS —
   use the provider's `ALIAS`/`ANAME`, or Cloudflare's CNAME flattening. On
   Cloudflare keep the record **DNS-only (grey cloud)** until the certificate
   issues, or the proxy intercepts the ACME challenge.
2. Once SSL is active, set `BASEROW_PUBLIC_URL=https://jadawl.site` and Reload.
   Baserow rejects requests on any host that does not match it, so the two must
   change together.

---

## Troubleshooting by symptom

| Symptom | Cause | Fix |
|---|---|---|
| Fast 502 from BunnyCDN on every path | Nothing bound to :80 — container crashed or crash-looping | Read the container log. Most likely `PORT` is not 3000 (§4). |
| `EADDRINUSE :::80` in the log | Nuxt taking Caddy's port | `PORT=3000` |
| Log stops after the data-folder warning | Volume check blocking boot | `DISABLE_VOLUME_CHECK=yes` |
| `chown` / "no such user" at startup | Embedded services not disabled on the lite image | `DISABLE_EMBEDDED_PSQL=yes`, `DISABLE_EMBEDDED_REDIS=yes` |
| `401 Unauthorized` pulling the image | GHCR package private | Make the package (not the repo) public |
| `Railpack could not determine how to build the app` | Wrong build type; cannot be changed | Recreate the app with Dockerfile |
| Container restarts repeatedly on first boot | Migrations in progress | Expected; they resume and finish |
| Killed / exit 137 | OOM on the 4 GB plan | `BASEROW_RUN_MINIMAL=yes`, `BASEROW_AMOUNT_OF_WORKERS=1`, `SYNC_TEMPLATES_ON_STARTUP=false` |
| UI loads, grid empty, websockets fail | `BASEROW_PUBLIC_URL` does not match the browser URL | Correct it and Reload |
| Uploaded files vanish after a deploy | No S3 configured | Set the `AWS_*` variables |
| Everyone logged out after a deploy | `SECRET_KEY` / `BASEROW_JWT_SIGNING_KEY` being regenerated | Set both explicitly |

---

## Open items

1. **Login rate limiting is gone.** It was implemented as Traefik middleware in
   `docker-compose.yml` (`docs/PRODUCTION_HARDENING.md` §1.5) — 5 req/s per IP on
   `/api/user/token-auth/` and the reset-password endpoints. CranL never reads
   that file, so credential stuffing is currently limited only by network speed.
   Baserow's own throttle cannot substitute: it limits concurrency per user, not
   attempts per IP. Check whether CranL's CDN tab offers rate limiting or a WAF.
2. **Public signup.** Anyone who finds the URL can register. Disable it in the
   admin panel once the first staff account exists
   (`docs/PRODUCTION_HARDENING.md` §2.1, its highest-priority item).
3. **S3 credentials** — blocked on the CranL token quota bug.
4. **`jadawl.site`** — DNS and SSL pending.
5. **`BASEROW_ENABLE_SECURE_PROXY_SSL_HEADER`** — not set.
6. **`PORT=3000` is fragile.** It is a manual env var defending against a
   platform-injected one. Making the image immune would mean forcing `PORT` in
   the frontend's supervisor wrapper in `Azizahmed/Jadawel` and republishing.

## Facts worth not re-deriving

- The first account created through the **signup form** becomes staff. Do not
  use `createsuperuser` for it: `show_admin_signup_page` is only cleared by the
  signup API, so a CLI-made account leaves it set and `/login` then redirects to
  `/signup` permanently, with no way in through the UI.
- pgvector is optional — `is_pgvector_enabled()` in
  `backend/src/baserow/core/pgvector.py` feature-detects it, and its absence
  just disables embedding fields.
- Supabase would work as the database (it is Postgres) but adds nothing over
  `jadawel-postgres`, and its PostgREST auto-exposes the `public` schema, where
  Baserow creates every user table without RLS. Convex cannot host this app at
  all — Baserow issues live DDL against Postgres and has no SQL-free mode.
- CI and Dependabot are deliberately disabled in this repository; it re-tests
  nothing and merges nothing.
- Image published 2026-08-02 by run 30758451992, digest
  `sha256:9bd2a24b2bf1a7ba98d7010481cb91c1698acde367095c5f2a0ad54a0bdb6238`.
