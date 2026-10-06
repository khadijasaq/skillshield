# Specification: Downloaded Skill Assessment (SkillShield)

Status: Draft — second milestone (downloaded/marketplace skill assessment)
Schema version: 1.0 (extends, does not replace, the schema version established in `docs/spec.md`)

This document is the source of truth for **what** the second milestone should
do. It does not describe task breakdowns or sequencing beyond the
high-level phase list in §13 — a corresponding `plan.md`-style document, if
needed, is created separately and is not part of this specification.

`docs/spec.md` and `docs/plan.md` remain in force. This document does not
redefine or replace them; it extends them. Where anything here appears to
conflict with `docs/spec.md`, `docs/spec.md` takes precedence and this
document must be corrected.

---

## 1. Relationship to the first milestone

The first milestone (`docs/spec.md`, `docs/plan.md`) established a
product-independent conformance foundation:

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

with canonical models `Skill`, `Capability`, `SecurityEvent`, `Evidence`,
`Decision`; the conceptual sets `D` (declared), `S` (static), `R` (runtime),
`P` (policy); the rules `R ⊆ D`, `R ⊆ P`, `R ⊆ D ∩ P`; and the three-operation
integration contract `register_skill` / `emit_event` / `evaluate`.

**This milestone does not replace any of that.** It is architecturally the
same system, applied to a new kind of input and extended with two new
evidence-producing stages (static analysis, controlled execution) that feed
the same canonical models and the same conformance core.

The product name for this milestone's host-facing tool is **SkillShield**.
SkillShield is a *consumer* of the existing architecture, analogous to the
reference application, except that:

- its "host product" is a downloaded skill package rather than a live
  product installation, and
- it is itself responsible for *producing* most of the evidence (via static
  analysis and controlled execution) rather than merely relaying events a
  host product already generates.

Everything SkillShield produces must still arrive at `core/` as canonical
`Skill`, `SecurityEvent`, and `Evidence` instances, through an adapter, per
the existing architectural boundary. No new "core" concept introduced by
this milestone bypasses that boundary.

---

## 2. Scope of this milestone

### In scope

- A downloaded-skill adapter boundary (`adapters/skillshield/` or
  equivalent — see §13) that turns a downloaded skill package into a
  canonical `Skill`.
- A static-analysis output contract: a defined interface and canonical
  `Evidence`/`SecurityEvent` shape that a static analyzer must produce,
  without requiring a complete static-analysis implementation.
- A controlled-execution integration contract: a defined interface for
  executing a skill under observation, without selecting or building a
  specific sandbox technology.
- A runtime-monitoring contract: how observations made during controlled
  execution become canonical `SecurityEvent` objects — reusing the existing
  `SecurityEvent` model unchanged.
- Extension of the conformance core's set algebra to incorporate `S`
  (static) as an actual, populated set, alongside the existing `D`, `R`,
  `P` — including the comparison operators needed to detect
  declaration/static/runtime mismatches (§7).
- A minimal, generic policy interface expressing permitted/forbidden
  capabilities (extending, not replacing, `ConformanceEngine.set_policy`).
- A canonical **Finding** model distinguishing the *kind* of mismatch
  detected (undeclared, policy-violating, static/runtime mismatch, invalid,
  etc.) from the single `Decision` produced by the first milestone.
- A canonical **Assessment Report** structure aggregating a skill's
  declaration, evidence, findings, and decision into one artifact intended
  for a human reader.
- Use of the existing reference application
  (`github.com/khadijasaq/vuln-agentic-skills-app`) as the first concrete
  testbed for exercising this pipeline end-to-end on at least one skill.

### Explicitly out of scope for this milestone

See §14 for the full list. In summary: a complete static-analysis engine,
a real sandbox implementation, LLM-based analysis, a general policy
language, probabilistic/weighted risk scoring, a frontend/dashboard,
marketplace integration, and benchmark-suite evaluation are all deferred.

---

## 3. Terminology introduced in this milestone

- **Downloaded Skill** — a skill artifact that did not arrive through a live
  host-product integration (as in the first milestone) but as a standalone
  package/source tree obtained from a marketplace or other external source,
  prior to any decision about whether to trust or run it.
- **SkillShield** — the host-facing tool built on top of `core/` that
  accepts a Downloaded Skill and produces a Security Assessment. SkillShield
  itself is composed of an adapter, a static analyzer, a controlled
  execution environment, and a runtime monitor — all product-specific or
  assessment-specific components that sit outside `core/`.
- **Static Analyzer** — a component that inspects a skill's source/artifacts
  without executing them and produces static evidence.
- **Controlled Execution Environment ("the sandbox")** — a component that
  executes a Downloaded Skill under observation. Referred to generically;
  no specific technology is chosen in this document (§9, §12).
- **Runtime Monitor** — a component that observes activity during controlled
  execution and converts it into canonical `SecurityEvent` objects. This is
  the same `SecurityEvent` model as the first milestone; the only thing new
  is that the *source* of events is a sandbox rather than a live host
  product.
- **Finding** — a single, standardized statement that some comparison among
  `D`, `S`, `R`, `P` produced a notable result (e.g. "capability X was
  observed at runtime but not declared"). Distinct from a `Decision`: a
  skill's evaluation may yield zero, one, or several Findings, which are
  then summarized into exactly one `Decision` plus one Assessment Report.
- **Assessment Report** — the canonical, aggregate output of evaluating one
  Downloaded Skill: identity, declaration, evidence, Findings, Decision,
  and a recommendation (§10).

---

## 4. Stage 1 — Downloaded skill integration

### 4.1 Input

A Downloaded Skill, as given to SkillShield, conceptually consists of:

- a **manifest/metadata** component: whatever structured declaration the
  skill's native format uses to state its identity, version, and declared
  capabilities/permissions (the analogue of the first milestone's native
  skill dict, e.g. `native_skill["declared_capabilities"]`);
- a **source** component: the files that implement the skill's behavior
  (scripts, modules, prompts, tool definitions — whatever the native format
  uses);
- an optional **dependencies** component: declared third-party packages or
  other skills the skill depends on;
- an optional **runtime configuration** component: environment variables,
  config files, or invocation parameters needed to run the skill;
- an optional **credentials/configuration** component: secrets or
  connection details the skill expects to be supplied at runtime. This
  milestone does not require SkillShield to supply real credentials (see
  §9.3); it only needs to recognize that a skill *declares* a need for
  them, which is itself evidence.

This specification does **not** assume a specific on-disk package format
(e.g. a particular archive layout or manifest filename) for Downloaded
Skills in general, and does not assume the exact internal layout of
`vuln-agentic-skills-app` until it has been inspected. The adapter
implementing Stage 1 is responsible for whatever concrete parsing the real
package format requires; this document only fixes the *shape* the adapter
must produce on the way out.

### 4.2 Adapter boundary

Per the existing architecture (`docs/spec.md` §10), a downloaded-skill
adapter is responsible for:

1. Locating and parsing the manifest/metadata.
2. Translating declared capabilities/permissions into the canonical
   `Capability` vocabulary (extending the vocabulary via
   `register_capability` where the native format introduces genuinely new
   capability kinds — not by branching core logic).
3. Producing a canonical `Skill` via `register_skill`, exactly as the
   reference adapter does today — with `source` identifying the origin
   (e.g. `"vuln_agentic_skills_app"`) and `integrity` populated from
   whatever checksum/signature the package provides, or an explicit
   placeholder when none exists (not a fabricated value).
4. Exposing the skill's source-file locations to the Stage 2 static
   analyzer and its runtime configuration to the Stage 3 controlled
   execution environment. This is new surface area relative to the first
   milestone's adapter contract (which only needed to reach `evaluate`),
   and is specified in §5.1 and §6.1 rather than by modifying
   `ProductAdapter` itself.

### 4.3 Output

The output of Stage 1 is exactly one canonical `Skill` instance (§7.1 of
`docs/spec.md`), registered through the existing `register_skill`
operation, plus a reference to the skill's on-disk source location that
Stage 2 and Stage 3 can use (see §5.1, §6.1). No new canonical model is
required for this stage.

### 4.4 Use of the reference vulnerable-skills application

`github.com/khadijasaq/vuln-agentic-skills-app` is the first concrete
Downloaded Skill source this milestone targets. It is a **controlled
testbed**, not part of the generic architecture — identical in spirit to
how the reference application from the first milestone is "one adapter
among potentially many, not a special case baked into the core"
(`docs/spec.md` §11).

Before implementation, its actual manifest format, source layout, and
packaging must be inspected; this specification does not assume those
details sight-unseen. What it does fix is the boundary: whatever that
inspection reveals becomes adapter-internal translation logic (§4.2), never
a `core/` branch.

---

## 5. Stage 2 — Static security analysis

### 5.1 Interface/output contract

A static analyzer is a component with the following conceptual contract:

```text
analyze(skill_source_location) -> list[StaticFinding]
```

where `skill_source_location` is whatever Stage 1 exposes (a directory
path, file list, etc.) and a `StaticFinding` is the minimal information
needed to construct canonical `Evidence` and, where applicable, a canonical
`Capability`:

```text
StaticFinding:
    capability        — the canonical Capability this finding implies,
                         if any (e.g. "network.egress")
    file               — the source file the finding was observed in
    location           — a line number or other locator within that file,
                         where available
    detector           — a short identifier for which check produced this
                         finding (e.g. "import-scan", "endpoint-literal")
    description        — a short human-readable explanation
```

This milestone defines this contract and requires that **at least one**
concrete detector exists (sufficient to demonstrate the pipeline end-to-end
against the reference testbed — see §11), but does not require a complete
static-analysis framework. Additional detectors are added incrementally
without changing this contract.

### 5.2 Categories of evidence a static analyzer may eventually detect

The following are illustrative categories a detector may target over time.
This milestone does not commit to implementing all of them, and does not
treat this as a closed or exhaustive taxonomy:

```text
network access               filesystem access
process/command execution    subprocess usage
environment-variable access  credential/secret access
suspicious imports            dangerous dependencies
external endpoints             hidden actions
undeclared tools                undeclared capabilities
encoded/obfuscated content    suspicious code patterns
```

Each, when detected, is expected to map to a canonical `Capability` (e.g.
"process/command execution" → `process.execute`) through the same
kind of adapter-owned mapping table used by the reference adapter's
`mapping.py` — static-analysis capability mappings are not core logic
either.

### 5.3 From StaticFinding to canonical Evidence

Each `StaticFinding` becomes one canonical `Evidence` instance
(`docs/spec.md` §7.4) with:

```text
source      = EvidenceSource.STATIC
skill_id    = the Skill this analysis was run against
data        = {
                "capability": <capability identifier, if any>,
                "file": <file>,
                "location": <location>,
                "detector": <detector>,
                "description": <description>,
              }
```

This reuses the existing `Evidence` model unchanged. No new fields are
added to `Evidence` for this milestone; `data` (already an untyped `dict`
per the first milestone's model) is sufficient to carry static-specific
detail without widening the canonical schema. This is consistent with
`docs/spec.md` §7.4: "Evidence is treated as present/absent information
grouped by source, not as a scored signal" — static evidence here is
still present/absent per finding, not weighted.

The set of distinct capability identifiers across a skill's static
`Evidence` is, by definition, `S` (§7 below).

### 5.4 Conceptual flow

```text
Skill Source
     ↓
Static Analyzer
     ↓
StaticFinding(s)
     ↓
Canonical Evidence (source = STATIC)  +  Canonical Capability
     ↓
Conformance Layer
```

---

## 6. Stage 3 — Controlled/sandboxed execution

### 6.1 Integration contract

Controlled execution is specified as an interface, not an implementation:

```text
execute(skill, runtime_config) -> ExecutionHandle
```

`ExecutionHandle` is whatever lets the Stage 4 runtime monitor attach to
the running skill and later be told the skill has finished — its exact
shape is an implementation detail deferred past this specification, as
long as it satisfies: the sandbox is the only thing that actually runs the
skill's code, and the runtime monitor observes it only through channels
the sandbox provides (see §12 — "the sandbox itself is part of the
security boundary").

### 6.2 Untrusted-input principle

Downloaded skills are **untrusted by default**. This milestone's
controlled-execution component must be designed so that:

- the skill's code does not need to be trusted for the assessment to be
  meaningful;
- a skill that behaves maliciously during assessment does not compromise
  the assessment host, the conformance core, or the evidence already
  collected for other skills.

This specification does **not** select a specific isolation technology
(container, VM, seccomp profile, language-level sandbox, etc.) in this
milestone — see §12. What it fixes is the set of observations the chosen
technology must be able to make available to Stage 4, listed in §6.3.

### 6.3 Observable categories

The controlled execution environment must be capable of exposing, at
minimum, observations in each of these categories (mirroring the static
categories in §5.2 so the two can be compared in Stage 5):

```text
filesystem access (read/write/create/delete)
network access (connections, requests, endpoints contacted)
process execution (subprocesses, commands run)
environment/credential access (env vars read, secrets referenced)
tool invocation (calls the skill makes to its own declared tools)
agent actions (if the skill drives an agent loop)
external communication (any egress not already covered above)
created/modified files (as a specific case of filesystem access worth
    tracking by path, for reporting — §10)
```

This milestone requires that the sandbox integration contract can
*represent* observations in each category (so Stage 4 has something to
convert), not that every category has a working detector on day one. Which
categories have real instrumentation in the first implementation is an
implementation-phase decision (§13, Phase 3/4), not a specification
commitment.

### 6.4 Optional credentials

Per §4.1, a Downloaded Skill may declare that it needs credentials. The
controlled execution environment is not required to provide real,
functioning credentials in this milestone — it may supply placeholder/dummy
values, or none, and treat the skill's *attempt* to use credentials
(env-var read, specific file access, outbound auth header, etc.) as the
observation that matters, not whether the attempt succeeds. This avoids
making "obtain real third-party credentials for an untrusted skill" a
dependency of this milestone.

---

## 7. Stage 4 — Runtime monitoring

### 7.1 Observation → canonical SecurityEvent

Every discrete observation made during controlled execution becomes one
canonical `SecurityEvent` (`docs/spec.md` §7.3), exactly as in the first
milestone — no new event model is introduced. Representative mappings:

```text
network request        → network.egress
file read               → filesystem.read
file write              → filesystem.write
process execution       → process.execute
credential access       → credential.read
tool invocation         → the capability the tool maps to
```

Note that `filesystem.read` does not yet exist in the initial capability
vocabulary established by `docs/spec.md` §7.2 (`task.read`,
`network.egress`, `process.execute`, `filesystem.write`,
`credential.read`). Adding it (and any other capability a real
instrumentation path requires) is done the same way the first milestone
already supports: via `register_capability`, extending the open vocabulary
— never by hand-editing a closed enum, and never inside `core/` as a
product-specific branch.

### 7.2 Required event detail

As established in `docs/spec.md` §7.3, each `SecurityEvent` carries
`event_id`, `timestamp`, `event_type`, `context`, `actor`, `action`,
`target`. For sandbox-sourced events, this milestone requires the adapter
producing them to populate `context` consistently (e.g. including the
executing skill's `skill_id`, as the reference adapter already does, and
the execution/run identifier if the same skill is assessed more than
once) and to prefer the standard event payload — not to introduce a
different shape just because the source is a sandbox instead of a live
product. The `source` (sandbox vs. live host) of a `SecurityEvent` is not
itself a canonical field in this milestone (`SecurityEvent` has no
`source` field); where that distinction matters it is carried in
`context`, consistent with the model as it exists today.

### 7.3 From events to R

The set of distinct capability identifiers across a skill's runtime
`SecurityEvent`s is `R`, exactly as defined in `docs/spec.md` §8 — this
milestone does not change how `R` is derived, only how the events reach
the engine (sandbox instead of live host events).

---

## 8. Stage 5 — Declaration / static / runtime comparison

### 8.1 The four sets

```text
D = declared capabilities      (from Skill.declaration, as today)
S = statically inferred capabilities   (from Stage 2 Evidence — NEW, populated)
R = runtime observed capabilities      (from Stage 4 SecurityEvents, as today)
P = policy-permitted capabilities      (as today, via the policy interface — §9)
```

`S` existed only conceptually in the first milestone ("Static evidence is
supported conceptually in the model... but advanced static analysis is not
part of this milestone" — `docs/spec.md` §8). This milestone is what
populates `S` with real data for the first time.

### 8.2 Existing rules remain unchanged

```text
R ⊆ D
R ⊆ P
R ⊆ D ∩ P
```

These continue to hold and continue to be evaluated exactly as implemented
in `core/conformance/rules.py` (`runtime_within_declared`,
`runtime_within_policy`, `runtime_within_declared_and_policy`,
`undeclared_capabilities`, `policy_violating_capabilities`). This milestone
adds comparisons; it does not modify these.

### 8.3 New comparisons introduced by this milestone

```text
S - D   → statically inferred but undeclared capability
R - D   → runtime observed but undeclared capability        (already exists
            as undeclared_capabilities; re-stated here for completeness)
R - S   → runtime behavior not identified statically
S - R   → statically identified behavior not observed during this execution
R ∩ D   → observed behavior consistent with declaration
R ∩ P   → policy-compliant observed behavior
```

Each is a pure set operation over capability-identifier sets, exactly in
the style of the existing `rules.py` functions — e.g.:

```python
def static_within_declared(declared: set[str], static: set[str]) -> bool:
    """S ⊆ D — every statically inferred capability should be declared."""
    return static <= declared

def statically_undeclared_capabilities(declared: set[str], static: set[str]) -> set[str]:
    """S - D."""
    return static - declared

def runtime_not_statically_identified(static: set[str], observed: set[str]) -> set[str]:
    """R - S."""
    return observed - static

def statically_identified_not_observed(static: set[str], observed: set[str]) -> set[str]:
    """S - R."""
    return static - observed
```

These are additions to `core/conformance/rules.py` (or a sibling module),
following the same pattern as the existing functions: pure, deterministic,
operating only on plain sets of capability identifier strings, with no
scoring.

### 8.4 No probabilistic scoring

As in the first milestone, all of the above are deterministic set
memberships, not weighted or probabilistic signals. A non-empty `S - D` is
a fact ("this was statically inferred but not declared"), not a score.
Severity/risk classification (§10) is a separate, later step applied to
facts like these — it does not retroactively turn the underlying
comparison into a probability.

---

## 9. Stage 6 — Hidden/mismatched behavior detection

### 9.1 What counts as a mismatch

Given the comparisons in §8.3, this milestone distinguishes the following
situations, each mapped to a distinct `ReasonCode`/Finding type (§10):

| Situation | Set condition | Finding/reason |
|---|---|---|
| Runtime behavior absent from declaration | `R - D ≠ ∅` | `UNDECLARED_CAPABILITY` (existing) |
| Static finding absent from declaration | `S - D ≠ ∅` | `UNDECLARED_CAPABILITY` (same reason code; evidence source distinguishes static vs. runtime discovery) |
| Runtime behavior not predicted by static analysis | `R - S ≠ ∅` | `STATIC_RUNTIME_MISMATCH` (existing reason code — this is its first real producer) |
| Static finding never exercised at runtime | `S - R ≠ ∅` | Reported as a Finding for completeness/transparency (§10), but is explicitly **not**, on its own, treated as a violation — dead/unreached code paths are expected and not evidence of malicious behavior |
| Observed capability not policy-permitted | `R - P ≠ ∅` | `POLICY_VIOLATION` (existing) |
| Declaration itself is structurally invalid | n/a | `INVALID_DECLARATION` / `MISSING_DECLARATION` (existing) |
| Event itself is structurally invalid | n/a | `INVALID_EVENT` (existing) |
| Capability identifier not in the supported vocabulary | n/a | `UNKNOWN_CAPABILITY` (existing) |

No new `ReasonCode` values are required by this milestone; the eight
defined in `docs/spec.md` §7.5 are sufficient, because
`STATIC_RUNTIME_MISMATCH` was already reserved for exactly this purpose.

### 9.2 Evidence must explain itself

Per §5.3 and §7.2, every piece of `Evidence` behind a Finding already
carries what was discovered and how (`source`, and in `data`: capability,
file/location for static, or the originating `SecurityEvent` detail for
runtime). A Finding (§10) references the specific `Evidence` instance(s)
that produced it, so "what was declared / what was discovered / how it was
discovered / where" is always answerable by following Finding → Evidence →
(file+location) or (event+timestamp), without inventing a parallel
explanation mechanism.

### 9.3 Mismatch is not automatically malicious

This specification explicitly rejects treating every mismatch as evidence
of malice. `S - R` (statically identified but unreached) is the clearest
case — unreached code paths are normal. Even `R - D`
(`UNDECLARED_CAPABILITY`) only means the declaration was incomplete
relative to behavior; whether that is a bug, an oversight, or something
adversarial is a judgment the Assessment Report's severity/recommendation
(§10) may inform but must not silently assert. No component in this
milestone is permitted to upgrade a Finding into a claim like "this skill
is malicious" — only into standardized, falsifiable statements like "R - D
= {network.egress}".

---

## 10. Stage 7 & 8 — Policy/risk evaluation and the security assessment report

### 10.1 Policy interface (extends, does not replace, `set_policy`)

The first milestone already has a minimal policy mechanism:
`ConformanceEngine.set_policy(skill_id, frozenset[str])`, representing `P`
as a flat permitted-capability set. This milestone extends it just enough
to express **forbidden** capabilities explicitly (not merely "absent from
the permitted set"), since a downloaded-skill policy needs to be able to
say "this capability is actively denied" rather than only "this capability
was never allowed" — the two read differently in a report even though they
currently produce the same `POLICY_VIOLATION` outcome.

```text
PolicyRule:
    capability   — a canonical Capability identifier
    effect       — ALLOW | FLAG | DENY
```

A policy for a skill is a collection of `PolicyRule`s. The policy
evaluation for a given observed capability is: the most specific matching
rule's `effect` applies; a capability with no matching rule falls back to
the existing default (absent from `P` → violation, i.e. effectively
`DENY`, preserving current behavior exactly for skills that do not use the
new rule form). This is additive: existing callers using
`set_policy(skill_id, frozenset(...))` continue to work unchanged, since a
flat permitted set is the special case where every listed capability has
effect `ALLOW` and everything else is `DENY`.

This remains deliberately minimal — not a general-purpose policy language
(no wildcards, no conditions, no composition operators). It is the
smallest extension that lets §10.3's report distinguish "flagged" from
"denied" capabilities, as the stage-8 conceptual example in this
milestone's source brief requires.

### 10.2 Separation of concerns

This milestone keeps four things distinct, per the brief's explicit
requirement not to collapse them into one score:

```text
Conformance result  — the existing ALLOW/FLAG/DENY Decision (docs/spec.md §7.5)
Policy result        — which PolicyRule(s), if any, matched and with what effect
Security Finding      — one standardized statement from §9.1's table
Overall assessment   — the Assessment Report (§10.3), which aggregates all
                        of the above but does not reduce them to a single
                        number
```

### 10.3 Canonical Assessment Report structure

A new canonical model, `Assessment`, aggregates the result of evaluating
one Downloaded Skill:

```text
Assessment:
    schema_version          — "1.0"
    skill_id                 — the assessed Skill's id
    skill_name                — for report readability
    skill_version             — for report readability
    source                    — where the skill came from (matches Skill.source)
    declared_capabilities     — D, as declared-capability identifiers
    static_capabilities       — S, as capability identifiers found by Stage 2
    runtime_capabilities       — R, as capability identifiers observed in Stage 4
    findings                  — list[Finding] (§9.1/§10.4)
    policy_results             — list of (capability, matched PolicyRule or None, effect)
    decision                   — the existing canonical Decision
    severity                  — a small closed classification (§10.5)
    recommendation             — a short human-readable string (e.g. "DO NOT USE"),
                                 derived mechanically from decision + severity,
                                 never freeform/generated text
```

This is a new model, additive to the existing five (`Skill`, `Capability`,
`SecurityEvent`, `Evidence`, `Decision`) — it does not modify any of them.
Like them, it gets a corresponding JSON Schema
(`schemas/assessment.schema.json`) field-aligned with this dataclass, per
`docs/spec.md` §15's standing rule that schemas track models 1:1. Per
`docs/spec.md` §7.4/§17, it introduces no scoring mechanism beyond the
closed severity classification in §10.5 — "severity" here is a label, not a
probability.

### 10.4 Canonical Finding structure

```text
Finding:
    reason_code       — one of the existing ReasonCode values (§9.1)
    capabilities       — the specific capability identifier(s) involved
    evidence_refs       — identifiers of the Evidence instance(s) behind this finding
    description          — short, mechanically generated, human-readable text
                           (e.g. "network.egress observed at runtime but not declared")
```

`Finding` is a new canonical model, additive to the existing set. It does
not replace `Decision` — a skill's evaluation still produces exactly one
`Decision` (§7.5 of `docs/spec.md`, unchanged), and may in addition produce
zero or more `Finding`s that explain *why*, feeding into the `Assessment`
(§10.3).

### 10.5 Severity classification

A small, closed, non-probabilistic classification is introduced to let the
Assessment Report communicate relative concern without scoring:

```text
LOW
MEDIUM
HIGH
```

Mapping from Decision + Finding reason codes to severity is deterministic
and fixed (e.g. any `POLICY_VIOLATION` or `INTEGRITY_FAILURE` → `HIGH`; any
`UNDECLARED_CAPABILITY` or `STATIC_RUNTIME_MISMATCH` with no policy
violation → `MEDIUM`; a clean `ALLOW` with no findings → `LOW`). The exact
mapping table is an implementation-phase detail (§13, Phase 6/7) but the
*kind* of classification (closed, deterministic, three values) is fixed
here so implementation does not drift into probabilistic scoring.

### 10.6 Report format is not frozen

The conceptual example in this milestone's source brief (skill identity,
declared/static/runtime findings, conformance result, policy result,
overall severity, recommendation) is illustrative of *content*, not of a
committed rendering format (text block, JSON, HTML, etc.). This milestone
fixes the `Assessment`/`Finding` canonical models (§10.3, §10.4); how they
are rendered to a user is deferred (§14 — "frontend/dashboard" and
"advanced reporting system" are explicitly out of scope). A minimal,
unstyled textual rendering (akin to today's
`examples/reference_app_walkthrough.py` printing) is sufficient for this
milestone's end-to-end demonstration (§11).

---

## 11. Evaluation strategy

This milestone's evaluation is staged, matching the source brief exactly:

1. **Single skill, single testbed.** Use
   `github.com/khadijasaq/vuln-agentic-skills-app` and demonstrate, on at
   least one of its skills, all of:
   - benign declared behavior (an `ALLOW` case, analogous to Case A in
     `docs/plan.md` Phase 5),
   - undeclared behavior discovered at runtime (`R - D`),
   - at least one static finding (`S` populated, nonempty),
   - at least one runtime finding (`R` populated, nonempty),
   - at least one declaration/runtime mismatch
     (`UNDECLARED_CAPABILITY` or `STATIC_RUNTIME_MISMATCH`),
   - at least one policy violation (reusing/extending `set_policy` per
     §10.1).
2. **Expand to additional skills** within the same testbed application
   once (1) is demonstrated end-to-end.
3. **External benchmark/dataset sources** (Trail of Bits Overtly Malicious
   Skills, MalSkillBench, MaliciousSkillBench, SkillTrustBench, or similar)
   are a **future** evaluation target, explicitly not a dependency of this
   milestone or its acceptance criteria (§15). They are named here only so
   future milestones have a known direction.

---

## 12. Security boundaries

Monitoring a skill does not make running it safe. The act of executing an
untrusted Downloaded Skill is the dangerous step; the runtime monitor
(§7) only observes that step after the fact (or concurrently) — it is not
itself what makes execution safe. Safety, to whatever extent this milestone
provides it, comes from the controlled execution environment (§6) isolating
the execution, not from the monitor watching it.

The actors/components relevant to this boundary:

```text
Untrusted Skill          — the Downloaded Skill under assessment; never trusted
Assessment Host            — the machine/process running SkillShield itself;
                             must remain unaffected by anything the untrusted
                             skill does
Sandbox                     — the controlled execution environment (§6);
                             the actual isolation boundary between the
                             untrusted skill and the assessment host
Monitor                      — observes the sandbox and produces SecurityEvents
                             (§7); a monitoring failure should not be
                             mistaken for a safety failure, and vice versa
Conformance Core             — unchanged from the first milestone; operates
                             only on canonical data that has already crossed
                             out of the sandbox
Evidence Store / Report       — the Assessment and its Evidence, retained
                             after execution has ended
User                          — makes the trust/use decision based on the
                             Assessment Report
```

This milestone does **not** select a sandbox technology (container, VM,
seccomp, gVisor, a restricted subprocess, language-level isolation, etc.).
That selection is deferred to the implementation phase that actually builds
the controlled execution environment (§13, Phase 3), and must be made with
the isolation requirement in §6.2 as its acceptance bar — not performance,
not convenience. Until a real sandbox exists, any interim/stub
implementation used to exercise this pipeline (§13, Phase 3) must be
clearly documented as non-isolating and must not be run against skills from
untrusted sources outside the fixed reference testbed (§4.4).

---

## 13. Phased implementation plan

This is a planning outline, not a committed sequence with file-level detail
(that belongs in a `plan.md`-equivalent produced separately, following the
same review process as `docs/plan.md`). Each phase below names its
objective, scope, likely components, inputs/outputs, acceptance criteria,
tests, and non-goals at the level this specification can responsibly fix in
advance; concrete file paths are deferred to that later planning step.

### Phase 1 — Downloaded skill adapter/integration

- **Objective:** bring a real skill from `vuln-agentic-skills-app` into the
  system as a canonical `Skill`.
- **Scope:** inspect the testbed's actual manifest/source format; build the
  adapter described in §4.2.
- **Likely components:** a new adapter package (e.g.
  `adapters/vuln_agentic_skills_app/`, named for what it actually adapts —
  not a generic `adapters/skillshield/`, consistent with
  `adapters/reference_app/` being named for its product).
- **Inputs:** the testbed's on-disk skill package.
- **Outputs:** one registered canonical `Skill`.
- **Acceptance criteria:** `register_skill` succeeds for at least one real
  skill from the testbed; declared capabilities normalize into the
  canonical vocabulary (extending it via `register_capability` as needed).
- **Tests:** adapter unit tests analogous to `test_reference_adapter.py`.
- **Non-goals:** static analysis, execution, monitoring.

### Phase 2 — Static analysis foundation

- **Objective:** implement the contract in §5.1 with at least one real
  detector.
- **Scope:** `StaticFinding` → `Evidence` conversion (§5.3); one concrete
  detector (e.g. an import/literal scan for network or process-execution
  indicators) sufficient to produce a nonempty `S` for the Phase 1 skill.
- **Likely components:** a static-analysis module outside `core/` (static
  analyzers are listed in §10 of this document as their own category,
  distinct from adapters).
- **Inputs:** the skill's source location (from Phase 1).
- **Outputs:** `Evidence` instances with `source = STATIC`.
- **Acceptance criteria:** at least one `StaticFinding` is produced for the
  Phase 1 skill and converts into canonical `Evidence`.
- **Tests:** unit tests for the detector and for `StaticFinding → Evidence`
  conversion.
- **Non-goals:** a complete static-analysis framework; obfuscation
  detection; dependency scanning beyond what the one chosen detector
  covers.

### Phase 3 — Controlled execution/sandbox foundation

- **Objective:** implement the interface in §6.1 with a minimal,
  explicitly-non-production isolation mechanism sufficient to run the
  Phase 1 skill under observation.
- **Scope:** `execute(skill, runtime_config) -> ExecutionHandle`; document
  the isolation limitations explicitly per §12.
- **Likely components:** a sandbox module outside `core/`.
- **Inputs:** the registered `Skill` and whatever runtime configuration it
  declares needing (§4.1).
- **Outputs:** a running/completed execution that Phase 4 can attach to.
- **Acceptance criteria:** the Phase 1 skill can be executed through this
  interface at all (isolation strength is explicitly not graded in this
  milestone — see §12).
- **Tests:** integration test that execution starts and completes for the
  Phase 1 skill.
- **Non-goals:** production-grade isolation; multi-tenant execution;
  resource-limit enforcement.

### Phase 4 — Runtime monitoring

- **Objective:** convert Phase 3 observations into canonical
  `SecurityEvent`s per §7.
- **Scope:** at least the observable categories actually exercised by the
  Phase 1 skill; `register_capability` extensions as needed (e.g.
  `filesystem.read`, §7.1).
- **Likely components:** a monitor module outside `core/`, paired with
  Phase 3's sandbox.
- **Inputs:** sandbox-level observations.
- **Outputs:** canonical `SecurityEvent`s, fed through the existing
  `emit_event`.
- **Acceptance criteria:** at least one real runtime event is captured for
  the Phase 1 skill and reaches `R` via the existing engine.
- **Tests:** integration test analogous to `test_conformance_engine.py`,
  using sandbox-sourced events instead of hand-constructed ones.
- **Non-goals:** full behavioral coverage of every category in §6.3.

### Phase 5 — Declaration/static/runtime correlation

- **Objective:** implement the new set comparisons in §8.3 and the Finding
  mapping in §9.1.
- **Scope:** new pure functions alongside `core/conformance/rules.py`; the
  `Finding` model (§10.4); wiring `STATIC_RUNTIME_MISMATCH` to its first
  real producer.
- **Likely components:** `core/conformance/` (rules only — still
  product-independent) and `core/models/finding.py`.
- **Inputs:** `D`, `S`, `R` for the Phase 1 skill (from Phases 1, 2, 4).
- **Outputs:** a list of `Finding`s for that skill.
- **Acceptance criteria:** each of the six comparisons in §8.3 is
  implemented and unit-tested in isolation; at least one nonempty
  real-data case (from the Phase 1 skill) is demonstrated for at least one
  comparison.
- **Tests:** unit tests mirroring `test_conformance_rules.py`.
- **Non-goals:** probabilistic scoring; collapsing findings into the
  `Decision` itself (they remain separate, per §10.2).

### Phase 6 — Policy and risk evaluation

- **Objective:** implement the `PolicyRule`/effect extension in §10.1 and
  the severity classification in §10.5.
- **Scope:** extend the policy mechanism without breaking existing
  `set_policy(skill_id, frozenset)` callers; fix the severity mapping
  table.
- **Likely components:** `core/conformance/engine.py` (extended, not
  rewritten) and a small policy module.
- **Inputs:** `R`, the skill's policy rules.
- **Outputs:** policy results (§10.2) and a severity classification.
- **Acceptance criteria:** existing Phase-5-of-first-milestone tests
  (Cases A/B/C in `tests/integration/test_end_to_end.py`) continue to pass
  unmodified; a new policy-rule-based case demonstrates `FLAG` vs. `DENY`
  distinguished by `effect`.
- **Tests:** unit tests for policy-rule matching; regression run of
  existing end-to-end tests.
- **Non-goals:** a general-purpose policy language; probabilistic risk
  scores.

### Phase 7 — Security assessment/report

- **Objective:** implement the `Assessment` model (§10.3) and a minimal
  textual rendering.
- **Scope:** aggregate `Skill`, `Evidence`, `Finding`s, `Decision`, policy
  results, and severity into one `Assessment`; add
  `schemas/assessment.schema.json`.
- **Likely components:** `core/models/assessment.py`; an example
  walkthrough script analogous to
  `examples/reference_app_walkthrough.py`.
- **Inputs:** the outputs of Phases 1–6 for the Phase 1 skill.
- **Outputs:** one `Assessment` instance, printed in a minimal textual
  form.
- **Acceptance criteria:** running the new walkthrough against the Phase 1
  skill produces a complete `Assessment` with all fields in §10.3
  populated and a schema-aligned `Assessment` model.
- **Tests:** schema/model alignment test analogous to the existing
  per-model alignment checks; an end-to-end test asserting the `Assessment`
  for the Phase 1 skill has the expected findings/severity/recommendation.
- **Non-goals:** a frontend/dashboard; HTML/PDF rendering; freeform
  generated text.

### Phase 8 — Evaluation against vulnerable/benchmark skills

- **Objective:** broaden coverage within the existing testbed, per §11
  step 2.
- **Scope:** additional skills from `vuln-agentic-skills-app`, exercising
  more of §6.3's observable categories and more detectors from §5.2.
- **Likely components:** no new core components expected; primarily new
  detectors, new sandbox observation categories, and new tests.
- **Inputs/outputs:** same shapes as Phases 1–7, applied to more skills.
- **Acceptance criteria:** at minimum, the six demonstration cases in §11
  step 1 are each shown on a genuinely distinct skill from the testbed
  (not merely re-run on the Phase 1 skill), proving the pipeline
  generalizes within the testbed.
- **Tests:** additional end-to-end tests, one per newly covered skill.
- **Non-goals:** external benchmark integration (§11 step 3) — explicitly
  deferred past this milestone.

---

## 14. Explicitly out of scope for this milestone

This milestone does **not** implement:

- a complete malware/malicious-skill detector
- universal or complete static analysis
- LLM-based security analysis
- a universal/general-purpose policy language
- marketplace integration with every marketplace
- production-grade sandbox isolation
- a frontend/dashboard
- automatic patch generation
- autonomous remediation
- a large/exhaustive vulnerability taxonomy
- probabilistic or weighted risk scoring
- evaluation against every external benchmark at once (only the staged
  approach in §11 is in scope)

The goal is an incrementally built assessment pipeline that demonstrably
works end-to-end on one real skill before breadth is added — not maximal
coverage from the start.

---

## 15. Acceptance criteria for this milestone

1. A Downloaded Skill from `vuln-agentic-skills-app` can be registered as a
   canonical `Skill` through a dedicated adapter (§4).
2. A static analyzer produces at least one real `Evidence` instance with
   `source = STATIC` for that skill, populating `S` (§5).
3. A controlled execution environment can run that skill under observation,
   with its isolation limitations explicitly documented (§6, §12).
4. Runtime observations during that execution become canonical
   `SecurityEvent`s, populating `R` through the existing `emit_event`
   operation (§7).
5. All six comparisons in §8.3 are implemented as pure, tested functions,
   and at least one produces a nonempty result against real data from the
   target skill (§8).
6. At least one `UNDECLARED_CAPABILITY` and at least one
   `STATIC_RUNTIME_MISMATCH` Finding can be produced and correctly
   attributed to their originating Evidence (§9).
7. Policy evaluation can distinguish an `ALLOW`-effect capability from a
   `DENY`-effect capability for the same skill, without breaking any
   existing first-milestone policy test (§10.1).
8. A canonical `Assessment` can be produced for the target skill with every
   field in §10.3 populated, backed by a schema aligned with the model
   (§10.3, consistent with `docs/spec.md` §15).
9. The six demonstration cases in §11 step 1 are all shown for at least one
   skill from the reference testbed.
10. `core/` contains no branch, conditional, or assumption specific to
    `vuln-agentic-skills-app`, to a particular sandbox technology, or to a
    particular static-analysis engine (consistent with `docs/spec.md` §2).
11. All new canonical models (`Finding`, `Assessment`) have schemas in
    `schemas/` that remain field-aligned with their models, per the
    existing alignment-testing pattern.
12. All existing first-milestone tests continue to pass unmodified.

---

## 16. Relationship to repository structure

This specification does not require reorganizing the existing structure.
Anticipated additions (exact paths to be fixed by the implementation plan,
not this document):

```text
src/agentic_conformance/
├── core/
│   ├── models/
│   │   └── finding.py, assessment.py        (NEW — additive)
│   └── conformance/
│       └── rules.py                          (EXTENDED — new pure functions)
│
└── adapters/
    └── <vuln-agentic-skills-app adapter>/    (NEW)

<static analysis module>                      (NEW — outside core/)
<sandbox / controlled execution module>       (NEW — outside core/)
<runtime monitor module>                       (NEW — outside core/)

schemas/
├── finding.schema.json                       (NEW)
└── assessment.schema.json                     (NEW)

docs/
└── downloaded-skill-assessment-spec.md        (this document)

tests/, examples/                              (extended, same conventions)
```

No new top-level directories beyond what `docs/plan.md`'s non-goals section
already anticipates needing architectural justification for
(`frontend/`, `api/`, `services/`, `analyzers/`, `monitoring/`,
`policies/`, `reports/`, `benchmark/`) are introduced by this
specification. Where a phase above needs a home for static-analysis,
sandbox, or monitoring code, that placement is an implementation-plan
decision made with the same care `docs/plan.md` §"Repository Stability"
already requires — not a default to one of those names.
