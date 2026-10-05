# Agentic Skill Security & Conformance Layer

A product-independent security and conformance layer for Agentic Skills. It
assesses whether a skill's declared and observed behavior conforms to
expected safety and capability boundaries, and produces a standardized
decision that any host product can enforce, without embedding
product-specific logic into the core conformance logic itself.

## Architectural idea

```text
Host Product
  -> Product Adapter
  -> Canonical Models
  -> Conformance Core
  -> Standardized Decision
  -> Product Enforcement
```

Adapters translate a host product's native data and events into canonical,
product-independent models. The conformance core reasons only over these
canonical models and emits a standardized decision. Enforcement of that
decision is left to the host product.

## Current scope

This repository currently contains only the generic integration and
conformance **foundation**: project structure, packaging, and tooling. The
canonical models, adapter interface, and conformance engine are not yet
implemented and will be added once a `spec.md` and `plan.md` are introduced.
