"""Tests for Assessment aggregation and rendering (second milestone, Phase 7)."""

from __future__ import annotations

from agentic_conformance.core.conformance.assessment import build_assessment, format_assessment
from agentic_conformance.core.models import (
    Action,
    Actor,
    Capability,
    Decision,
    DecisionValue,
    Evidence,
    EvidenceSource,
    ReasonCode,
    SecurityEvent,
    Severity,
    Target,
)
from agentic_conformance.core.models.finding import Finding


def _event(capability: str, event_id: str) -> SecurityEvent:
    return SecurityEvent(
        event_id=event_id,
        timestamp="2026-10-06T00:00:00Z",
        event_type=capability,
        context={"skill_id": "s"},
        actor=Actor(type="skill", id="s"),
        action=Action(capability=Capability(capability), operation="invoke"),
        target=Target(type="resource", identifier="x"),
    )


def test_build_assessment_aggregates_every_field():
    static_evidence = [
        Evidence(source=EvidenceSource.STATIC, skill_id="s",
                  data={"capability": "network.egress", "file": "skill.py", "location": 5,
                        "detector": "net-broker-call", "description": "x"})
    ]
    events = [_event("task.read", "e1"), _event("network.egress", "e2")]
    finding = Finding(
        reason_code=ReasonCode.UNDECLARED_CAPABILITY,
        capabilities=("network.egress",),
        evidence_refs=("e2",),
        description="x",
    )
    decision = Decision(skill_id="s", value=DecisionValue.FLAG, reason_code=ReasonCode.UNDECLARED_CAPABILITY)

    assessment = build_assessment(
        skill_id="s", skill_name="S", skill_version="1.0.0", source="vuln_agentic_skills_app",
        declared_capabilities={"task.read"}, static_evidence=static_evidence, events=events,
        findings=[finding], decision=decision, policy_results={}, severity=Severity.MEDIUM,
    )

    assert assessment.skill_id == "s"
    assert assessment.declared_capabilities == ("task.read",)
    assert assessment.static_capabilities == ("network.egress",)
    assert assessment.runtime_capabilities == ("network.egress", "task.read")
    assert assessment.findings == (finding,)
    assert assessment.decision is decision
    assert assessment.severity is Severity.MEDIUM
    assert assessment.recommendation == "REVIEW BEFORE USE"  # FLAG + MEDIUM


def test_build_assessment_recommendation_mapping_is_fixed_and_deterministic():
    decision = Decision(skill_id="s", value=DecisionValue.ALLOW)
    assessment = build_assessment(
        skill_id="s", skill_name="S", skill_version="1.0.0", source="x",
        declared_capabilities={"task.read"}, static_evidence=[], events=[],
        findings=[], decision=decision, policy_results={}, severity=Severity.LOW,
    )
    assert assessment.recommendation == "NO ISSUES FOUND"


def test_build_assessment_includes_policy_results():
    decision = Decision(skill_id="s", value=DecisionValue.DENY, reason_code=ReasonCode.POLICY_VIOLATION)
    assessment = build_assessment(
        skill_id="s", skill_name="S", skill_version="1.0.0", source="x",
        declared_capabilities={"process.execute"}, static_evidence=[], events=[],
        findings=[], decision=decision,
        policy_results={"process.execute": DecisionValue.DENY}, severity=Severity.HIGH,
    )
    assert assessment.policy_results == ({"capability": "process.execute", "effect": "DENY"},)
    assert assessment.recommendation == "DO NOT USE"


def test_format_assessment_contains_required_sections():
    decision = Decision(skill_id="s", value=DecisionValue.ALLOW)
    assessment = build_assessment(
        skill_id="s", skill_name="Test Skill", skill_version="1.0.0", source="x",
        declared_capabilities={"task.read"}, static_evidence=[], events=[],
        findings=[], decision=decision, policy_results={}, severity=Severity.LOW,
    )

    text = format_assessment(assessment)

    assert "Test Skill" in text
    assert "Declared:" in text
    assert "Static findings:" in text
    assert "Runtime findings:" in text
    assert "Findings:" in text
    assert "Conformance decision:" in text
    assert "Severity:" in text
    assert "Recommendation:" in text
