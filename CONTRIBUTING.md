# Contributing

This is a private repository. Contributions come from the maintainer and from people
who have been explicitly granted access; there is no public contribution process and no
public issue tracker.

If you have access and want to make a change, please raise it as an issue first so the
approach can be agreed before any code is written.

## Workflow

1. Open an issue describing the change (bug, feature or refactor), or pick up an
   existing one.
2. Agree the approach on the issue before starting.
3. Branch from `develop`.
4. Make the change, keeping the pull request focused on a single concern.
5. Make sure the relevant lint and test commands pass locally.
6. Open a pull request that links the issue, summarises the change, notes any schema or
   environment-variable changes, and attaches screenshots for UI work.
7. A maintainer reviews and merges. Squash-merge and delete-source-branch are the
   defaults.

## Quality standards

* Backend changes must come with unit tests (`pytest` / `pytest-django`).
* Component and store changes must come with targeted frontend tests (`vitest`).
* Python is formatted and linted with Ruff (88-character lines, 4-space indent);
  docstrings use reStructuredText style.
* Frontend code passes ESLint, Stylelint and Prettier. SCSS follows the BEM naming
  already used in `web-frontend/modules`.
* Vue code uses Vue 3 semantics. Files containing JSX must use a `.jsx`/`.tsx`
  extension.
* Any user-facing string must be added to the locale files, with Arabic (`ar`) treated
  as the primary locale, not an afterthought. Follow the terminology in
  `docs/GLOSSARY_AR.md`.
* New layout or styling must work in RTL. Prefer CSS logical properties over
  `left`/`right`. See `docs/RTL_REVIEW.md`.
* Document anything that is not self-evident, and anything a plugin can rely on.
* CI (`.github/workflows/jadawel-ci.yml`) must be green.
* Aim for the **rule of 10s**: a pull request should touch no more than about 10 code
  files with more than 10 changed lines each (tests, CSS, migrations, translations and
  configuration do not count).

See `AGENTS.md` for the full repository guidelines and the command reference.

## Licence of contributions

Contributions to the core are made under the same [MIT License](http://choosealicense.com/licenses/mit/)
that covers it. Code under `premium/` and `enterprise/` remains subject to its own
licence terms.

## Bug reports

Report bugs on the repository's issue tracker. A good report has:

* A short summary and background.
* Exact steps to reproduce — be specific, and include sample data or code if you can.
* What you expected to happen.
* What actually happened.
* Notes: why you think it might be happening, and anything you tried that did not work.
* The locale and text direction you were using, if the bug is visual — RTL-only bugs are
  easy to miss otherwise.

## Vulnerabilities

Do not open an issue for a security vulnerability. Report it privately as described in
`SECURITY.md`.
