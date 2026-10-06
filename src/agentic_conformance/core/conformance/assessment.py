"""Assessment aggregation and minimal textual rendering (second milestone,
Phase 7; docs/downloaded-skill-assessment-spec.md §10.3, §10.6).

`build_assessment` consumes only canonical objects already produced by
earlier phases — it never re-derives D/S/R itself and never reaches into
adapter-, analyzer-, or execution-specific internals
(docs/downloaded-skill-assessment-plan.md §14 architectural boundary
check 7: "report generation consumes canonical findings/assessment").
"""

from __future__ import annotations

from agentic_conformance.core.conformance.correlation import (
    runtime_capability_set,
    static_capability_set,
)
from agentic_conformance.core.models import (
    Decision,
    DecisionValue,
    Evidence,
    SecurityEvent,
    Severity,
)
from agentic_conformance.core.models.assessment import Assessment
from agentic_conformance.core.models.finding import Finding

#: Fixed, deterministic (decision, severity) -> recommendation mapping.
#: Never freeform/generated text (spec §10.3).
_RECOMMENDATION_MAP: dict[tuple[DecisionValue, Severity], str] = {
    (DecisionValue.ALLOW, Severity.LOW): "NO ISSUES FOUND",
    (DecisionValue.ALLOW, Severity.MEDIUM): "REVIEW BEFORE USE",
    (DecisionValue.ALLOW, Severity.HIGH): "REVIEW BEFORE USE",
    (DecisionValue.FLAG, Severity.LOW): "REVIEW BEFORE USE",
    (DecisionValue.FLAG, Severity.MEDIUM): "REVIEW BEFORE USE",
    (DecisionValue.FLAG, Severity.HIGH): "DO NOT USE",
    (DecisionValue.DENY, Severity.LOW): "DO NOT USE",
    (DecisionValue.DENY, Severity.MEDIUM): "DO NOT USE",
    (DecisionValue.DENY, Severity.HIGH): "DO NOT USE",
}


def _recommendation_for(decision: Decision, severity: Severity) -> str:
    return _RECOMMENDATION_MAP[(decision.value, severity)]


def build_assessment(
    skill_id: str,
    skill_name: str,
    skill_version: str,
    source: str,
    declared_capabilities: set[str],
    static_evidence: list[Evidence],
    events: list[SecurityEvent],
    findings: list[Finding],
    decision: Decision,
    policy_results: dict[str, DecisionValue],
    severity: Severity,
) -> Assessment:
    """Aggregate one skill's declaration, evidence, findings, decision,
    policy results, and severity into one canonical Assessment."""
    static_capabilities = static_capability_set(static_evidence)
    runtime_capabilities = runtime_capability_set(events)

    return Assessment(
        skill_id=skill_id,
        skill_name=skill_name,
        skill_version=skill_version,
        source=source,
        declared_capabilities=tuple(sorted(declared_capabilities)),
        static_capabilities=tuple(sorted(static_capabilities)),
        runtime_capabilities=tuple(sorted(runtime_capabilities)),
        findings=tuple(findings),
        policy_results=tuple(
            {"capability": capability, "effect": effect.value}
            for capability, effect in sorted(policy_results.items())
        ),
        decision=decision,
        severity=severity,
        recommendation=_recommendation_for(decision, severity),
    )


def format_assessment(assessment: Assessment) -> str:
    """A minimal, deterministic textual rendering — no templating engine,
    no HTML, no frontend (spec §10.6: report format is explicitly
    unfrozen; a minimal unstyled rendering is sufficient for this
    milestone)."""
    lines = [
        f"Skill: {assessment.skill_name}",
        f"Version: {assessment.skill_version}",
        f"Source: {assessment.source}",
        "",
        f"Declared: {', '.join(assessment.declared_capabilities) or '(none)'}",
        f"Static findings: {', '.join(assessment.static_capabilities) or '(none)'}",
        f"Runtime findings: {', '.join(assessment.runtime_capabilities) or '(none)'}",
        "",
    ]
    if assessment.findings:
        lines.append("Findings:")
        for finding in assessment.findings:
            lines.append(
                f"  - {finding.reason_code.value}: {', '.join(finding.capabilities)} "
                f"({finding.description})"
            )
    else:
        lines.append("Findings: (none)")

    if assessment.policy_results:
        lines.append("")
        lines.append("Policy:")
        for result in assessment.policy_results:
            lines.append(f"  - {result['capability']} -> {result['effect']}")

    lines += [
        "",
        f"Conformance decision: {assessment.decision.value.value}"
        + (f" ({assessment.decision.reason_code.value})" if assessment.decision.reason_code else ""),
        f"Severity: {assessment.severity.value}",
        f"Recommendation: {assessment.recommendation}",
    ]
    return "\n".join(lines)
