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

# Published 2026-08-03 by run 30854107839, digest
# sha256:357058d24b82dadc60c072ba5530016b7274c5a4dd9939a6082b287d6e2d2bb7
# Adds the records list, progress and upcoming dates dashboard widgets on top of
# the charts in 2.3.0. Carries migration arabase 0002, which is additive —
# CreateModel only, no data touched.
ARG JADAWEL_IMAGE=ghcr.io/azizahmed/jadawel_cranl:2.4.0

# hadolint ignore=DL3006
FROM ${JADAWEL_IMAGE}

# Inherited from the base image and repeated here only so the deployment target
# is readable without chasing the base: ENTRYPOINT ["/baserow.sh"], CMD ["start"].
EXPOSE 80
