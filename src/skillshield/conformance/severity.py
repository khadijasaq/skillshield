"""Deterministic severity rules (docs/conformance-rules.md).

The exact rule table lives in docs/conformance-rules.md; this module is its
executable form and must stay in sync with that document.
"""

from __future__ import annotations

from skillshield.core.models.finding import FindingType, Severity


def classify(
    finding_type: FindingType,
    *,
    runtime_confirmed: bool = False,
    also_undeclared: bool = False,
) -> Severity:
    """Classify the severity of a single finding.

    See docs/conformance-rules.md for the authoritative table this
    implements:

        POLICY_VIOLATION        -> CRITICAL if also_undeclared else HIGH
        UNDECLARED_CAPABILITY   -> HIGH if runtime_confirmed else MEDIUM
        STATIC_RUNTIME_MISMATCH -> LOW
        INVALID_DECLARATION     -> MEDIUM
        ANALYSIS_FAILURE        -> LOW
        EXECUTION_FAILURE       -> LOW
    """
    if finding_type is FindingType.POLICY_VIOLATION:
        return Severity.CRITICAL if also_undeclared else Severity.HIGH
    if finding_type is FindingType.UNDECLARED_CAPABILITY:
        return Severity.HIGH if runtime_confirmed else Severity.MEDIUM
    if finding_type is FindingType.STATIC_RUNTIME_MISMATCH:
        return Severity.LOW
    if finding_type is FindingType.INVALID_DECLARATION:
        return Severity.MEDIUM
    if finding_type in (FindingType.ANALYSIS_FAILURE, FindingType.EXECUTION_FAILURE):
        return Severity.LOW
    raise ValueError(f"No severity rule defined for finding type: {finding_type!r}")
