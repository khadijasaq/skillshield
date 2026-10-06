"""Declaration/static/runtime (D/S/R) correlation (second milestone, Phase 5;
docs/downloaded-skill-assessment-spec.md §8.3, §9.1).

Spec §8.3 refers to six comparison relationships/categories (`S-D`, `R-D`,
`R-S`, `S-R`, `R∩D`, `R∩P`), with `S ⊆ D` given alongside them in the same
section's rule set. Every one of these seven is implemented or
represented, and explicitly tested (see `tests/unit/test_conformance_correlation.py`)
— but, per the corrected implementation plan, no redundant helper is
written for a comparison already directly supported elsewhere:

```text
1. S ⊆ D   static_within_declared()                           [NEW, this module]
2. S - D   statically_undeclared_capabilities()                 [NEW, this module]
3. R - D   rules.undeclared_capabilities()                        [REUSED, unmodified]
4. R - S   runtime_not_statically_identified()                     [NEW, this module]
5. S - R   statically_identified_not_observed()                     [NEW, this module]
6. R ∩ D   plain set intersection (observed & declared)               [ordinary set op]
7. R ∩ P   plain set intersection (observed & policy)                  [ordinary set op]
```

`correlate()` wires the capability-level comparisons to standardized
`Finding`s, reusing the existing `rules.py` functions for `R - D` and
`R - P` rather than duplicating them. `S ⊆ D` and `S - R` are computed for
completeness/transparency (per spec §9.1's "Static finding never
exercised at runtime... not, on its own, treated as a violation") but
deliberately do **not** produce a `Finding`: forcing a neutral,
non-violation fact through the `ReasonCode` vocabulary would either
require a ninth reason code (the spec explicitly says none are needed) or
misuse an existing violation-flavored one for something that is, by
definition, not a violation. `S - R` remains visible to a caller via the
plain capability sets this module accepts, and (in Phase 7) via the
`Assessment`'s own `declared_capabilities`/`static_capabilities`/
`runtime_capabilities` fields.

This module operates only on canonical `Evidence`/`SecurityEvent`
instances and plain capability-identifier sets — it has no knowledge of
`vuln-agentic-skills-app`, any sandbox, or any specific static analyzer.
"""

from __future__ import annotations

from agentic_conformance.core.conformance.rules import (
    policy_violating_capabilities,
    undeclared_capabilities,
)
from agentic_conformance.core.models import Evidence, EvidenceSource, SecurityEvent
from agentic_conformance.core.models.decision import ReasonCode
from agentic_conformance.core.models.finding import Finding


def static_within_declared(declared: set[str], static: set[str]) -> bool:
    """S ⊆ D — every statically inferred capability should be declared."""
    return static <= declared


def statically_undeclared_capabilities(declared: set[str], static: set[str]) -> set[str]:
    """S - D — statically inferred but undeclared capabilities."""
    return static - declared


def runtime_not_statically_identified(static: set[str], observed: set[str]) -> set[str]:
    """R - S — runtime behavior not identified statically."""
    return observed - static


def statically_identified_not_observed(static: set[str], observed: set[str]) -> set[str]:
    """S - R — statically identified behavior not observed during this execution."""
    return static - observed


def static_capability_set(static_evidence: list[Evidence]) -> set[str]:
    """The distinct canonical capability identifiers across STATIC Evidence — `S`."""
    return {
        item.data["capability"]
        for item in static_evidence
        if item.source is EvidenceSource.STATIC and "capability" in item.data
    }


def runtime_capability_set(events: list[SecurityEvent]) -> set[str]:
    """The distinct canonical capability identifiers across runtime events — `R`."""
    return {event.action.capability.identifier for event in events}


def _static_evidence_refs(skill_id: str, static_evidence: list[Evidence]) -> dict[str, list[str]]:
    """capability -> evidence_refs, for STATIC Evidence.

    `Evidence` (docs/spec.md §7.4) has no unique id field — deliberately,
    per docs/downloaded-skill-assessment-spec.md §5.3 ("no new fields are
    added to Evidence for this milestone") — so a stable, deterministic
    composite reference is derived from its own traceability fields
    instead of requiring a new one.
    """
    index: dict[str, list[str]] = {}
    for item in static_evidence:
        if item.source is not EvidenceSource.STATIC or "capability" not in item.data:
            continue
        capability = item.data["capability"]
        ref = (
            f"static:{skill_id}:{item.data.get('file')}:"
            f"{item.data.get('location')}:{item.data.get('detector')}"
        )
        index.setdefault(capability, []).append(ref)
    return index


def _runtime_evidence_refs(events: list[SecurityEvent]) -> dict[str, list[str]]:
    """capability -> evidence_refs, for runtime SecurityEvents (using their
    existing unique `event_id`)."""
    index: dict[str, list[str]] = {}
    for event in events:
        index.setdefault(event.action.capability.identifier, []).append(event.event_id)
    return index


def _refs_for(capabilities: set[str], *indices: dict[str, list[str]]) -> tuple[str, ...]:
    refs: set[str] = set()
    for capability in capabilities:
        for index in indices:
            refs.update(index.get(capability, ()))
    return tuple(sorted(refs))


def correlate(
    skill_id: str,
    declared: set[str],
    static_evidence: list[Evidence],
    events: list[SecurityEvent],
    policy: set[str] | None = None,
) -> list[Finding]:
    """Compare D/S/R/P for one skill and produce standardized Findings.

    Produces at most three Findings, each only when its triggering
    comparison is non-empty:

    * `UNDECLARED_CAPABILITY` — from `(S - D) | (R - D)` (spec §9.1: both
      a static and a runtime discovery of an undeclared capability map to
      this same reason code; the evidence_refs distinguish how each was
      discovered).
    * `STATIC_RUNTIME_MISMATCH` — from `R - S` (first real producer of
      this reason code, per spec §9.1).
    * `POLICY_VIOLATION` — from `R - P`, only when `policy` is supplied
      (reuses the existing, unmodified `rules.policy_violating_capabilities`).
    """
    static_capabilities = static_capability_set(static_evidence)
    observed = runtime_capability_set(events)
    static_index = _static_evidence_refs(skill_id, static_evidence)
    runtime_index = _runtime_evidence_refs(events)

    findings: list[Finding] = []

    undeclared = statically_undeclared_capabilities(declared, static_capabilities) | (
        undeclared_capabilities(declared, observed)
    )
    if undeclared:
        findings.append(
            Finding(
                reason_code=ReasonCode.UNDECLARED_CAPABILITY,
                capabilities=tuple(sorted(undeclared)),
                evidence_refs=_refs_for(undeclared, static_index, runtime_index),
                description=(
                    "Capabilities statically inferred or observed at runtime but not "
                    f"declared: {sorted(undeclared)}."
                ),
            )
        )

    mismatch = runtime_not_statically_identified(static_capabilities, observed)
    if mismatch:
        findings.append(
            Finding(
                reason_code=ReasonCode.STATIC_RUNTIME_MISMATCH,
                capabilities=tuple(sorted(mismatch)),
                evidence_refs=_refs_for(mismatch, runtime_index),
                description=(
                    "Capabilities observed at runtime but not identified by static "
                    f"analysis: {sorted(mismatch)}."
                ),
            )
        )

    if policy is not None:
        violating = policy_violating_capabilities(policy, observed)
        if violating:
            findings.append(
                Finding(
                    reason_code=ReasonCode.POLICY_VIOLATION,
                    capabilities=tuple(sorted(violating)),
                    evidence_refs=_refs_for(violating, runtime_index),
                    description=(
                        "Capabilities observed at runtime but not policy-permitted: "
                        f"{sorted(violating)}."
                    ),
                )
            )

    return findings
