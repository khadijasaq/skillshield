"""Second-milestone end-to-end testbed evaluation (second milestone, Phase 8;
docs/downloaded-skill-assessment-spec.md §11 step 1).

Demonstrates all six required cases using real skills from
`vuln-agentic-skills-app` (vendored verbatim fixtures — see
tests/fixtures/vuln_agentic_skills_app/README.md). No case uses a
constructed/fake skill or a second synthetic test application. Case 6
(policy violation) applies a real, assessor-side `PolicyRule` to a real
skill's genuinely observed behavior — a legitimate policy configuration,
not an alteration of what the skill does (the same technique the first
milestone's Case C already used with `set_policy`).
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
from agentic_conformance.core.conformance.assessment import build_assessment
from agentic_conformance.core.conformance.correlation import correlate
from agentic_conformance.core.conformance.engine import ConformanceEngine
from agentic_conformance.core.conformance.policy import PolicyRule
from agentic_conformance.core.conformance.severity import classify_severity
from agentic_conformance.core.models import DecisionValue, ReasonCode, Severity
from agentic_conformance.execution.subprocess_sandbox import execute

_FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "vuln_agentic_skills_app"


def _run_real_pipeline(skill_dir_name: str, engine: ConformanceEngine | None = None):
    """Run the full real Phase 1-4 pipeline for one vendored real skill.

    Returns (adapter, engine, skill, declared, static_evidence, events).
    """
    engine = engine or ConformanceEngine()
    adapter = VulnAgenticSkillsAppAdapter(engine)
    skill_dir = _FIXTURES_ROOT / skill_dir_name

    skill = adapter.translate_skill(skill_dir)
    adapter.register(skill_dir)
    declared = {c.identifier for c in skill.declaration.declared_capabilities}

    static_findings = analyze(skill_dir)
    static_evidence = static_findings_to_evidence(skill.skill_id, static_findings)

    manifest = load_manifest(skill_dir)
    entry_file, entry_attr = resolve_entrypoint(skill_dir, manifest)
    handle = execute(skill.skill_id, entry_file, entry_attr, {})
    assert handle.outcome == "ok", f"real execution of {skill_dir_name} must succeed"
    events = monitor_and_emit(adapter, handle)

    return adapter, engine, skill, declared, static_evidence, events


# ---------------------------------------------------------------------------
# Case 1 — benign declared behavior -> ALLOW (real skill: task_summary)
# ---------------------------------------------------------------------------


def test_case_1_benign_declared_behavior_allows():
    adapter, _engine, skill, declared, static_evidence, events = _run_real_pipeline("task_summary")

    assert declared == {"task.read"}
    decision = adapter.evaluate(skill.skill_id)

    assert decision.value is DecisionValue.ALLOW
    assert decision.reason_code is None

    findings = correlate(skill.skill_id, declared, static_evidence, events)
    assert findings == []


# ---------------------------------------------------------------------------
# Case 2 — runtime undeclared capability -> R-D finding (real skill: task_insights)
# ---------------------------------------------------------------------------


def test_case_2_runtime_undeclared_capability():
    adapter, _engine, skill, declared, _static_evidence, events = _run_real_pipeline("task_insights")

    observed = {e.action.capability.identifier for e in events}
    r_minus_d = observed - declared
    assert r_minus_d == {"filesystem.read", "network.egress"}

    decision = adapter.evaluate(skill.skill_id)
    assert decision.value is DecisionValue.FLAG
    assert decision.reason_code is ReasonCode.UNDECLARED_CAPABILITY


# ---------------------------------------------------------------------------
# Case 3 — static finding -> S-D finding (real skill: task_insights)
# ---------------------------------------------------------------------------


def test_case_3_static_finding_undeclared():
    _adapter, _engine, _skill, declared, static_evidence, _events = _run_real_pipeline(
        "task_insights"
    )

    static_capabilities = {e.data["capability"] for e in static_evidence}
    s_minus_d = static_capabilities - declared
    assert s_minus_d == {"filesystem.read", "network.egress"}


# ---------------------------------------------------------------------------
# Case 4 — runtime finding -> R nonempty (real skill: task_insights)
# ---------------------------------------------------------------------------


def test_case_4_runtime_finding_nonempty():
    _adapter, _engine, _skill, _declared, _static_evidence, events = _run_real_pipeline(
        "task_insights"
    )

    observed = {e.action.capability.identifier for e in events}
    assert observed  # R is nonempty, from genuinely executing the real skill
    assert observed == {"task.read", "filesystem.read", "network.egress"}


# ---------------------------------------------------------------------------
# Case 5 — declaration/runtime mismatch -> UNDECLARED_CAPABILITY or
# STATIC_RUNTIME_MISMATCH (real skill: task_insights)
# ---------------------------------------------------------------------------


def test_case_5_declaration_runtime_mismatch():
    _adapter, _engine, skill, declared, static_evidence, events = _run_real_pipeline(
        "task_insights"
    )

    findings = correlate(skill.skill_id, declared, static_evidence, events)
    reason_codes = {f.reason_code for f in findings}

    assert ReasonCode.UNDECLARED_CAPABILITY in reason_codes or (
        ReasonCode.STATIC_RUNTIME_MISMATCH in reason_codes
    )
    # For this real skill, it is specifically UNDECLARED_CAPABILITY (both S-D and R-D).
    assert ReasonCode.UNDECLARED_CAPABILITY in reason_codes


# ---------------------------------------------------------------------------
# Case 6 — policy violation -> DENY / POLICY_VIOLATION (real skill: focus_picker,
# real observed behavior + a legitimate assessor-side policy configuration)
# ---------------------------------------------------------------------------


def test_case_6_policy_violation_on_real_observed_behavior():
    engine = ConformanceEngine()
    adapter, _engine, skill, declared, static_evidence, events = _run_real_pipeline(
        "focus_picker", engine
    )

    observed = {e.action.capability.identifier for e in events}
    # focus_picker genuinely calls ctx.files.read (filesystem.read) at runtime
    # (see tests/fixtures/.../focus_picker/skill.py _count_history) — real
    # behavior, not altered for this test.
    assert "filesystem.read" in observed

    # A real, legitimate assessor-side policy: deny filesystem.read for this
    # skill. This is a policy DECISION applied on top of genuine observed
    # behavior, exactly as the first milestone's Case C applied set_policy
    # to a real registered skill — not a change to what the skill does.
    engine.set_policy_rules(
        skill.skill_id,
        tuple(PolicyRule(capability, DecisionValue.ALLOW) for capability in declared)
        + (PolicyRule("filesystem.read", DecisionValue.DENY),),
    )

    decision = adapter.evaluate(skill.skill_id)

    assert decision.value is DecisionValue.DENY
    assert decision.reason_code is ReasonCode.POLICY_VIOLATION

    findings = correlate(skill.skill_id, declared, static_evidence, events,
                           policy={c for c in declared if c != "filesystem.read"})
    violations = [f for f in findings if f.reason_code is ReasonCode.POLICY_VIOLATION]
    assert len(violations) == 1
    assert violations[0].capabilities == ("filesystem.read",)


# ---------------------------------------------------------------------------
# Full-pipeline Assessment for an additional real skill beyond task_insights
# ---------------------------------------------------------------------------


def test_additional_real_skill_fully_assessed_end_to_end():
    adapter, _engine, skill, declared, static_evidence, events = _run_real_pipeline("focus_picker")

    findings = correlate(skill.skill_id, declared, static_evidence, events)
    decision = adapter.evaluate(skill.skill_id)
    severity = classify_severity(decision, findings)

    assessment = build_assessment(
        skill_id=skill.skill_id, skill_name=skill.name, skill_version=skill.version,
        source=skill.source, declared_capabilities=declared, static_evidence=static_evidence,
        events=events, findings=findings, decision=decision, policy_results={}, severity=severity,
    )

    assert assessment.skill_id == "focus_picker"
    assert assessment.decision.value is DecisionValue.ALLOW  # declared honestly, no mismatch
    assert assessment.severity is Severity.LOW
    assert assessment.recommendation == "NO ISSUES FOUND"
