"""Real-data integration test for Assessment aggregation (second milestone,
Phase 7). Runs the full real pipeline for `task_insights` and builds a
complete, canonical Assessment from genuine evidence."""

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
from agentic_conformance.core.models import DecisionValue, ReasonCode, Severity
from agentic_conformance.execution.subprocess_sandbox import execute

_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "vuln_agentic_skills_app"
    / "task_insights"
)


def test_real_task_insights_full_assessment():
    engine = ConformanceEngine()
    adapter = VulnAgenticSkillsAppAdapter(engine)

    skill = adapter.translate_skill(_FIXTURE_DIR)
    adapter.register(_FIXTURE_DIR)
    declared = {c.identifier for c in skill.declaration.declared_capabilities}

    static_findings = analyze(_FIXTURE_DIR)
    static_evidence = static_findings_to_evidence(skill.skill_id, static_findings)

    manifest = load_manifest(_FIXTURE_DIR)
    entry_file, entry_attr = resolve_entrypoint(_FIXTURE_DIR, manifest)
    handle = execute(skill.skill_id, entry_file, entry_attr, {})
    assert handle.outcome == "ok"
    events = monitor_and_emit(adapter, handle)

    findings = correlate(skill.skill_id, declared, static_evidence, events)
    decision = adapter.evaluate(skill.skill_id)
    severity = classify_severity(decision, findings)

    assessment = build_assessment(
        skill_id=skill.skill_id, skill_name=skill.name, skill_version=skill.version,
        source=skill.source, declared_capabilities=declared, static_evidence=static_evidence,
        events=events, findings=findings, decision=decision, policy_results={}, severity=severity,
    )

    assert assessment.skill_id == "task_insights"
    assert assessment.declared_capabilities == ("task.read",)
    assert set(assessment.static_capabilities) == {"task.read", "filesystem.read", "network.egress"}
    assert set(assessment.runtime_capabilities) == {"task.read", "filesystem.read", "network.egress"}
    assert decision.value is DecisionValue.FLAG
    assert decision.reason_code is ReasonCode.UNDECLARED_CAPABILITY
    assert assessment.severity is Severity.MEDIUM
    assert assessment.recommendation == "REVIEW BEFORE USE"
    assert len(assessment.findings) >= 1
    assert any(f.reason_code is ReasonCode.UNDECLARED_CAPABILITY for f in assessment.findings)

    rendered = format_assessment(assessment)
    assert "Task Insights" in rendered
    assert "UNDECLARED_CAPABILITY" in rendered
