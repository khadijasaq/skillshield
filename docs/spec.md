# Specification: Agentic Skill Security & Conformance Layer

Status: Draft — first milestone (generic integration and conformance foundation)
Schema version: 1.0

This document is the source of truth for **what** the system should do. It
does not describe implementation steps, task breakdowns, or timelines — that
belongs in `plan.md`, which does not yet exist.

---

## 1. Project

**Name:** Agentic Skill Security & Conformance Layer

**Purpose:** Build a product-independent security and conformance layer for
Agentic Skills that integrates with different host products through
product-specific adapters.

**Fundamental architecture:**

```text
Host Product
      ↓
Product Adapter
      ↓
Canonical Models
      ↓
Conformance Core
      ↓
Standardized Decision
      ↓
Product Enforcement
```

The core must remain product-independent at every layer of this flow.

---

## 2. Architectural principles

1. `core/` is completely product-independent.
2. Product-specific logic belongs in `adapters/`.
3. Adapters translate native product information/events into canonical
   representations.
4. The conformance core operates only on canonical representations.
5. Declaration, observation, evaluation, decision, and enforcement are
   separate concerns.
6. Capabilities are represented using a normalized vocabulary.
7. Security/conformance evidence is standardized.
8. Lifecycle events use a common representation.
9. Decisions use a standardized format.
10. The architecture is extensible without unnecessary abstraction or
    over-engineering.

The core must never contain product-specific branches, for example:

```python
if product == "OpenClaw":
if product == "Dify":
if product == "reference_app":
```

This specification does not design around any single product.

---

## 3. Current implementation scope

The first milestone is the **generic integration and conformance
foundation**.

### In scope

- Skill registration
- Skill declaration
- Canonical Skill model
- Canonical Capability model
- Canonical Security Event model
- Evidence model
- Decision model
- Adapter contract
- Conformance engine
- Basic conformance rules
- Standardized decisions
- Enforcement boundary
- Reference application integration

### Explicitly out of scope for this milestone

- Multiple production adapters
- Advanced static analysis
- Advanced runtime monitoring
- LLM-based analysis
- Large-scale benchmarking
- Complex policy language
- Frontend/dashboard
- Advanced reporting
- Performance optimization

---

## 4. Integration architecture

```text
                         HOST PRODUCT
                              │
                              ▼
                     PRODUCT ADAPTER
                              │
                              ▼
                     CANONICAL MODELS
                              │
                              ▼
                    CONFORMANCE CORE
                              │
                              ▼
                       STANDARD DECISION
                              │
                              ▼
                     PRODUCT ENFORCEMENT
```

**Host Product** — The environment in which the Agentic Skill exists and
executes. It owns its own native representations of skills and events.

**Product Adapter** — Translates product-native skill information and
runtime events into canonical representations. Owns all product-specific
knowledge.

**Canonical Models** — The product-independent representation used by the
conformance core (Skill, Capability, Security Event, Evidence, Decision).

**Conformance Core** — Evaluates declarations, observed behavior, and
applicable policy against the conformance rules. Knows nothing about any
specific host product.

**Decision** — The standardized output of an evaluation (`ALLOW`, `FLAG`,
`DENY`), with a reason code.

**Product Enforcement** — The host product/integration layer decides how to
act on the returned decision. Enforcement mechanics are product-specific and
live outside the core.

---

## 5. Generic integration contract

The initial integration contract is limited to three primary operations:

```text
register_skill(skill_profile)
emit_event(security_event)
evaluate(skill_id)
```

**`register_skill(skill_profile)`** — Registers a skill and its declaration
with the conformance layer. `skill_profile` is a canonical Skill model
(§7.1), already translated by the adapter.

**`emit_event(security_event)`** — Provides a canonical security/lifecycle
event (§7.3) to the conformance layer. Events accumulate as evidence for a
skill.

**`evaluate(skill_id)`** — Evaluates the currently available information for
a skill (declaration, static evidence if any, runtime evidence, policy) and
returns a standardized conformance Decision (§7.5).

No general-purpose API framework, RPC layer, or networking protocol is
defined at this stage. These three operations are the entire contract; how
they are exposed (function calls, in-process methods, etc.) is an
implementation concern for `plan.md`.

---

## 6. Skill declaration

A **declaration** is the skill's claimed operational boundary — what it
states it intends to do.

A declaration supports:

- identity
- name
- version
- purpose
- declared capabilities
- permissions/constraints
- source
- integrity
- context

> A declaration is an assertion of intended capability, not proof of actual
> behavior.

Because a declaration is a claim, not proof, the system must compare the
declaration against other evidence (static and/or runtime) rather than
trusting it unconditionally.

---

## 7. Canonical models

### 7.1 Skill

Conceptually includes:

```text
schema_version
skill identity
name
version
description/purpose
source
integrity
declaration
dependencies
context
```

The model is intentionally minimal — it covers what is needed to identify a
skill and hold its declaration, and is not expanded with speculative fields.

### 7.2 Capability

Capabilities use normalized identifiers, independent of any host product's
native naming.

Initial examples:

```text
task.read
network.egress
process.execute
filesystem.write
credential.read
```

Different host products may expose equivalent behavior under different
native names. The adapter — not the core — is responsible for normalizing
these into the common capability vocabulary. For example, the following
native representations:

```text
HTTP request
requests.get()
fetch()
network tool
```

may all normalize to:

```text
network.egress
```

This milestone does not attempt to define an exhaustive capability
taxonomy — only the small set needed to demonstrate the conformance model.

### 7.3 Security Event

A canonical event containing:

```text
schema_version
event_id
timestamp
event_type
context
actor
action
target
```

> Event provenance and supporting evidence are represented through the
> Evidence model where required.

Conceptual example:

```json
{
  "schema_version": "1.0",
  "event_id": "evt-001",
  "timestamp": "...",
  "event_type": "network.request",
  "context": {
    "product_id": "product-x",
    "session_id": "session-1",
    "execution_id": "exec-1",
    "skill_id": "task-insights"
  },
  "actor": {
    "type": "skill",
    "id": "task-insights"
  },
  "action": {
    "capability": "network.egress",
    "operation": "request"
  },
  "target": {
    "type": "external_endpoint",
    "identifier": "..."
  }
}
```

All runtime activity observed by an adapter is represented in this form
before it reaches the conformance core.

### 7.4 Evidence

Evidence is information supporting a conformance evaluation. The model
distinguishes evidence by source:

```text
declaration
static
runtime
policy
```

This milestone does not implement evidence scoring, weighting, or
probabilistic confidence mechanisms. Evidence is treated as present/absent
information grouped by source, not as a scored signal.

### 7.5 Decision

The standardized output of a conformance evaluation.

Initial decision values:

```text
ALLOW
FLAG
DENY
```

Initial reason codes:

```text
INVALID_DECLARATION
MISSING_DECLARATION
UNDECLARED_CAPABILITY
POLICY_VIOLATION
STATIC_RUNTIME_MISMATCH
INVALID_EVENT
UNKNOWN_CAPABILITY
INTEGRITY_FAILURE
```

No additional decision states are introduced unless a concrete requirement
justifies them.

---

## 8. Conformance model

Define the following conceptual sets:

```text
D = declared capabilities
S = statically inferred capabilities
R = runtime observed capabilities
P = policy-permitted capabilities
```

The main initial runtime conformance rule:

```text
R ⊆ D
```

> Every runtime-observed capability should be declared by the skill.

When a policy boundary exists:

```text
R ⊆ P
```

Combined:

```text
R ⊆ D ∩ P
```

Static evidence (`S`) is supported conceptually in the model, so that static
findings can later be compared against `D` and `R`, but **advanced static
analysis is not part of this milestone**. No component in this milestone is
required to use an LLM to infer capabilities.

---

## 9. Conformance checks

These checks belong to the **conformance core**, not to individual adapters.

### Structural conformance

- Required declaration fields exist.
- Capability identifiers are syntactically valid and belong to the supported canonical capability vocabulary.
- Canonical representations (Skill, Security Event) are structurally valid.

### Runtime capability conformance

```text
R ⊆ D
```

### Policy conformance

When a policy exists for the skill:

```text
R ⊆ P
```

### Combined conformance

```text
R ⊆ D ∩ P
```

An adapter may trigger an evaluation, but it never implements these rules
itself — it only supplies canonical inputs to the core.

---

## 10. Adapter contract

An adapter is responsible for:

1. Receiving native product information.
2. Translating native skill information into the canonical Skill model.
3. Normalizing native capabilities into the canonical capability vocabulary.
4. Translating native runtime activity into canonical Security Events.
5. Sending canonical information to the conformance core
   (`register_skill`, `emit_event`).
6. Receiving standardized decisions (`evaluate`).
7. Optionally communicating/enforcing decisions within the host product.

```text
Adapter = translation + integration
Core    = conformance evaluation
```

The adapter must never implement the central conformance rules (§8, §9) —
those rules live exclusively in the core.

---

## 11. Reference application

The existing vulnerable Agentic Skills application is the **first reference
integration**, used as:

- a reference adapter implementation
- a controlled integration environment
- a controlled testbed for conformance behavior

The core must not depend on the reference application's internal
implementation. The architecture must remain reusable for future host
products — the reference application is one adapter among potentially many,
not a special case baked into the core.

---

## 12. Lifecycle

The generic lifecycle of a skill, from the conformance layer's perspective:

```text
Skill Registration
      ↓
Declaration Validation
      ↓
Skill Load
      ↓
Skill Execution
      ↓
Runtime Events
      ↓
Conformance Evaluation
      ↓
Decision
      ↓
Product Enforcement
      ↓
Audit / Evidence
```

This lifecycle is conceptual. It does not assume any specific host
framework, execution model, or runtime — each stage maps to adapter and core
responsibilities already defined in §4, §5, and §10.

---

## 13. Enforcement boundary

**Conformance Evaluation** and **Enforcement** are explicitly separate
concerns.

The conformance core produces one of:

```text
ALLOW
FLAG
DENY
```

The host product decides how that result affects execution — blocking,
warning, logging, quarantining, or any other product-specific response. The
core has no knowledge of, and no responsibility for, how its decision is
enforced.

Future decision types such as:

```text
MODIFY
ASK
DEFER
```

may be supported later, but are not required by this milestone.

---

## 14. Evidence and declaration/behavior comparison

```text
Declaration
     │
     │ expected boundary
     ▼
Conformance Evaluation
     ▲
     │
     ├── Static Evidence
     │
     └── Runtime Evidence
```

Using the conceptual model from §8:

```text
D = declared capabilities
S = static evidence
R = runtime evidence
P = policy
```

The governing principle:

> Declaration defines the claimed boundary; static and runtime evidence
> provide observations; the conformance layer determines whether the
> observations remain consistent with the declaration and applicable policy.

This is an engineering principle applied in this system, not a claimed
research contribution.

---

## 15. Schema and versioning

Canonical representations (Skill, Security Event, Evidence, Decision) are
versioned.

Initial schema version:

```text
1.0
```

Schemas in `schemas/` must remain aligned with the corresponding models in
`core/models/`. Versioning is kept simple: a single `schema_version` field
per canonical representation. No version-negotiation protocol is defined at
this stage.

---

## 16. Extensibility

The architecture is designed to later accommodate, without requiring the
core to become product-specific:

- static analyzers (contributing to `S`)
- runtime monitors (contributing richer `R`)
- policy engines (contributing richer `P`)
- additional product adapters
- additional capability types
- richer evidence
- additional decision types (e.g. `MODIFY`, `ASK`, `DEFER`)
- a frontend/dashboard

These are extension points for future milestones, not requirements of the
current one. Each extension is expected to plug in through an adapter, a new
evidence source, or an addition to the canonical vocabulary — never through
a product-specific branch inside `core/`.

---

## 17. Non-goals

This specification does not currently define:

- a complete malicious-skill detector
- a complete static-analysis framework
- an LLM security analyzer
- a universal policy language
- a frontend
- a dashboard
- adapters for every agentic platform
- large-scale benchmark evaluation
- production enforcement mechanisms for every host product

---

## 18. Acceptance criteria

The first milestone should eventually satisfy:

1. A host product can register a skill through an adapter.
2. The skill is represented using the canonical Skill model.
3. Native capabilities can be normalized into canonical capabilities.
4. Runtime activity can be represented as canonical Security Events.
5. The conformance core can compare observed capabilities with declared
   capabilities.
6. The conformance core can produce standardized ALLOW/FLAG/DENY decisions.
7. The reference application can demonstrate a conformant skill.
8. The reference application can demonstrate an undeclared capability.
9. Product-specific logic remains outside `core/`.
10. Canonical schemas remain aligned with the corresponding models.

---

## 19. Relationship to repository structure

This specification maps directly onto the existing repository structure and
introduces no new folders:

```text
src/
└── agentic_conformance/
    ├── core/
    │   ├── models/
    │   ├── conformance/
    │   └── interfaces/
    │
    └── adapters/
        └── reference_app/

schemas/
tests/
docs/
examples/
```

- `core/models/` — canonical Skill, Capability, Security Event, Evidence,
  Decision models (§7).
- `core/conformance/` — the conformance engine and checks (§8, §9).
- `core/interfaces/` — the adapter contract (§10) and the
  `register_skill` / `emit_event` / `evaluate` integration contract (§5).
- `adapters/reference_app/` — the reference application adapter (§11).
- `schemas/` — versioned schemas aligned with `core/models/` (§15).
- `tests/`, `docs/`, `examples/` — as already established in the repository.
