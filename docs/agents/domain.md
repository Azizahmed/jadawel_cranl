# Domain Docs

This repository uses a single-context domain-documentation layout.

## Before exploring

- Read the root `CONTEXT.md` when it exists.
- Read ADRs under `docs/adr/` that affect the area being changed.
- If an expected domain document does not exist, proceed silently.

## Vocabulary

Use the canonical terms defined in `CONTEXT.md` in issue titles, specifications,
implementation plans, hypotheses, and test names. Avoid synonyms the glossary
explicitly rejects.

If a needed concept is absent, reconsider whether it is domain-specific. Use the
domain-modeling workflow to add a genuinely missing term.

## ADR conflicts

If proposed work contradicts an existing ADR, surface the conflict explicitly rather
than silently overriding the decision.
