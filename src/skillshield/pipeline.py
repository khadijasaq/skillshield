"""The SkillShield application interface (docs/product-spec.md §23;
docs/product-plan.md P5).

One synchronous entry point that runs the complete pipeline -- ingestion,
declaration, static analysis, controlled execution, D/S/R/P correlation,
findings, and the final recommendation -- and returns a single ``Assessment``.
Per the decision already recorded in DECISIONS.md ("P5/P6"), this is a plain
synchronous call rather than a submit/poll/retrieve job model: the prototype's
assessments complete well inside any UI's own timeout, and a synchronous call
satisfies every acceptance criterion without speculative job-queue machinery.

This module is glue only. It does not re-implement anything that
``skillshield.ingestion``, ``skillshield.analysis.static``,
``skillshield.execution``, ``skillshield.policy``, or
``skillshield.conformance`` already do.

Error handling: a fatal ingestion problem (``skillshield.ingestion.IngestionError``
and its subclasses) and a bad policy file (``skillshield.policy.errors.PolicyLoadError``)
both propagate unchanged out of ``assess()``. Neither is turned into an
``Assessment`` with some synthetic "failed" recommendation -- there is no
``Skill`` identity to hang one on in the ingestion case, and a bad policy
*file* is an operator configuration mistake, not something about the skill
being assessed. Callers (the CLI, and later the UI) must catch these
separately from a normally-returned ``Assessment`` and report "could not be
assessed" rather than blending that into a completed assessment's
recommendation -- these are different kinds of outcome.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from skillshield.analysis.static import analyze
from skillshield.conformance.assessment import recommend
from skillshield.conformance.engine import build_findings
from skillshield.core.models.assessment import Assessment, CapabilitySummary
from skillshield.execution.result import ExecutionStatus
from skillshield.execution.sandbox import execute
from skillshield.ingestion import ingest
from skillshield.policy.loader import load_policy

_STANDING_LIMITATION = (
    "Static evidence indicates possible behavior, not proof it occurs. "
    "Runtime evidence reflects only this one controlled execution; its "
    "absence does not prove a capability can never occur."
)

_EXECUTION_STATUS_LIMITATIONS = {
    ExecutionStatus.TIMEOUT: (
        "Controlled execution timed out before completing. Runtime evidence "
        "collected before the timeout is included, but is likely incomplete."
    ),
    ExecutionStatus.CRASHED: (
        "The skill's entrypoint crashed during controlled execution. Runtime "
        "evidence collected before the crash is included, but is likely incomplete."
    ),
    ExecutionStatus.NO_ENTRYPOINT: (
        "No usable entrypoint could be resolved, so controlled execution did "
        "not run at all. There is no runtime evidence for this skill."
    ),
}


def assess(
    input_path: str | Path,
    *,
    policy_path: str | Path | None = None,
    timeout_seconds: float = 10.0,
) -> Assessment:
    """Run the complete SkillShield pipeline over one downloaded skill and
    return its final ``Assessment``.

    ``input_path`` may be a local directory or a ZIP archive (the two
    supported input forms, per docs/product-spec.md §6). Raises an
    ``IngestionError`` subclass if the input is unsafe/invalid to analyze,
    or ``PolicyLoadError`` if ``policy_path`` names a malformed policy file --
    see the module docstring for why these are not folded into a returned
    ``Assessment``.
    """
    artifact, skill = ingest(input_path)

    static_result = analyze(skill, artifact)
    execution_result = execute(skill, artifact, timeout_seconds=timeout_seconds)
    policy = load_policy(policy_path)

    execution_failures = (
        (execution_result.failure_reason,) if execution_result.failure_reason else ()
    )

    findings = build_findings(
        declared=skill.declared_capability_ids(),
        static=static_result.capabilities,
        runtime=execution_result.runtime_capabilities,
        policy=policy,
        declaration_problem=skill.declaration_problem,
        static_evidence=static_result.evidence,
        analysis_failures=static_result.analysis_failures,
        runtime_evidence=execution_result.events,
        execution_failures=execution_failures,
    )
    recommendation = recommend(findings)

    limitations: list[str] = [_STANDING_LIMITATION]
    status_limitation = _EXECUTION_STATUS_LIMITATIONS.get(execution_result.status)
    if status_limitation is not None:
        limitations.append(status_limitation)
    if static_result.analysis_failures:
        limitations.append(
            "Static analysis could not fully parse one or more source files; "
            "static coverage for this skill may be incomplete "
            f"({len(static_result.analysis_failures)} file(s) affected)."
        )
    if skill.declaration_problem is not None:
        limitations.append(
            f"Declaration problem ({skill.declaration_problem.kind}): "
            f"{skill.declaration_problem.detail}. Declared capabilities may be "
            "incomplete or absent as a result."
        )

    return Assessment(
        skill_id=skill.skill_id,
        skill_name=skill.name,
        skill_version=skill.version,
        recommendation=recommendation,
        capabilities=CapabilitySummary(
            declared=skill.declared_capability_ids(),
            static=static_result.capabilities,
            runtime=execution_result.runtime_capabilities,
            policy_permitted=policy.permitted_capabilities,
        ),
        findings=findings,
        limitations=tuple(limitations),
        artifact_digest=artifact.content_digest,
        policy_name=policy.name,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def assessment_to_jsonable(assessment: Assessment) -> dict:
    """Manual, dependency-free JSON-serializable rendering of an Assessment
    (enums -> their .value, frozensets -> sorted lists, nested dataclasses ->
    dicts). No new runtime dependency for this; dataclasses.asdict() alone
    does not handle Enum/frozenset the way we want for clean JSON output.

    Shared by the CLI's ``--json`` output and the UI's ``/api/assess``
    response, so there is exactly one Assessment -> JSON rendering in the
    whole project.
    """

    def evidence_jsonable(evidence):
        return [
            {"source": e.source.value, "capability": e.capability, "detail": e.detail}
            for e in evidence
        ]

    def finding_jsonable(f):
        return {
            "finding_type": f.finding_type.value,
            "severity": f.severity.value,
            "capability": f.capability,
            "explanation": f.explanation,
            "source_location": f.source_location,
            "policy_info": (
                {"policy_name": f.policy_info.policy_name, "permitted": f.policy_info.permitted}
                if f.policy_info is not None
                else None
            ),
            "evidence": evidence_jsonable(f.evidence),
        }

    return {
        "skill_id": assessment.skill_id,
        "skill_name": assessment.skill_name,
        "skill_version": assessment.skill_version,
        "recommendation": assessment.recommendation.value,
        "capabilities": {
            "declared": sorted(assessment.capabilities.declared),
            "static": sorted(assessment.capabilities.static),
            "runtime": sorted(assessment.capabilities.runtime),
            "policy_permitted": sorted(assessment.capabilities.policy_permitted),
        },
        "findings": [finding_jsonable(f) for f in assessment.findings],
        "limitations": list(assessment.limitations),
        "artifact_digest": assessment.artifact_digest,
        "policy_name": assessment.policy_name,
        "generated_at": assessment.generated_at,
    }
