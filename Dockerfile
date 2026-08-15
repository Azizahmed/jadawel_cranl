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

# Published 2026-08-09 by publish-image.yml from main @ d5698cc, digest
# sha256:4097ccfac0690ccc9d49bdddb85ea05bd9d1a5a4cfa6eac3ec7298728822349c
#
# Carries one migration, arabase.0004_dashboard_share, which creates the
# DashboardShare table behind the new public dashboard links. Nothing in it
# touches an existing table, so it is safe to roll forward on a live database.
#
# Also in this image: workspace-level generative AI key settings are gone (the
# API route 404s and the workspace Settings menu entry no longer renders), and
# dashboard widgets can be dragged and resized on the grid board.
#
# 2.6.1 over 2.6.0: a password-protected dashboard link waved through anyone
# signed in to the owning workspace, so the owner could never verify their own
# password. The password now applies to every request on the public URL.
#
# Set JADAWEL_* in the dashboard before deploying. The BASEROW_* shims still
# accept the old names, but JADAWEL_JWT_SIGNING_KEY must carry the same value
# as BASEROW_JWT_SIGNING_KEY or every issued session is invalidated.
# Pinned by digest, not by tag. The publish workflow pushes `:latest` alongside
# the version tag, and re-running it with a tag that already exists silently
# repoints that tag — so a tag pin does not identify a fixed image. The digest
# does, and it is the same 2.6.1 build described above.
ARG JADAWEL_IMAGE=ghcr.io/azizahmed/jadawel_cranl@sha256:4097ccfac0690ccc9d49bdddb85ea05bd9d1a5a4cfa6eac3ec7298728822349c

# hadolint ignore=DL3006
FROM ${JADAWEL_IMAGE}

# Inherited from the base image and repeated here only so the deployment target
# is readable without chasing the base: ENTRYPOINT ["/jadawel.sh"], CMD ["start"].
EXPOSE 80
