# Implementation Plan: Agentic Skill Security & Conformance Layer

This document defines **HOW** the first milestone described in `docs/spec.md` is implemented.

`docs/spec.md` remains the source of truth for **WHAT** is required. This plan defines the implementation sequence and validation process.

All implementation must remain within the scope of the specification. No phase may introduce behavior that is outside the finalized first-milestone requirements.

---

## 1. Plan Overview

The first milestone establishes a **generic integration and conformance foundation** for Agentic Skills.

The implementation follows this sequence:

1. Canonical models and schemas
2. Integration interfaces
3. Minimal conformance engine
4. Reference application adapter
5. End-to-end demonstration
6. Final testing, validation, and documentation

The architectural boundary remains:

```text
Adapter = translation + integration

Core = canonical representation + conformance evaluation
```

Product-specific logic must remain outside the core.

---

## 2. Current Starting Point

The following are already in place:

* Repository structure:

  * `src/agentic_conformance/core/models/`
  * `src/agentic_conformance/core/conformance/`
  * `src/agentic_conformance/core/interfaces/`
  * `src/agentic_conformance/adapters/reference_app/`
  * `schemas/`
  * `tests/unit/`
  * `tests/integration/`
  * `docs/`
  * `examples/`
* `pyproject.toml`
* Hatchling build configuration
* `uv` development environment
* Ruff and pytest configuration
* CI workflow
* Basic package/import test
* Finalized `docs/spec.md`
* `CLAUDE.md`

The following are not yet implemented:

* Canonical models
* Canonical JSON schemas
* Integration interfaces
* Conformance engine
* Reference application adapter
* End-to-end demonstration

---

# Phase 1 — Canonical Models and Schemas

## Goal

Implement the canonical representations defined in `docs/spec.md` §7 and the schema/versioning requirements in §15.

The implementation must remain minimal, product-independent, and free of speculative abstractions.

## Files

Create:

```text
src/agentic_conformance/core/models/skill.py
src/agentic_conformance/core/models/capability.py
src/agentic_conformance/core/models/security_event.py
src/agentic_conformance/core/models/evidence.py
src/agentic_conformance/core/models/decision.py
src/agentic_conformance/core/models/__init__.py

schemas/skill.schema.json
schemas/security_event.schema.json
schemas/evidence.schema.json
schemas/decision.schema.json

tests/unit/test_models.py
```

### Important schema boundary

Do **not** create `schemas/capability.schema.json`.

`Capability` is a canonical model, but the first milestone does not define a separate capability schema. According to `docs/spec.md` §15, the versioned schema-backed canonical representations are:

* Skill
* Security Event
* Evidence
* Decision

The implementation must follow this specification rather than adding a schema only for symmetry.

---

## Scope

### 1. Skill

Implement the canonical Skill model according to `docs/spec.md` §7.1.

It must represent:

* `schema_version`
* skill identity
* name
* version
* description/purpose
* source
* integrity
* declaration
* dependencies
* context

Do not introduce speculative fields.

---

### 2. Capability

Implement the canonical Capability model according to `docs/spec.md` §7.2.

Initial supported canonical capability identifiers:

```text
task.read
network.egress
process.execute
filesystem.write
credential.read
```

The vocabulary must remain **extensible**.

Do not implement the vocabulary as an irreversible closed enum.

Capability identifiers should be validated against the currently supported canonical vocabulary while allowing the vocabulary to be expanded later.

Capability normalization must remain product-independent.

Do not place product-specific capability mappings inside the core model.

No separate capability JSON schema is required in Phase 1.

---

### 3. SecurityEvent

Implement the canonical Security Event model according to `docs/spec.md` §7.3.

Required representation:

* `schema_version`
* `event_id`
* `timestamp`
* `event_type`
* `context`
* `actor`
* `action`
* `target`

The specification discusses evidence/source conceptually, but no additional speculative fields should be introduced.

---

### 4. Evidence

Implement the canonical Evidence model according to `docs/spec.md` §7.4.

Supported evidence sources:

```text
declaration
static
runtime
policy
```

The model must not include:

* confidence scores
* evidence weights
* probabilistic scoring
* ranking mechanisms

Evidence remains source-tagged and deterministic in this milestone.

---

### 5. Decision

Implement the canonical Decision model according to `docs/spec.md` §7.5.

Supported decision values:

```text
ALLOW
FLAG
DENY
```

Supported reason codes:

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

Do not introduce additional decision states.

---

## Implementation Constraints

* Use the Python standard library where practical.
* Dataclasses are acceptable where appropriate.
* Do not introduce runtime dependencies.
* Do not use Pydantic.
* Do not implement an API framework.
* Do not implement networking or RPC.
* Do not implement integration interfaces yet.
* Do not implement the conformance engine yet.
* Do not implement conformance rules yet.
* Do not implement static analysis.
* Do not implement runtime monitoring.
* Do not implement policy evaluation.
* Do not implement the reference adapter.
* Do not implement a frontend.
* Do not introduce unnecessary abstractions.
* Models must remain completely product-independent.

---

## Schema Requirements

Create:

```text
schemas/skill.schema.json
schemas/security_event.schema.json
schemas/evidence.schema.json
schemas/decision.schema.json
```

Each schema must:

* be valid JSON Schema
* correspond to its canonical model
* use schema version `1.0`
* define required fields
* maintain the same field structure as its corresponding model
* contain no speculative fields

Do not create:

```text
schemas/capability.schema.json
```

---

## Tests

Create:

```text
tests/unit/test_models.py
```

Tests must cover:

* valid construction of Skill
* valid construction of Capability
* valid construction of SecurityEvent
* valid construction of Evidence
* valid construction of Decision
* missing required fields
* invalid structural values
* invalid capability identifiers
* invalid evidence sources
* invalid decision values
* invalid decision reason codes
* schema/model field alignment for:

  * Skill
  * SecurityEvent
  * Evidence
  * Decision

Do not require a schema/model alignment test for Capability because Capability does not have a separate schema in this milestone.

---

## Phase 1 Completion Criteria

Phase 1 is complete when:

* all required canonical models exist
* all four required schemas exist
* models validate their required structures
* capability validation supports the initial vocabulary without making it permanently closed
* decision and evidence values are validated
* schema/model field alignment tests pass
* no runtime dependencies have been added
* no Phase 2+ functionality has been implemented
* Ruff passes
* pytest passes

### Review checkpoint

After completing Phase 1, stop implementation.

Do not begin Phase 2 until the repository owner has reviewed and approved the Phase 1 implementation.

---

# Phase 2 — Integration Interfaces

## Goal

Define the minimal in-process integration contract described in `docs/spec.md` §5 and the adapter contract described in §10.

## Files

Create:

```text
src/agentic_conformance/core/interfaces/conformance_api.py
src/agentic_conformance/core/interfaces/adapter.py
src/agentic_conformance/core/interfaces/__init__.py

tests/unit/test_interfaces.py
```

## Scope

Implement the three core operations:

```text
register_skill(skill_profile)
emit_event(security_event)
evaluate(skill_id)
```

The integration contract must remain:

* in-process
* synchronous unless otherwise required by the implementation
* based on canonical models
* product-independent

Define an adapter contract that requires adapters to translate native product representations into canonical models.

Adapters must not implement central conformance rules.

Do not introduce:

* REST
* HTTP APIs
* RPC
* message brokers
* networking
* distributed execution
* unnecessary service abstractions

## Tests

Test that:

* the three integration operations exist
* their expected inputs/outputs are represented
* the adapter contract exposes the required translation/integration methods
* the adapter contract cannot be incorrectly instantiated without required behavior

## Phase 2 Completion Criteria

* integration contract exists
* adapter contract exists
* interfaces use canonical representations
* no product-specific logic exists in core
* tests pass

### Review checkpoint

After completing Phase 2, stop implementation.

Do not begin Phase 3 until the repository owner has reviewed and approved the Phase 2 implementation.

---

# Phase 3 — Minimal Conformance Engine

## Goal

Implement the deterministic conformance evaluation defined in `docs/spec.md` §8 and §9.

## Files

Create:

```text
src/agentic_conformance/core/conformance/structural.py
src/agentic_conformance/core/conformance/rules.py
src/agentic_conformance/core/conformance/engine.py
src/agentic_conformance/core/conformance/__init__.py

tests/unit/test_conformance_structural.py
tests/unit/test_conformance_rules.py
tests/integration/test_conformance_engine.py
```

## Scope

Implement structural validation for:

* Skill declarations
* canonical Security Events
* required fields
* supported capability identifiers

Implement the deterministic conformance relationships:

```text
D = declared capabilities
S = statically inferred capabilities
R = runtime observed capabilities
P = policy-permitted capabilities
```

Primary rule:

```text
R ⊆ D
```

Policy rule:

```text
R ⊆ P
```

Combined rule:

```text
R ⊆ D ∩ P
```

Static evidence is conceptually supported, but an advanced static analyzer is not part of this milestone.

The engine must not require static evidence for the initial runtime/policy conformance checks.

The engine evaluates the registered skill declaration and the runtime events available through the Phase 2 integration contract.

The engine must:

1. retrieve the registered skill declaration
2. validate its structure
3. validate relevant runtime events
4. derive observed capabilities
5. compare observed capabilities against declared capabilities
6. apply the simple permitted-capability policy when provided
7. produce a standardized Decision

## Decision behavior

The engine must produce:

```text
ALLOW
FLAG
DENY
```

with an appropriate reason code from the specification.

No complex policy language is required.

Policy may initially be represented as a simple permitted-capability set.

## Tests

Test:

### Structural checks

* valid declaration
* missing declaration fields
* invalid capability
* invalid Security Event

### Conformance rules

* `R ⊆ D`
* undeclared runtime capability
* `R ⊆ P`
* policy violation
* combined declaration/policy violation

### Engine

* valid conformant evaluation
* undeclared capability
* policy violation
* invalid declaration
* invalid event
* standardized Decision output

## Explicit non-goals for Phase 3

Do not implement:

* advanced static analysis
* LLM analysis
* probabilistic scoring
* complex policy languages
* product-specific rules
* runtime monitoring infrastructure
* enforcement mechanisms

## Phase 3 Completion Criteria

* structural checks are implemented
* conformance rules are implemented
* engine produces deterministic decisions
* reason codes are standardized
* all tests pass
* no static analyzer, LLM analyzer, or complex policy engine exists in `core/conformance`

### Review checkpoint

After completing Phase 3, stop implementation.

Do not begin Phase 4 until the repository owner has reviewed and approved the Phase 3 implementation.

---

# Phase 4 — Reference Application Adapter

## Goal

Implement the first product-specific adapter for the existing reference application.

The reference application is a controlled testbed for demonstrating the generic integration structure.

## Files

Create:

```text
src/agentic_conformance/adapters/reference_app/adapter.py
src/agentic_conformance/adapters/reference_app/mapping.py
src/agentic_conformance/adapters/reference_app/__init__.py

tests/unit/test_reference_adapter.py
```

## Scope

The adapter must:

* translate native skill/declaration information into canonical Skill representations
* translate native runtime actions into canonical Security Events
* normalize native capabilities into canonical capability identifiers
* call the generic integration contract
* remain limited to product-specific translation and integration

Examples of native behaviors that may map to canonical capabilities include:

```text
HTTP request
requests.get()
fetch()
network tool invocation
```

which may normalize to:

```text
network.egress
```

The adapter must not contain the central conformance rules.

## Tests

Test:

* native declaration → canonical Skill
* native runtime action → canonical Security Event
* native capability → canonical Capability
* integration with the generic core
* absence of conformance rules inside the adapter

## Phase 4 Completion Criteria

* reference application can integrate through the adapter
* translation logic remains product-specific
* conformance logic remains in core
* core contains zero reference-application-specific branches or assumptions
* tests pass

### Review checkpoint

After completing Phase 4, stop implementation.

Do not begin Phase 5 until the repository owner has reviewed and approved the Phase 4 implementation.

---

# Phase 5 — End-to-End Integration

## Goal

Demonstrate the complete flow:

```text
Reference Application
        ↓
Reference Adapter
        ↓
Canonical Models
        ↓
Conformance Core
        ↓
Standard Decision
```

## Files

Create:

```text
tests/integration/test_end_to_end.py
examples/reference_app_walkthrough.py
```

## Deterministic Decision Semantics

### Case A — Conformant

```text
D = {task.read}
R = {task.read}
```

Expected:

```text
ALLOW
```

### Case B — Undeclared capability

```text
D = {task.read}
R = {task.read, network.egress}
```

Expected:

```text
FLAG
```

Reason:

```text
UNDECLARED_CAPABILITY
```

### Case C — Policy violation

```text
D = {task.read, process.execute}
P = {task.read}
R = {process.execute}
```

Expected:

```text
DENY
```

Reason:

```text
POLICY_VIOLATION
```

### Invalid declaration/event

Invalid declaration or invalid event must produce:

```text
DENY
```

with the appropriate validation reason code.

These are the deterministic implementation semantics for this milestone.

## Tests

The end-to-end integration test must assert the exact expected decision and reason code for the defined cases.

Do not introduce additional decision behavior beyond the cases defined above unless explicitly required by `docs/spec.md`.

## Example

The walkthrough should:

1. create/register a reference skill
2. emit runtime events
3. evaluate the skill
4. print the resulting standardized decision

## Phase 5 Completion Criteria

* all three defined cases pass
* invalid declaration/event behavior passes
* adapter-to-core flow works
* walkthrough runs successfully
* integration tests pass

### Review checkpoint

After completing Phase 5, stop implementation.

Do not begin Phase 6 until the repository owner has reviewed and approved the Phase 5 implementation.

---

# Phase 6 — Tests, Validation, and Documentation

## Goal

Finalize the first milestone without introducing new architectural behavior.

## Scope

* extend tests where required by implemented behavior
* finalize the reference application walkthrough
* verify schema/model alignment
* verify architectural boundaries
* verify product independence of core
* verify adapter isolation
* clean up implementation issues found during review
* ensure documentation accurately reflects the implemented milestone

No new feature or architectural layer should be introduced in this phase.

## Validation

Run:

```text
uv run ruff check .
uv run pytest
```

Also verify:

* example walkthrough runs
* all tests pass
* no unintended runtime dependencies were added
* no product-specific logic exists in core
* no speculative features were added
* schemas remain aligned with canonical models
* repository structure remains consistent with `docs/spec.md`

## Phase 6 Completion Criteria

The first milestone is complete when:

* Ruff passes
* pytest passes
* the reference walkthrough runs
* all acceptance criteria in `docs/spec.md` are satisfied
* no out-of-scope functionality has been introduced
* implementation remains consistent with the specification

---

# Non-Goals for the First Milestone

The following are explicitly outside this implementation plan:

* multiple production adapters
* advanced static analysis
* advanced runtime monitoring
* LLM-based analysis
* large-scale benchmarking
* complex policy languages
* frontend/dashboard
* advanced reporting system
* performance optimization
* production enforcement for every host platform
* universal security policy language
* automatic patch generation
* complete malicious-skill detection
* large-scale vulnerability classification

Do not create new top-level directories for:

```text
frontend/
api/
services/
analyzers/
monitoring/
policies/
reports/
benchmark/
```

unless the specification is explicitly changed later.

---

# Architectural Boundaries

The core architectural boundary is:

```text
Adapter = translation + integration

Core = canonical representation + conformance evaluation
```

## Adapter

Responsible for:

* product-specific translation
* native capability mapping
* native event mapping
* registration/integration with the host product

The adapter must not implement central conformance rules.

## Core

Responsible for:

* canonical models
* canonical validation
* conformance evaluation
* standardized decisions
* standardized evidence representation

The core must:

* remain product-independent
* operate only on canonical representations
* contain no product-specific branches
* contain no assumptions about a particular host product

## Canonical Model Boundary

The architectural boundary is:

```text
Native Product Data
        ↓
     Adapter
        ↓
Canonical Models
        ↓
Conformance Core
```

Raw/native product data must not be passed directly into conformance rules.

## Enforcement Boundary

Evaluation and enforcement remain separate.

The core produces:

```text
ALLOW
FLAG
DENY
```

The host product remains responsible for deciding what operational action to take, such as:

```text
allow
warn
log
block
quarantine
request human approval
```

Future dispositions such as `MODIFY`, `ASK`, or `DEFER` may be considered later, but they are not required for this milestone.

---

# Implementation Order

The implementation must follow this order:

```text
Phase 1
Canonical Models + Schemas
        ↓
Review
        ↓
Phase 2
Integration Interfaces
        ↓
Review
        ↓
Phase 3
Conformance Engine
        ↓
Review
        ↓
Phase 4
Reference Adapter
        ↓
Review
        ↓
Phase 5
End-to-End Integration
        ↓
Review
        ↓
Phase 6
Final Testing + Validation
```

Do not skip ahead and implement later phases before the earlier phase has been reviewed.

---

# Implementation Practices

## Source of Truth

* `docs/spec.md` defines **WHAT** the system must implement.
* `docs/plan.md` defines **HOW** the implementation is sequenced.
* If the plan and specification conflict, the specification takes precedence.
* Do not silently expand the specification through implementation.

## Minimalism

Prefer:

* small focused modules
* standard-library functionality where sufficient
* simple deterministic behavior
* explicit data structures
* minimal dependencies

Avoid:

* premature abstractions
* unnecessary frameworks
* speculative infrastructure
* duplicate representations
* unnecessary service layers

## Repository Stability

Do not reorganize the repository unless there is a clear architectural reason supported by the specification.

Do not introduce new top-level directories outside the defined repository structure.

## Version Control

Claude must not:

* create commits
* create branches
* create tags
* push changes
* merge pull requests

Version-control operations are performed manually by the repository owner after review.

## Phase Discipline

Each phase must be implemented independently.

After completing a phase:

1. run the relevant tests
2. run validation
3. inspect the changed files
4. summarize the implementation
5. report anything intentionally not implemented
6. stop for repository-owner review

The next phase must not begin until the previous phase has been reviewed and approved.

---

# Acceptance Criteria Mapping

| Specification Requirement                            | Implementation Phase                   |
| ---------------------------------------------------- | -------------------------------------- |
| Host product can register a skill through an adapter | Phase 2 + Phase 4                      |
| Canonical Skill representation exists                | Phase 1                                |
| Native capabilities are normalized                   | Phase 4                                |
| Runtime activity becomes canonical Security Events   | Phase 1 + Phase 4                      |
| Core compares observed behavior with declaration     | Phase 3                                |
| Standardized decisions are produced                  | Phase 3                                |
| Reference app demonstrates a conformant skill        | Phase 5 — Case A                       |
| Reference app demonstrates an undeclared capability  | Phase 5 — Case B                       |
| Policy violation can produce DENY                    | Phase 5 — Case C                       |
| Product-specific logic remains outside core          | Phase 4 + architectural boundary tests |
| Schemas remain aligned with canonical models         | Phase 1 + Phase 6                      |

---

# Final Milestone Outcome

At the end of the first milestone, the repository should demonstrate the following generic flow:

```text
                HOST PRODUCT
                     │
                     ▼
              PRODUCT ADAPTER
                     │
                     ▼
             CANONICAL MODELS
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
      DECLARATION           RUNTIME EVENTS
          │                     │
          └──────────┬──────────┘
                     ▼
             CONFORMANCE CORE
                     │
                     ▼
            STANDARD DECISION
                     │
              ┌──────┼──────┐
              ▼      ▼      ▼
            ALLOW   FLAG   DENY
```

The first milestone therefore establishes a reusable, product-independent conformance layer rather than a product-specific security scanner.

Future work may add static analysis, richer runtime monitoring, additional adapters, policy engines, evidence correlation, frontend interfaces, and larger evaluation benchmarks, but those are intentionally deferred until the generic integration and conformance foundation is stable.
