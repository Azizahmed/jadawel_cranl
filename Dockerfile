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

# Published 2026-08-09 by publish-image.yml from main @ eeccadf, digest
# sha256:fffdf230bbbefff75ff352ad6f8927b97ff9fcf2f5c182a4da110746f16f8900
#
# Carries one migration, arabase.0004_dashboard_share, which creates the
# DashboardShare table behind the new public dashboard links. Nothing in it
# touches an existing table, so it is safe to roll forward on a live database.
#
# Also in this image: workspace-level generative AI key settings are gone (the
# API route 404s and the workspace Settings menu entry no longer renders), and
# dashboard widgets can be dragged and resized on the grid board.
#
# Set JADAWEL_* in the dashboard before deploying. The BASEROW_* shims still
# accept the old names, but JADAWEL_JWT_SIGNING_KEY must carry the same value
# as BASEROW_JWT_SIGNING_KEY or every issued session is invalidated.
ARG JADAWEL_IMAGE=ghcr.io/azizahmed/jadawel_cranl:2.6.0

# hadolint ignore=DL3006
FROM ${JADAWEL_IMAGE}

# Inherited from the base image and repeated here only so the deployment target
# is readable without chasing the base: ENTRYPOINT ["/jadawel.sh"], CMD ["start"].
EXPOSE 80
