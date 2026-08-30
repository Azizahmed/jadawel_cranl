# Issue tracker: GitHub

Issues and specs for this repository live as GitHub issues in
`Azizahmed/jadawel_cranl`. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a
  heredoc for multiline bodies.
- **Read an issue**: `gh issue view <number> --comments`, including labels.
- **List issues**: `gh issue list --state open --json
  number,title,body,labels,comments`, with suitable label and state filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`.
- **Apply or remove labels**: `gh issue edit <number> --add-label "..."` or
  `--remove-label "..."`.
- **Close an issue**: `gh issue close <number> --comment "..."`.

Infer the repository from `git remote -v`; `gh` does this automatically when run
inside this clone.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Skill operations

When a skill says to publish to the issue tracker, create a GitHub issue. When a
skill says to fetch a relevant ticket, use `gh issue view <number> --comments`.

Wayfinder maps and tickets use GitHub issues, sub-issues where available, native
dependencies where available, assignees as claims, and the `wayfinder:*` label
family. If GitHub sub-issues or dependencies are unavailable, use a map task list
and explicit `Part of` or `Blocked by` relationships in issue bodies.
