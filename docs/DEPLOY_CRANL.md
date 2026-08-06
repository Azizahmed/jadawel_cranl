# Deploying Jadawel to CranL

## Which repository is this?

`Azizahmed/jadawel_cranl` — a deployment copy, branched from
`Azizahmed/Jadawel` at `codex/hostinger-coolify-deploy` and carrying the root
`Dockerfile` and `publish-image.yml` on top of it. It exists so that CranL work
cannot disturb the running Coolify deployment, which continues to be served from
the original repository.

Code changes belong in `Azizahmed/Jadawel`. To bring them here, merge that
branch into this repository's `main` and publish a new image. Committing feature
work directly here diverges the two trees with no path back.

CranL is not Coolify, and none of [DEPLOYMENT.md](DEPLOYMENT.md) applies here.
The differences that shape everything below:

- **No Docker Compose build pack.** The new-app wizard offers Railpack
  (auto-detect) and Dockerfile, nothing else. `docker-compose.yml` is unusable.
- **Railpack cannot build this repo.** It looks for an application manifest at
  the root; this is a monorepo whose manifests live in `backend/` and
  `web-frontend/`. Detection fails before any build step, with
  `Railpack could not determine how to build the app`.
- **Build type and branch are set only at creation.** The Settings tab exposes
  domain, port and delete; there is no update-application endpoint in the API.
  Changing either means creating a new app and deleting the old one.
- **4 GB RAM per app on Pro.** The Nuxt production build peaks above that, so
  building this repo on CranL fails regardless of configuration.
- **CranL terminates TLS and routes to the container itself.** No Traefik
  labels, no external proxy network, no certresolver — all of which the Coolify
  compose file exists to configure.
- **No persistent volume.** Anything written inside the container is lost on
  redeploy.

## The shape of the deployment

Because the app cannot be built on CranL, the build moves to GitHub Actions
(16 GB runners) and CranL only pulls the result:

```
push to branch
  -> GitHub Actions (publish-image.yml): backend + web-frontend -> all-in-one-lite
       -> ghcr.io/azizahmed/jadawel_cranl:<tag>
            -> root Dockerfile: FROM that image
                 -> CranL builds a trivial one-line image and runs it on :80
                      -> managed Postgres + managed Redis + S3
```

The `prod-lite` variant is used deliberately. The full all-in-one image embeds
Postgres and Redis under `/jadawel/data`, which on a host with no persistent
volume means the database is destroyed on every redeploy.

**Pushing code does not change what is deployed.** Publish first, then redeploy.

## 1. Publish an image

Actions → **Publish all-in-one image** → Run workflow, on `main`, with a tag such as `2.2.2`. Expect 30–60
minutes cold. It pushes `ghcr.io/azizahmed/jadawel_cranl:<tag>` and `:latest`.

Then decide the package's visibility, at
`github.com/users/Azizahmed/packages/container/jadawel_cranl/settings`:

- **Public** — CranL pulls with no credentials. The repository stays private,
  but the built application (including the fork's frontend bundle) becomes
  publicly downloadable.
- **Private** — requires CranL to hold a GHCR pull credential. If the wizard has
  no registry-credentials field, this option does not work and the image must be
  public.

Pin the published tag in the root `Dockerfile` (`ARG JADAWEL_IMAGE=...`) and
commit. Leaving it at `latest` means a redeploy silently picks up whatever was
published most recently.

## 2. Create the managed backing services

New → Database, twice: **Postgres** and **Redis**. Note each connection string.
Both are mandatory — `prod-lite` contains no database or cache of its own, and
the container filesystem does not survive a redeploy.

Uploaded files need S3 for the same reason; without `AWS_*` set they are written
to `/jadawel/data/media` and vanish on the next deploy.

## 3. Create the app

New app, and because these cannot be changed afterwards, get them right first
time:

| Setting | Value |
|---|---|
| Repository | `Azizahmed/jadawel_cranl` |
| Branch | `main` |
| Build Type | **Dockerfile** |
| Port | **80** — the image serves through its bundled Caddy, not 3000 |

The Dockerfile must be named `Dockerfile` and sit at the repository root, which
is where this repo now keeps it, regardless of what the wizard's path field
suggests.

## 4. Environment variables

```bash
for n in SECRET_KEY JADAWEL_JWT_SIGNING_KEY; do echo "$n=$(tr -dc 'a-z0-9' </dev/urandom | head -c50)"; done
```

The list below was written before the first deploy and proved incomplete. Five
more variables turned out to be mandatory — `PORT=3000` above all, without which
the container crash-loops. See [cranl_fix.md](../cranl_fix.md) for the full
working set and why each is needed.

| Variable | Value | Why |
|---|---|---|
| `PORT` | `3000` | CranL injects `PORT=80` to match the routing port, and Nitro obeys it — so the web-frontend tries to bind Caddy's socket and dies with `EADDRINUSE :::80`. `NITRO_PORT` does not override it. |
| `DISABLE_VOLUME_CHECK` | `yes` | Boot otherwise stops at the unmounted-data-folder warning. Safe: Postgres and Redis are external. |
| `JADAWEL_RUN_MINIMAL` | `yes` | Folds the export worker into the main worker on a 4 GB plan. |
| `JADAWEL_AMOUNT_OF_WORKERS` | `1` | Required for the above to take effect. |
| `SYNC_TEMPLATES_ON_STARTUP` | `false` | Drops a step that can take 30 minutes from every boot. |
| `JADAWEL_TRIGGER_SYNC_TEMPLATES_AFTER_MIGRATION` | `true` | Must be set alongside the row above, which it silently defaults to (`backend/docker/docker-entrypoint.sh:30`). Without it the instance has **no templates at all**; with it they import in celery after boot instead of blocking it. |
| `SECRET_KEY` | *generated* | Must be set explicitly. `jadawel.sh` otherwise generates one into `/jadawel/data/.secret`, which is ephemeral here — so every redeploy would invalidate all sessions. |
| `JADAWEL_JWT_SIGNING_KEY` | *generated* | Same, via `.jwt_signing_key`. Regenerating it logs everyone out. |
| `JADAWEL_PUBLIC_URL` | `https://jadawl.site` | Must exactly match the browser URL, scheme included, no trailing slash. |
| `DATABASE_URL` | *from managed Postgres* | Or the `DATABASE_HOST` / `PORT` / `NAME` / `USER` / `PASSWORD` set. |
| `REDIS_URL` | *from managed Redis* | Or the `REDIS_HOST` / `PORT` / `PASSWORD` set. |
| `DISABLE_EMBEDDED_PSQL` | `yes` | **Required on the lite image.** Without it the startup script runs `chown -R postgres:postgres` for a user that only exists in the full image, and a missing database silently becomes a confusing failure instead of a loud one. |
| `DISABLE_EMBEDDED_REDIS` | `yes` | Same, for `chown -R redis:redis`. |
| `AWS_ACCESS_KEY_ID` | | Uploads are lost on redeploy without S3. |
| `AWS_SECRET_ACCESS_KEY` | | |
| `AWS_STORAGE_BUCKET_NAME` | | |
| `AWS_S3_REGION_NAME` | | |
| `AWS_S3_ENDPOINT_URL` | | Only for non-AWS S3. |

Leave `JADAWEL_CADDY_ADDRESSES` unset. Its `:80` default is correct — CranL owns
TLS, and pointing Caddy at an `https://` address makes it try to obtain its own
certificate on a port it cannot reach, which hangs the deploy.

Optional SMTP (password resets and invitations do not work without it) — same
variables as [DEPLOYMENT.md §3](DEPLOYMENT.md).

## 5. Deploy and create the first account

Migrations run automatically on startup. Watch the log until the backend reports
it is listening, then open the domain and **sign up through the web form**. The
first account created becomes staff.

Do not use `createsuperuser` for it: the `show_admin_signup_page` flag is only
cleared by the signup API, so a CLI-made account leaves it set and `/login`
redirects to `/signup` permanently, with no way in through the UI.

## Updating

1. Push code.
2. Run the publish workflow to build a new image tag.
3. Bump `ARG JADAWEL_IMAGE` in the root `Dockerfile` and commit.
4. Redeploy on CranL.

Skipping step 2 or 3 redeploys the same image.

## Troubleshooting

**`Railpack could not determine how to build the app`** — the app was created
with the Railpack build type. It cannot be changed; recreate the app with
Dockerfile.

**Build OOMs or is killed with no error** — something is building the repo from
source rather than pulling the published image. Check that the root `Dockerfile`
is the one being used and that `ARG JADAWEL_IMAGE` points at a tag that exists.

**`denied` / `unauthorized` pulling from ghcr.io** — the GHCR package is private
and CranL has no credential for it. See §1.

**Container starts, then exits during startup with a `chown` error** —
`DISABLE_EMBEDDED_PSQL` / `DISABLE_EMBEDDED_REDIS` are not set. See §4.

**Everyone is logged out after each deploy** — `SECRET_KEY` or
`JADAWEL_JWT_SIGNING_KEY` is unset and being regenerated. See §4.

**UI loads but the grid stays empty and websockets fail** —
`JADAWEL_PUBLIC_URL` does not exactly match the browser URL.

**The template picker is empty** — the sync never ran against this database. See
§4; it is a separate variable from `SYNC_TEMPLATES_ON_STARTUP`.

**`/api/*` returns a Nuxt 404 page instead of JSON** — the host being requested
is not named in `JADAWEL_PUBLIC_URL`, so `Caddyfile:82-131` routes backend paths
to the frontend. Add the extra host to `JADAWEL_EXTRA_PUBLIC_URLS`.

**Uploaded files disappear after a deploy** — no S3 configured. See §4.
