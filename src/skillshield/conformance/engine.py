"""Conformance engine: turns D/S/R/P capability sets into Finding objects
(docs/product-spec.md §17, §18; docs/conformance-rules.md).

This module performs the five required correlations (S-D, R-D, S-R, R-S,
R-P) and attaches evidence and severity to each resulting Finding. It does
not know how D/S/R/P were produced -- that is ingestion's (D), static
analysis's (S), and controlled execution's (R) responsibility, arriving in
later batches.
"""

from __future__ import annotations

from skillshield.conformance import correlation, severity
from skillshield.core.models.evidence import Evidence, EvidenceSource
from skillshield.core.models.finding import Finding, FindingType, PolicyInfo
from skillshield.core.models.policy import SecurityPolicy
from skillshield.core.models.skill import DeclarationProblem


def _explain_undeclared(capability: str, *, static: bool, runtime: bool) -> str:
    return (
        f"Capability '{capability}' was not declared. "
        f"Declared: no. Static: {'yes' if static else 'no'}. "
        f"Runtime: {'yes' if runtime else 'no'}."
    )


def _static_evidence_for(
    capability: str, static_evidence: tuple[Evidence, ...]
) -> tuple[Evidence, ...]:
    """Real static evidence for a capability, or a bare fallback Evidence
    when none was supplied (Batch 1 synthetic-set callers)."""
    matches = tuple(e for e in static_evidence if e.capability == capability)
    return matches if matches else (Evidence(EvidenceSource.STATIC, capability),)


def _runtime_evidence_for(
    capability: str, runtime_evidence: tuple[Evidence, ...]
) -> tuple[Evidence, ...]:
    """Real runtime evidence for a capability, or a bare fallback Evidence
    when none was supplied (Batch 1/2 synthetic-set callers)."""
    matches = tuple(e for e in runtime_evidence if e.capability == capability)
    return matches if matches else (Evidence(EvidenceSource.RUNTIME, capability),)


def build_findings(
    *,
    declared: frozenset[str],
    static: frozenset[str],
    runtime: frozenset[str],
    policy: SecurityPolicy | None = None,
    declaration_problem: DeclarationProblem | None = None,
    static_evidence: tuple[Evidence, ...] = (),
    analysis_failures: tuple[str, ...] = (),
    runtime_evidence: tuple[Evidence, ...] = (),
    execution_failures: tuple[str, ...] = (),
) -> tuple[Finding, ...]:
    """Produce the Finding list for one skill from its D/S/R/P capability sets.

    ``declared``/``static``/``runtime`` are plain capability-identifier
    sets. ``policy`` is optional -- when absent, no POLICY_VIOLATION
    findings are produced (there is nothing to violate). ``static_evidence``
    carries real file/line/detector detail from ``analysis.static.analyze``
    (optional -- when a capability has no matching entry, a bare Evidence is
    used instead, which is what Batch 1's synthetic-set tests still rely on).
    Each entry in ``analysis_failures`` becomes one ANALYSIS_FAILURE finding.
    ``runtime_evidence`` is the analogous real-detail source from
    ``execution.sandbox.execute``; each entry in ``execution_failures``
    becomes one EXECUTION_FAILURE finding.
    """
    findings: list[Finding] = []

    runtime_undeclared = correlation.undeclared_runtime(declared, runtime)
    static_undeclared = correlation.undeclared_static(declared, static) - runtime_undeclared

    violations: frozenset[str] = frozenset()
    if policy is not None:
        violations = correlation.policy_violations(runtime, policy.permitted_capabilities)

    for capability in sorted(runtime_undeclared):
        findings.append(
            Finding(
                finding_type=FindingType.UNDECLARED_CAPABILITY,
                severity=severity.classify(
                    FindingType.UNDECLARED_CAPABILITY, runtime_confirmed=True
                ),
                capability=capability,
                explanation=_explain_undeclared(
                    capability, static=capability in static, runtime=True
                ),
                evidence=_runtime_evidence_for(capability, runtime_evidence),
            )
        )

    for capability in sorted(static_undeclared):
        findings.append(
            Finding(
                finding_type=FindingType.UNDECLARED_CAPABILITY,
                severity=severity.classify(
                    FindingType.UNDECLARED_CAPABILITY, runtime_confirmed=False
                ),
                capability=capability,
                explanation=_explain_undeclared(capability, static=True, runtime=False),
                evidence=_static_evidence_for(capability, static_evidence),
            )
        )

    for capability in sorted(correlation.runtime_only(static, runtime)):
        findings.append(
            Finding(
                finding_type=FindingType.STATIC_RUNTIME_MISMATCH,
                severity=severity.classify(FindingType.STATIC_RUNTIME_MISMATCH),
                capability=capability,
                explanation=(
                    f"Capability '{capability}' was observed at runtime but was not "
                    "indicated by static analysis."
                ),
                evidence=_runtime_evidence_for(capability, runtime_evidence),
            )
        )

    for capability in sorted(correlation.static_only(static, runtime)):
        findings.append(
            Finding(
                finding_type=FindingType.STATIC_RUNTIME_MISMATCH,
                severity=severity.classify(FindingType.STATIC_RUNTIME_MISMATCH),
                capability=capability,
                explanation=(
                    f"Capability '{capability}' is indicated by static analysis but was "
                    "not observed during this controlled execution. This does not prove "
                    "the capability can never occur."
                ),
                evidence=_static_evidence_for(capability, static_evidence),
            )
        )

    if policy is not None:
        for capability in sorted(violations):
            also_undeclared = capability in runtime_undeclared
            findings.append(
                Finding(
                    finding_type=FindingType.POLICY_VIOLATION,
                    severity=severity.classify(
                        FindingType.POLICY_VIOLATION, also_undeclared=also_undeclared
                    ),
                    capability=capability,
                    explanation=(
                        f"Capability '{capability}' was observed at runtime but is denied "
                        f"by policy '{policy.name}'."
                    ),
                    evidence=(Evidence(EvidenceSource.POLICY, capability),),
                    policy_info=PolicyInfo(policy.name, permitted=False),
                )
            )

    if declaration_problem is not None:
        findings.append(
            Finding(
                finding_type=FindingType.INVALID_DECLARATION,
                severity=severity.classify(FindingType.INVALID_DECLARATION),
                explanation=(
                    f"Declaration problem ({declaration_problem.kind}): "
                    f"{declaration_problem.detail}"
                ),
            )
        )

    for failure in analysis_failures:
        findings.append(
            Finding(
                finding_type=FindingType.ANALYSIS_FAILURE,
                severity=severity.classify(FindingType.ANALYSIS_FAILURE),
                explanation=f"Static analysis could not complete for one file: {failure}",
            )
        )

    for failure in execution_failures:
        findings.append(
            Finding(
                finding_type=FindingType.EXECUTION_FAILURE,
                severity=severity.classify(FindingType.EXECUTION_FAILURE),
                explanation=f"Controlled execution did not complete normally: {failure}",
            )
        )

    return tuple(findings)
