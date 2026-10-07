"""Findings -> Recommendation mapping (docs/product-spec.md §19;
docs/conformance-rules.md).
"""

from __future__ import annotations

from skillshield.core.models.assessment import Recommendation
from skillshield.core.models.finding import Finding, Severity, severity_rank

_HIGH_TIER = (Severity.HIGH, Severity.CRITICAL)


def recommend(findings: tuple[Finding, ...]) -> Recommendation:
    """Map a Finding tuple to a Recommendation by maximum severity.

    No findings                -> NO_ISSUES_FOUND
    Max severity LOW/MEDIUM    -> REVIEW_BEFORE_USE
    Max severity HIGH/CRITICAL -> DO_NOT_USE
    """
    if not findings:
        return Recommendation.NO_ISSUES_FOUND
    max_severity = max(findings, key=lambda f: severity_rank(f.severity)).severity
    if max_severity in _HIGH_TIER:
        return Recommendation.DO_NOT_USE
    return Recommendation.REVIEW_BEFORE_USE
