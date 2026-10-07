"""Tests for deterministic severity classification (second milestone, Phase 6)."""

from __future__ import annotations

from agentic_conformance.core.conformance.severity import classify_severity
from agentic_conformance.core.models import Decision, DecisionValue, ReasonCode, Severity
from agentic_conformance.core.models.finding import Finding


def _finding(reason_code: ReasonCode) -> Finding:
    return Finding(
        reason_code=reason_code, capabilities=("x",), evidence_refs=("y",), description="z"
    )


def test_clean_allow_with_no_findings_is_low():
    decision = Decision(skill_id="s", value=DecisionValue.ALLOW)
    assert classify_severity(decision, []) is Severity.LOW


def test_policy_violation_finding_is_high():
    decision = Decision(skill_id="s", value=DecisionValue.DENY, reason_code=ReasonCode.POLICY_VIOLATION)
    findings = [_finding(ReasonCode.POLICY_VIOLATION)]
    assert classify_severity(decision, findings) is Severity.HIGH


def test_integrity_failure_is_high():
    decision = Decision(skill_id="s", value=DecisionValue.DENY, reason_code=ReasonCode.INTEGRITY_FAILURE)
    assert classify_severity(decision, []) is Severity.HIGH


def test_undeclared_capability_without_policy_violation_is_medium():
    decision = Decision(skill_id="s", value=DecisionValue.FLAG, reason_code=ReasonCode.UNDECLARED_CAPABILITY)
    findings = [_finding(ReasonCode.UNDECLARED_CAPABILITY)]
    assert classify_severity(decision, findings) is Severity.MEDIUM


def test_static_runtime_mismatch_without_policy_violation_is_medium():
    decision = Decision(skill_id="s", value=DecisionValue.ALLOW)
    findings = [_finding(ReasonCode.STATIC_RUNTIME_MISMATCH)]
    assert classify_severity(decision, findings) is Severity.MEDIUM


def test_policy_violation_outranks_medium_findings():
    """Multiple findings with mixed severities -> HIGH wins (deterministic, not averaged)."""
    decision = Decision(skill_id="s", value=DecisionValue.DENY, reason_code=ReasonCode.POLICY_VIOLATION)
    findings = [_finding(ReasonCode.UNDECLARED_CAPABILITY), _finding(ReasonCode.POLICY_VIOLATION)]
    assert classify_severity(decision, findings) is Severity.HIGH


def test_structural_deny_reason_codes_are_high():
    for reason in (
        ReasonCode.INVALID_DECLARATION,
        ReasonCode.MISSING_DECLARATION,
        ReasonCode.INVALID_EVENT,
        ReasonCode.UNKNOWN_CAPABILITY,
    ):
        decision = Decision(skill_id="s", value=DecisionValue.DENY, reason_code=reason)
        assert classify_severity(decision, []) is Severity.HIGH
