"""Second-milestone end-to-end walkthrough (docs/downloaded-skill-assessment-spec.md;
docs/downloaded-skill-assessment-plan.md Phases 1-7).

Demonstrates the complete real pipeline:

    Real Skill (vuln-agentic-skills-app)
        -> vuln_agentic_skills_app Adapter
        -> Canonical Skill / D
        -> Static Analysis -> STATIC Evidence / S
        -> Controlled Execution -> Runtime Monitoring -> SecurityEvents / R
        -> D/S/R Correlation -> Finding(s)
        -> Policy + Severity
        -> Assessment -> rendered report

against two real, vendored skills from the testbed (see
tests/fixtures/vuln_agentic_skills_app/README.md for provenance): the
"honest" `task_summary` skill (a clean ALLOW) and the "lying" `task_insights`
skill (a genuine UNDECLARED_CAPABILITY).

Run with:

    uv run python examples/skillshield_assessment_walkthrough.py
"""

from __future__ import annotations

from pathlib import Path

from agentic_conformance.adapters.vuln_agentic_skills_app import VulnAgenticSkillsAppAdapter
from agentic_conformance.adapters.vuln_agentic_skills_app.adapter import (
    load_manifest,
    resolve_entrypoint,
)
from agentic_conformance.analysis.runtime.monitor import monitor_and_emit
from agentic_conformance.analysis.static import analyze, static_findings_to_evidence
from agentic_conformance.core.conformance.assessment import build_assessment, format_assessment
from agentic_conformance.core.conformance.correlation import correlate
from agentic_conformance.core.conformance.engine import ConformanceEngine
from agentic_conformance.core.conformance.severity import classify_severity
from agentic_conformance.execution.subprocess_sandbox import execute

_FIXTURES_ROOT = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "vuln_agentic_skills_app"
)


def assess_real_skill(skill_dir_name: str) -> str:
    """Run the full real pipeline for one vendored real skill and return its
    rendered Assessment."""
    skill_dir = _FIXTURES_ROOT / skill_dir_name
    engine = ConformanceEngine()
    adapter = VulnAgenticSkillsAppAdapter(engine)

    skill = adapter.translate_skill(skill_dir)
    adapter.register(skill_dir)
    declared = {c.identifier for c in skill.declaration.declared_capabilities}

    static_findings = analyze(skill_dir)
    static_evidence = static_findings_to_evidence(skill.skill_id, static_findings)

    manifest = load_manifest(skill_dir)
    entry_file, entry_attr = resolve_entrypoint(skill_dir, manifest)
    handle = execute(skill.skill_id, entry_file, entry_attr, {})
    events = monitor_and_emit(adapter, handle) if handle.outcome == "ok" else []

    findings = correlate(skill.skill_id, declared, static_evidence, events)
    decision = adapter.evaluate(skill.skill_id)
    severity = classify_severity(decision, findings)

    assessment = build_assessment(
        skill_id=skill.skill_id, skill_name=skill.name, skill_version=skill.version,
        source=skill.source, declared_capabilities=declared, static_evidence=static_evidence,
        events=events, findings=findings, decision=decision, policy_results={}, severity=severity,
    )
    return format_assessment(assessment)


def main() -> None:
    for skill_dir_name in ("task_summary", "task_insights"):
        print("=" * 72)
        print(assess_real_skill(skill_dir_name))
        print()


if __name__ == "__main__":
    main()
