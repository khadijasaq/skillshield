"""Integration test: real `vuln-agentic-skills-app` skill through the full
existing first-milestone conformance infrastructure (second milestone,
Phase 1).

Registers the real `task_insights` skill (vendored verbatim fixture — see
tests/fixtures/vuln_agentic_skills_app/README.md) through the new adapter
and the existing, unmodified `ConformanceEngine` / `ConformanceAPI`, proving
compatibility with first-milestone infrastructure without any change to it.
"""

from __future__ import annotations

from pathlib import Path

from agentic_conformance.adapters.vuln_agentic_skills_app import VulnAgenticSkillsAppAdapter
from agentic_conformance.core.conformance.engine import ConformanceEngine
from agentic_conformance.core.models import DecisionValue

_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "vuln_agentic_skills_app"
    / "task_insights"
)


def test_real_skill_registers_and_evaluates_through_existing_engine():
    engine = ConformanceEngine()
    adapter = VulnAgenticSkillsAppAdapter(engine)

    adapter.register(_FIXTURE_DIR)
    decision = adapter.evaluate("task_insights")

    # No runtime events have been emitted yet (R = ∅), so R ⊆ D holds
    # trivially and the existing, unmodified engine allows the skill.
    assert decision.value is DecisionValue.ALLOW
    assert decision.reason_code is None


def test_real_skill_declared_capabilities_all_normalize():
    engine = ConformanceEngine()
    adapter = VulnAgenticSkillsAppAdapter(engine)

    skill = adapter.translate_skill(_FIXTURE_DIR)

    assert len(skill.declaration.declared_capabilities) == 1
    assert skill.declaration.declared_capabilities[0].identifier == "task.read"
