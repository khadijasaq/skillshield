"""Tests for D/S/R correlation (second milestone, Phase 5;
docs/downloaded-skill-assessment-spec.md §8.3).

Covers all seven comparison relationships listed in §8.3 — the four new
pure functions, the three reused/ordinary-set-operation ones — using
deterministic, hand-constructed fixtures, per the corrected plan's
requirement that every comparison have explicit test coverage, not only
the newly written functions.
"""

from __future__ import annotations

from agentic_conformance.core.conformance.correlation import (
    correlate,
    runtime_capability_set,
    runtime_not_statically_identified,
    static_capability_set,
    static_within_declared,
    statically_identified_not_observed,
    statically_undeclared_capabilities,
)
from agentic_conformance.core.conformance.rules import (
    policy_violating_capabilities,
    undeclared_capabilities,
)
from agentic_conformance.core.models import (
    Action,
    Actor,
    Capability,
    Evidence,
    EvidenceSource,
    ReasonCode,
    SecurityEvent,
    Target,
)


def _static_evidence(skill_id: str, capability: str, file: str = "skill.py",
                      location: int = 1, detector: str = "x") -> Evidence:
    return Evidence(
        source=EvidenceSource.STATIC,
        skill_id=skill_id,
        data={"capability": capability, "file": file, "location": location,
              "detector": detector, "description": "x"},
    )


def _event(capability: str, event_id: str, skill_id: str = "s") -> SecurityEvent:
    return SecurityEvent(
        event_id=event_id,
        timestamp="2026-10-06T00:00:00Z",
        event_type=capability,
        context={"skill_id": skill_id},
        actor=Actor(type="skill", id=skill_id),
        action=Action(capability=Capability(capability), operation="invoke"),
        target=Target(type="resource", identifier="x"),
    )


# ---------------------------------------------------------------------------
# 1. S ⊆ D
# ---------------------------------------------------------------------------


def test_static_within_declared_true_when_subset():
    assert static_within_declared({"task.read", "network.egress"}, {"task.read"}) is True


def test_static_within_declared_false_when_not_subset():
    assert static_within_declared({"task.read"}, {"task.read", "network.egress"}) is False


# ---------------------------------------------------------------------------
# 2. S - D
# ---------------------------------------------------------------------------


def test_statically_undeclared_capabilities_reports_difference():
    assert statically_undeclared_capabilities({"task.read"}, {"task.read", "network.egress"}) == {
        "network.egress"
    }


def test_statically_undeclared_capabilities_empty_when_conformant():
    assert statically_undeclared_capabilities({"task.read", "network.egress"}, {"task.read"}) == set()


# ---------------------------------------------------------------------------
# 3. R - D — reused from core.conformance.rules, exercised here directly
# ---------------------------------------------------------------------------


def test_reused_runtime_undeclared_capabilities():
    assert undeclared_capabilities({"task.read"}, {"task.read", "filesystem.read"}) == {
        "filesystem.read"
    }


# ---------------------------------------------------------------------------
# 4. R - S
# ---------------------------------------------------------------------------


def test_runtime_not_statically_identified_reports_difference():
    assert runtime_not_statically_identified({"task.read"}, {"task.read", "network.egress"}) == {
        "network.egress"
    }


def test_runtime_not_statically_identified_empty_when_matching():
    assert runtime_not_statically_identified({"task.read", "network.egress"}, {"task.read"}) == set()


# ---------------------------------------------------------------------------
# 5. S - R
# ---------------------------------------------------------------------------


def test_statically_identified_not_observed_reports_difference():
    assert statically_identified_not_observed({"task.read", "network.egress"}, {"task.read"}) == {
        "network.egress"
    }


def test_statically_identified_not_observed_empty_when_fully_exercised():
    assert statically_identified_not_observed({"task.read"}, {"task.read", "network.egress"}) == set()


# ---------------------------------------------------------------------------
# 6. R ∩ D — ordinary set intersection, no dedicated function
# ---------------------------------------------------------------------------


def test_runtime_intersect_declared_is_plain_set_intersection():
    observed = {"task.read", "network.egress"}
    declared = {"task.read", "process.execute"}
    assert observed & declared == {"task.read"}


# ---------------------------------------------------------------------------
# 7. R ∩ P — ordinary set intersection, no dedicated function
# ---------------------------------------------------------------------------


def test_runtime_intersect_policy_is_plain_set_intersection():
    observed = {"task.read", "process.execute"}
    policy = {"task.read"}
    assert observed & policy == {"task.read"}
    assert policy_violating_capabilities(policy, observed) == {"process.execute"}


# ---------------------------------------------------------------------------
# static_capability_set / runtime_capability_set helpers
# ---------------------------------------------------------------------------


def test_static_capability_set_ignores_non_static_evidence():
    declaration_evidence = Evidence(source=EvidenceSource.DECLARATION, skill_id="s", data={})
    static_evidence = _static_evidence("s", "network.egress")
    assert static_capability_set([declaration_evidence, static_evidence]) == {"network.egress"}


def test_runtime_capability_set_deduplicates():
    events = [_event("task.read", "e1"), _event("task.read", "e2")]
    assert runtime_capability_set(events) == {"task.read"}


# ---------------------------------------------------------------------------
# correlate() — Finding generation and evidence attribution
# ---------------------------------------------------------------------------


def test_correlate_produces_undeclared_capability_from_static_mismatch():
    static_evidence = [_static_evidence("s", "network.egress", location=10)]
    findings = correlate("s", declared={"task.read"}, static_evidence=static_evidence, events=[])

    assert len(findings) == 1
    assert findings[0].reason_code is ReasonCode.UNDECLARED_CAPABILITY
    assert findings[0].capabilities == ("network.egress",)
    assert findings[0].evidence_refs == ("static:s:skill.py:10:x",)


def test_correlate_produces_undeclared_capability_from_runtime_mismatch():
    """With no static evidence at all, an observed-but-undeclared capability is
    correctly reported as BOTH an undeclared capability (R - D) AND a
    static/runtime mismatch (R - S, since S is empty here) — these are
    independent, genuinely overlapping comparisons, not duplicates."""
    events = [_event("process.execute", "evt-1", skill_id="s")]
    findings = correlate("s", declared={"task.read"}, static_evidence=[], events=events)

    by_reason = {f.reason_code: f for f in findings}
    assert set(by_reason) == {ReasonCode.UNDECLARED_CAPABILITY, ReasonCode.STATIC_RUNTIME_MISMATCH}
    assert by_reason[ReasonCode.UNDECLARED_CAPABILITY].capabilities == ("process.execute",)
    assert by_reason[ReasonCode.UNDECLARED_CAPABILITY].evidence_refs == ("evt-1",)
    assert by_reason[ReasonCode.STATIC_RUNTIME_MISMATCH].capabilities == ("process.execute",)


def test_correlate_produces_static_runtime_mismatch():
    """R - S ≠ ∅: observed at runtime, not identified statically."""
    static_evidence = [_static_evidence("s", "task.read")]
    events = [_event("task.read", "evt-1", skill_id="s"), _event("network.egress", "evt-2", skill_id="s")]

    findings = correlate("s", declared={"task.read", "network.egress"},
                          static_evidence=static_evidence, events=events)

    mismatch = [f for f in findings if f.reason_code is ReasonCode.STATIC_RUNTIME_MISMATCH]
    assert len(mismatch) == 1
    assert mismatch[0].capabilities == ("network.egress",)
    assert mismatch[0].evidence_refs == ("evt-2",)


def test_correlate_produces_policy_violation_when_policy_given():
    events = [_event("process.execute", "evt-1", skill_id="s")]
    findings = correlate("s", declared={"task.read", "process.execute"}, static_evidence=[],
                          events=events, policy={"task.read"})

    violations = [f for f in findings if f.reason_code is ReasonCode.POLICY_VIOLATION]
    assert len(violations) == 1
    assert violations[0].capabilities == ("process.execute",)


def test_correlate_produces_no_findings_when_fully_conformant():
    static_evidence = [_static_evidence("s", "task.read")]
    events = [_event("task.read", "evt-1", skill_id="s")]

    findings = correlate("s", declared={"task.read"}, static_evidence=static_evidence, events=events)

    assert findings == []


def test_correlate_never_claims_maliciousness():
    """A Finding only ever states a standardized fact, never a verdict."""
    static_evidence = [_static_evidence("s", "network.egress")]
    findings = correlate("s", declared={"task.read"}, static_evidence=static_evidence, events=[])

    for finding in findings:
        assert "malicious" not in finding.description.lower()
        assert "attack" not in finding.description.lower()
