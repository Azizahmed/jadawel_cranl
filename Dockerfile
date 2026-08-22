# Deployment entry point for PaaS hosts that only support a root Dockerfile
# built from the repository (CranL, and others with the same constraint).
#
# It deliberately does NOT build the monorepo. The Nuxt production build peaks
# above 4 GB and is OOM-killed on a small app plan, so the image is built by
# .github/workflows/publish-image.yml on a GitHub runner and merely pulled here.
#
# Consequences of that split, in order of how likely they are to bite:
#
#   1. Pushing code does not change what is deployed. Run the publish workflow
#      first, then redeploy. A tag pinned below makes that explicit; `latest`
#      quietly deploys whatever was published last.
#   2. This is the `prod-lite` variant: no embedded Postgres or Redis. The host
#      must provide both, plus S3 for uploads — hosts without a persistent
#      volume lose container-local data on every redeploy.
#   3. The image serves on port 80 behind its bundled Caddy, not 3000.
#
# See docs/DEPLOY_CRANL.md for the full deployment procedure.

# Published 2026-08-22 by publish-image.yml from release 2.9.0 @ 0848521d7,
# digest sha256:19ed2e7cce2e6f22709ad28b94ba32fac8b6bc5524eb04e89ca920c725f6068f.
#
# 2.9.0 adds matched Arabic and English project-management templates, plus
# Arabic and English Saudi budget-consolidation templates. It also enforces
# the Gregorian Arabic month names familiar in Saudi Arabia and clears Vite's
# generated dependency cache when correcting the datepicker locale.
#
# Previously published 2026-08-17 by publish-image.yml from tag v2.8.1 @
# c3639cd64, digest
# sha256:1047c4c1658496d8b94be17ec1eb7e00a6d5f2beff0bad4c44b8afad44bbba6e
#
# **No migration.** 2.8.1 changes one package in the image and one path lookup
# in the backup code.
#
# 2.8.1 makes backups possible at all. The image installed postgresql-client
# from POSTGRES_VERSION, the same variable that selects the *embedded* Postgres
# server, so it shipped pg_dump 15 — and this deployment backs up CranL's
# managed Postgres 16, which pg_dump refuses to touch because it will not dump
# a server newer than itself. Every backup failed on the version check.
#
# POSTGRES_CLIENT_VERSION=18 is now separate from POSTGRES_VERSION=15. Raising
# the latter would have fixed the dump and broken the image for anyone using
# the embedded database: a Postgres 16 server will not start on a data
# directory that 15 initialised. Newer is free for the client, which reads
# older servers and refuses only newer ones.
#
# Installing a newer client is not sufficient on its own. /usr/bin/pg_dump is
# Debian's pg_wrapper, which picks a major version from the default *cluster*
# — the embedded one — rather than from the server being contacted, and the
# prod stage still carries client 15 as a dependency of postgresql-15. So
# arabase.backup.runner.client_binary() reads /usr/lib/postgresql/*/bin/ and
# takes the highest major itself. pg_restore resolves the same way: a dump
# written by a newer pg_dump is unreadable by an older pg_restore.
#
# Carried over from 2.8.0, the Page view, a fourth view type beside Grid,
# Gallery and Form.
# A Page renders an HTML document written by an AI over MCP, fed with the
# view's live rows, and shares on a public link with the optional password a
# form already had. A new Page opens on a setup panel carrying the workspace's
# MCP address, the page's own number and a prompt to paste, because a page is
# authored from outside the app and an empty one is otherwise a dead end.
#
# The document is untrusted, so it never renders on the app's origin: it goes
# in an iframe sandboxed to allow-scripts *without* allow-same-origin, under a
# server-computed CSP whose connect-src is 'none'. The page is handed real
# rows, so what matters is that it cannot send them anywhere. See
# docs/PAGE_VIEW.md.
#
# Carried over from 2.7.2, the Backup admin section (Admin -> Backup): health,
# an hourly/daily/weekly schedule stored in the database rather than the
# environment, run history including failures, and a restore that will not
# write over the live database.
#
# 2.7.2 also fixed the Arabic date locale. `ar` was never imported into moment, so
# every date in the product rendered in Ukrainian — `serp` for August — because
# `uk` was the last import and moment answers a missing locale by keeping the
# one it is on. Digits stay Western, as AGENTS.md requires.
#
# Carried over from 2.7.0, the two that matter most in production:
#
#   - A public dashboard link returned every column of its backing table, not
#     just the ones its widgets display. Anyone holding a share URL could read
#     the rest of the row. Existing links keep working and are now scoped.
#   - Backup retention listed by prefix and deleted anything past the window,
#     so an empty JADAWEL_BACKUP_S3_PREFIX meant the whole bucket. The config
#     now refuses an empty prefix, which means a backup job configured that way
#     will fail loudly on this image instead of running.
#
# Also: rate limits are countable per client (they keyed on a caller-controlled
# header before, so the contact form was an open mail relay), disabled MCP tools
# can no longer be invoked by name, share tokens expire, chart and agenda
# widgets read date columns correctly, and user files are archived alongside the
# database dump.
#
# Set JADAWEL_* in the dashboard before deploying. The BASEROW_* shims still
# accept the old names, but JADAWEL_JWT_SIGNING_KEY must carry the same value
# as BASEROW_JWT_SIGNING_KEY or every issued session is invalidated.
#
# JADAWEL_ENABLE_SECURE_PROXY_SSL_HEADER=yes is worth setting here: it is what
# turns on Secure cookies and HSTS, and the all-in-one image defaults it empty.
#
# Pinned by digest, not by tag. The publish workflow pushes `:latest` alongside
# the version tag, so a tag pin does not identify a fixed image. The digest
# does, and it is the 2.8.1 build described above.
#
# Changing only this line has not been enough to swap the container: CranL
# reported the 2.7.2 deploy `done` while the old workers kept running, because
# a digest-only edit to a `FROM` does not invalidate its build cache. Follow
# the deploy with a reload, and verify behaviour rather than trusting `done`.
ARG JADAWEL_IMAGE=ghcr.io/azizahmed/jadawel_cranl@sha256:19ed2e7cce2e6f22709ad28b94ba32fac8b6bc5524eb04e89ca920c725f6068f

# hadolint ignore=DL3006
FROM ${JADAWEL_IMAGE}

# Inherited from the base image and repeated here only so the deployment target
# is readable without chasing the base: ENTRYPOINT ["/jadawel.sh"], CMD ["start"].
EXPOSE 80
