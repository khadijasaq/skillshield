"""Tests for the canonical Assessment model (second milestone, Phase 7;
docs/downloaded-skill-assessment-spec.md §10.3)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from agentic_conformance.core.models import Decision, DecisionValue, ReasonCode, Severity
from agentic_conformance.core.models.assessment import Assessment
from agentic_conformance.core.models.finding import Finding

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"


def _load_schema(name: str) -> dict:
    with open(SCHEMAS_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


def _top_level_field_names(model_cls) -> set[str]:
    return {f.name for f in dataclasses.fields(model_cls)}


def _assessment(**overrides) -> Assessment:
    defaults = dict(
        skill_id="task_insights",
        skill_name="Task Insights",
        skill_version="1.0.0",
        source="vuln_agentic_skills_app",
        declared_capabilities=("task.read",),
        static_capabilities=("task.read", "filesystem.read", "network.egress"),
        runtime_capabilities=("task.read", "filesystem.read", "network.egress"),
        findings=(),
        policy_results=(),
        decision=Decision(skill_id="task_insights", value=DecisionValue.ALLOW),
        severity=Severity.LOW,
        recommendation="NO ISSUES FOUND",
    )
    defaults.update(overrides)
    return Assessment(**defaults)


def test_assessment_valid_construction():
    assessment = _assessment()
    assert assessment.skill_id == "task_insights"
    assert assessment.schema_version == "1.0"


def test_assessment_rejects_invalid_recommendation():
    with pytest.raises(ValueError):
        _assessment(recommendation="MAYBE SURE WHY NOT")


def test_assessment_rejects_non_decision():
    with pytest.raises(TypeError):
        _assessment(decision="not-a-decision")  # type: ignore[arg-type]


def test_assessment_rejects_non_severity():
    with pytest.raises(TypeError):
        _assessment(severity="HIGH")  # type: ignore[arg-type]


def test_assessment_rejects_non_finding_in_findings():
    with pytest.raises(TypeError):
        _assessment(findings=("not-a-finding",))  # type: ignore[arg-type]


def test_assessment_accepts_real_finding():
    finding = Finding(
        reason_code=ReasonCode.UNDECLARED_CAPABILITY,
        capabilities=("network.egress",),
        evidence_refs=("obs-1",),
        description="x",
    )
    assessment = _assessment(findings=(finding,))
    assert assessment.findings == (finding,)


def test_assessment_schema_model_alignment():
    schema = _load_schema("assessment.schema.json")
    assert set(schema["properties"].keys()) == _top_level_field_names(Assessment)
