# Deploying Jadawel to CranL

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
       -> ghcr.io/azizahmed/jadawel:<tag>
            -> root Dockerfile: FROM that image
                 -> CranL builds a trivial one-line image and runs it on :80
                      -> managed Postgres + managed Redis + S3
```

The `prod-lite` variant is used deliberately. The full all-in-one image embeds
Postgres and Redis under `/baserow/data`, which on a host with no persistent
volume means the database is destroyed on every redeploy.

**Pushing code does not change what is deployed.** Publish first, then redeploy.

## 1. Publish an image

Actions → **Publish all-in-one image** → Run workflow, on
`codex/hostinger-coolify-deploy`, with a tag such as `2.2.2`. Expect 30–60
minutes cold. It pushes `ghcr.io/azizahmed/jadawel:<tag>` and `:latest`.

Then decide the package's visibility, at
`github.com/users/Azizahmed/packages/container/jadawel/settings`:

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
to `/baserow/data/media` and vanish on the next deploy.

## 3. Create the app

New app, and because these cannot be changed afterwards, get them right first
time:

| Setting | Value |
|---|---|
| Repository | `Azizahmed/Jadawel` |
| Branch | `codex/hostinger-coolify-deploy` |
| Build Type | **Dockerfile** |
| Port | **80** — the image serves through its bundled Caddy, not 3000 |

The Dockerfile must be named `Dockerfile` and sit at the repository root, which
is where this repo now keeps it, regardless of what the wizard's path field
suggests.

## 4. Environment variables

```bash
for n in SECRET_KEY BASEROW_JWT_SIGNING_KEY; do echo "$n=$(tr -dc 'a-z0-9' </dev/urandom | head -c50)"; done
```

| Variable | Value | Why |
|---|---|---|
| `SECRET_KEY` | *generated* | Must be set explicitly. `baserow.sh` otherwise generates one into `/baserow/data/.secret`, which is ephemeral here — so every redeploy would invalidate all sessions. |
| `BASEROW_JWT_SIGNING_KEY` | *generated* | Same, via `.jwt_signing_key`. Regenerating it logs everyone out. |
| `BASEROW_PUBLIC_URL` | `https://jadawl.site` | Must exactly match the browser URL, scheme included, no trailing slash. |
| `DATABASE_URL` | *from managed Postgres* | Or the `DATABASE_HOST` / `PORT` / `NAME` / `USER` / `PASSWORD` set. |
| `REDIS_URL` | *from managed Redis* | Or the `REDIS_HOST` / `PORT` / `PASSWORD` set. |
| `DISABLE_EMBEDDED_PSQL` | `yes` | **Required on the lite image.** Without it the startup script runs `chown -R postgres:postgres` for a user that only exists in the full image, and a missing database silently becomes a confusing failure instead of a loud one. |
| `DISABLE_EMBEDDED_REDIS` | `yes` | Same, for `chown -R redis:redis`. |
| `AWS_ACCESS_KEY_ID` | | Uploads are lost on redeploy without S3. |
| `AWS_SECRET_ACCESS_KEY` | | |
| `AWS_STORAGE_BUCKET_NAME` | | |
| `AWS_S3_REGION_NAME` | | |
| `AWS_S3_ENDPOINT_URL` | | Only for non-AWS S3. |

Leave `BASEROW_CADDY_ADDRESSES` unset. Its `:80` default is correct — CranL owns
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
`BASEROW_JWT_SIGNING_KEY` is unset and being regenerated. See §4.

**UI loads but the grid stays empty and websockets fail** —
`BASEROW_PUBLIC_URL` does not exactly match the browser URL.

**Uploaded files disappear after a deploy** — no S3 configured. See §4.
