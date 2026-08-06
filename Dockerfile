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

# Published 2026-08-06, digest
# sha256:ccac318f493988e982574821acc8c55fb00636c1b088a4cd8a8ff2fbbc8b031e
# Built locally rather than by publish-image.yml: GitHub Actions was in a major
# outage and never acquired a runner. Same three builds the workflow runs.
#
# Completes the baserow -> jadawel rename. Carries seven migrations: the
# LocalJadawel RenameModel set, the show_jadawel_help_request field, the
# get_jadawel_table_* functions, and the sweep of the Postgres constraint,
# index and sequence names RenameModel left behind.
#
# Set JADAWEL_* in the dashboard before deploying. The BASEROW_* shims still
# accept the old names, but JADAWEL_JWT_SIGNING_KEY must carry the same value
# as BASEROW_JWT_SIGNING_KEY or every issued session is invalidated.
ARG JADAWEL_IMAGE=ghcr.io/azizahmed/jadawel_cranl:2.5.0

# hadolint ignore=DL3006
FROM ${JADAWEL_IMAGE}

# Inherited from the base image and repeated here only so the deployment target
# is readable without chasing the base: ENTRYPOINT ["/jadawel.sh"], CMD ["start"].
EXPOSE 80
