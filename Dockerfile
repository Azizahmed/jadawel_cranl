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

# Published 2026-08-15 by publish-image.yml from tag v2.7.2 @ 2744ce368, digest
# sha256:a97d0666d2709e3d3baef6f9f3e018373d82cae1bdea0f49ed51f3510e5dfe15
#
# **One migration**, arabase.0005_backuprun_backupschedule. It creates the two
# tables behind the Backup admin section and touches nothing that exists, so it
# rolls forward — and back — without altering existing data.
#
# 2.7.2 adds the Backup admin section (Admin -> Backup): health, an
# hourly/daily/weekly schedule stored in the database rather than the
# environment, run history including failures, and a restore that will not
# write over the live database.
#
# It also fixes the Arabic date locale. `ar` was never imported into moment, so
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
# does, and it is the 2.7.2 build described above.
ARG JADAWEL_IMAGE=ghcr.io/azizahmed/jadawel_cranl@sha256:a97d0666d2709e3d3baef6f9f3e018373d82cae1bdea0f49ed51f3510e5dfe15

# hadolint ignore=DL3006
FROM ${JADAWEL_IMAGE}

# Inherited from the base image and repeated here only so the deployment target
# is readable without chasing the base: ENTRYPOINT ["/jadawel.sh"], CMD ["start"].
EXPOSE 80
