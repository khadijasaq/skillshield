"""Tests for runtime observation -> canonical SecurityEvent mapping (second
milestone, Phase 4), using a synthetic ExecutionHandle fixture to isolate
the mapping logic from any real execution."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_conformance.adapters.vuln_agentic_skills_app import VulnAgenticSkillsAppAdapter
from agentic_conformance.analysis.runtime.monitor import (
    invalid_observation_capabilities,
    monitor_and_emit,
    observations_to_native_events,
    runtime_capability_set,
)
from agentic_conformance.core.interfaces import ConformanceAPI
from agentic_conformance.core.models import Decision, DecisionValue, SecurityEvent, Skill
from agentic_conformance.execution.handle import ExecutionHandle


class _RecordingConformanceAPI(ConformanceAPI):
    def __init__(self) -> None:
        self.events: list[SecurityEvent] = []

    def register_skill(self, skill_profile: Skill) -> None:
        pass

    def emit_event(self, security_event: SecurityEvent) -> None:
        self.events.append(security_event)

    def evaluate(self, skill_id: str) -> Decision:
        return Decision(skill_id=skill_id, value=DecisionValue.ALLOW)


def _handle(observations) -> ExecutionHandle:
    return ExecutionHandle(
        skill_id="task_insights",
        invocation_id="inv-001",
        outcome="ok",
        exit_code=0,
        duration_seconds=0.05,
        stdout="{}",
        stderr="",
        working_directory=Path("/tmp/x"),
        created_or_modified_files=(),
        observations=tuple(observations),
    )


def test_observations_to_native_events_adds_skill_and_invocation_id():
    handle = _handle([{"seq": 1, "capability": "task.read", "resource": "*",
                        "detail": {}, "outcome": "ok", "source": "broker", "ts": "t"}])

    enriched = observations_to_native_events(handle)

    assert enriched[0]["skill_id"] == "task_insights"
    assert enriched[0]["invocation_id"] == "inv-001"


def test_monitor_and_emit_produces_canonical_events_and_emits_them():
    api = _RecordingConformanceAPI()
    adapter = VulnAgenticSkillsAppAdapter(api)
    handle = _handle([
        {"seq": 1, "capability": "task.read", "resource": "*", "detail": {},
         "outcome": "ok", "source": "broker", "ts": "2026-10-06T00:00:00.000Z"},
        {"seq": 2, "capability": "fs.read", "resource": "data/tasks.json", "detail": {},
         "outcome": "ok", "source": "broker", "ts": "2026-10-06T00:00:01.000Z"},
        {"seq": 3, "capability": "net.outbound", "resource": "http://127.0.0.1/x", "detail": {},
         "outcome": "ok", "source": "broker", "ts": "2026-10-06T00:00:02.000Z"},
    ])

    events = monitor_and_emit(adapter, handle)

    assert len(events) == 3
    assert len(api.events) == 3
    identifiers = {e.action.capability.identifier for e in events}
    assert identifiers == {"task.read", "filesystem.read", "network.egress"}
    assert all(isinstance(e, SecurityEvent) for e in events)
    assert all(e.context["skill_id"] == "task_insights" for e in events)


def test_runtime_capability_set_deduplicates():
    api = _RecordingConformanceAPI()
    adapter = VulnAgenticSkillsAppAdapter(api)
    handle = _handle([
        {"seq": 1, "capability": "task.read", "resource": "*", "detail": {},
         "outcome": "ok", "source": "broker", "ts": "t1"},
        {"seq": 2, "capability": "task.read", "resource": "x", "detail": {},
         "outcome": "ok", "source": "broker", "ts": "t2"},
    ])

    events = monitor_and_emit(adapter, handle)

    assert runtime_capability_set(events) == {"task.read"}


def test_invalid_observation_capabilities_reports_unmapped_native_ids():
    handle = _handle([
        {"seq": 1, "capability": "not_a_real_native_capability", "resource": "*",
         "detail": {}, "outcome": "ok", "source": "broker", "ts": "t"},
    ])

    invalid = invalid_observation_capabilities(handle)

    assert invalid == {"not_a_real_native_capability"}


def test_monitor_and_emit_raises_clearly_on_unmapped_capability():
    api = _RecordingConformanceAPI()
    adapter = VulnAgenticSkillsAppAdapter(api)
    handle = _handle([
        {"seq": 1, "capability": "not_a_real_native_capability", "resource": "*",
         "detail": {}, "outcome": "ok", "source": "broker", "ts": "t"},
    ])

    with pytest.raises(ValueError):
        monitor_and_emit(adapter, handle)
