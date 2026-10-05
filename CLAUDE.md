# Project Instructions

This repository implements the **Agentic Skill Security & Conformance Layer**: a
product-independent conformance system for Agentic Skills.

## Architectural rules

- `core/` is product-independent. It must never contain product-specific
  branches, conditionals, or assumptions about a particular host product.
- Product-specific logic belongs in `adapters/` (e.g. `adapters/reference_app/`).
- Adapters are responsible for normalizing native product data/events into
  canonical models before anything reaches `core/`.
- Conformance logic in `core/` operates only on canonical representations,
  never on raw/native product data.
- Keep `schemas/` compatible with the models defined in `core/models/`.

## Working practices

- Add tests for new functionality (`tests/unit/`, `tests/integration/`).
- Prefer small, focused modules over large multi-purpose ones.
- Do not introduce unnecessary architectural layers.
- Do not reorganize the repository without a clear architectural reason.
- Read `docs/spec.md` and `docs/plan.md` before implementing any new
  feature.
