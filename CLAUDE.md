@AGENTS.md

## Fork identity

This repo is **Jadawel** — an Arabic-first, RTL fork of Baserow. AGENTS.md above
is unmodified upstream Baserow guidance: accurate for build/test/lint, but silent
on deploy and fork scope, both covered below.

## Remotes and branches

Two remotes point to two different repos — the wrong one silently diverges work
with no path back:

- `origin` (`Azizahmed/Jadawel`) — the real dev repo. All feature commits belong
  here.
- `cranl` (`Azizahmed/jadawel_cranl`) — a deploy-only mirror carrying an extra
  root `Dockerfile` and publish workflow. Never commit feature work directly to
  it; bring changes over by merging `origin`'s `codex/hostinger-coolify-deploy`
  into its `main` and publishing a new image.

Production branch is `codex/hostinger-coolify-deploy`.

## Deploying

Two separate, non-interchangeable deploy targets:

- **Coolify** (production, `jadawel.azoz.cloud`) — auto-deploys on push to
  `codex/hostinger-coolify-deploy`. See `docs/DEPLOYMENT.md`.
- **CranL** — can't build this monorepo directly (no Compose pack, Railpack
  finds no manifest, 4 GB RAM ceiling); GitHub Actions builds the image and
  CranL only pulls it. See `docs/DEPLOY_CRANL.md`.

## Fork-specific docs

`docs/` holds plans and audits specific to this fork (RTL/i18n completion,
dashboard widgets, Arabic glossary, production hardening, audits) — check there
before re-deriving scope or history that's already written down.

`website/index.html` and `website/landing.html` are marketing pages, not part
of the deployed app image; they need separate hosting to go live.

## Skills

`.claude/skills` is a symlink to `.agents/skills`, the canonical location for project skills. Both paths resolve to the same directory.
