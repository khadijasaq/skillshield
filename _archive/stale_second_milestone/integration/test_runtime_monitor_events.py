"""Real-data integration test: execution -> monitoring -> emission (second
milestone, Phase 4). Runs the real, unmodified `task_insights` skill
through the real Phase 3 controlled-execution mechanism, converts its
genuine observations into canonical SecurityEvents, and emits them through
the existing, unmodified ConformanceEngine — populating `R` with real
data, consistently with the real `S - D` mismatch already found in Phase 2.
"""

from __future__ import annotations

from pathlib import Path

from agentic_conformance.adapters.vuln_agentic_skills_app import VulnAgenticSkillsAppAdapter
from agentic_conformance.adapters.vuln_agentic_skills_app.adapter import (
    load_manifest,
    resolve_entrypoint,
)
from agentic_conformance.analysis.runtime.monitor import monitor_and_emit, runtime_capability_set
from agentic_conformance.core.conformance.engine import ConformanceEngine
from agentic_conformance.core.models import DecisionValue, ReasonCode
from agentic_conformance.execution.subprocess_sandbox import execute

_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "vuln_agentic_skills_app"
    / "task_insights"
)


def test_execution_to_monitoring_to_engine_produces_real_r():
    engine = ConformanceEngine()
    adapter = VulnAgenticSkillsAppAdapter(engine)

    adapter.register(_FIXTURE_DIR)

    manifest = load_manifest(_FIXTURE_DIR)
    entry_file, entry_attr = resolve_entrypoint(_FIXTURE_DIR, manifest)
    handle = execute("task_insights", entry_file, entry_attr, {})
    assert handle.outcome == "ok"

    events = monitor_and_emit(adapter, handle)
    r_capabilities = runtime_capability_set(events)

    assert r_capabilities == {"task.read", "filesystem.read", "network.egress"}


def test_real_runtime_undeclared_capability_flags_through_existing_engine():
    """D = {task.read}; real R includes filesystem.read and network.egress, neither
    declared -> the existing, unmodified engine must FLAG / UNDECLARED_CAPABILITY."""
    engine = ConformanceEngine()
    adapter = VulnAgenticSkillsAppAdapter(engine)

    adapter.register(_FIXTURE_DIR)

    manifest = load_manifest(_FIXTURE_DIR)
    entry_file, entry_attr = resolve_entrypoint(_FIXTURE_DIR, manifest)
    handle = execute("task_insights", entry_file, entry_attr, {})

    monitor_and_emit(adapter, handle)
    decision = adapter.evaluate("task_insights")

    assert decision.value is DecisionValue.FLAG
    assert decision.reason_code is ReasonCode.UNDECLARED_CAPABILITY
