"""Deterministic severity classification (second milestone, Phase 6;
docs/downloaded-skill-assessment-spec.md §10.5).

A fixed, closed mapping from `Decision` + `Finding`s to one of
`LOW`/`MEDIUM`/`HIGH` — no probabilistic scoring, no ML, no LLM, no
numeric risk value, per this batch's explicit instructions.
"""

from __future__ import annotations

from agentic_conformance.core.models import Decision, ReasonCode, Severity
from agentic_conformance.core.models.finding import Finding

#: Reason codes that always indicate a HIGH-severity result, whether they
#: appear on the Decision itself or on a Finding.
_HIGH_SEVERITY_REASONS = frozenset(
    {
        ReasonCode.POLICY_VIOLATION,
        ReasonCode.INTEGRITY_FAILURE,
        ReasonCode.INVALID_DECLARATION,
        ReasonCode.MISSING_DECLARATION,
        ReasonCode.INVALID_EVENT,
        ReasonCode.UNKNOWN_CAPABILITY,
    }
)

#: Reason codes that indicate MEDIUM severity when no HIGH-severity reason
#: is also present.
_MEDIUM_SEVERITY_REASONS = frozenset(
    {ReasonCode.UNDECLARED_CAPABILITY, ReasonCode.STATIC_RUNTIME_MISMATCH}
)


def classify_severity(decision: Decision, findings: list[Finding]) -> Severity:
    """Classify the overall severity of one evaluation.

    Rules, in order:

    1. Any HIGH-severity reason code on the Decision or on any Finding ->
       `HIGH` (policy violations, integrity failures, and every
       structural-validation DENY reason are treated as HIGH: a skill
       that could not even be evaluated correctly is not a MEDIUM
       concern).
    2. Otherwise, any MEDIUM-severity reason code on any Finding ->
       `MEDIUM` (an undeclared-capability or static/runtime mismatch,
       with no policy violation).
    3. Otherwise (a clean `ALLOW` with no findings, or any other
       unclassified case) -> `LOW`.
    """
    all_reason_codes = {f.reason_code for f in findings}
    if decision.reason_code is not None:
        all_reason_codes.add(decision.reason_code)

    if all_reason_codes & _HIGH_SEVERITY_REASONS:
        return Severity.HIGH
    if all_reason_codes & _MEDIUM_SEVERITY_REASONS:
        return Severity.MEDIUM
    return Severity.LOW
