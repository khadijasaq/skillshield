"""Tests for the `vuln-agentic-skills-app` adapter (second milestone, Phase 1).

Uses the real, verbatim `task_insights` manifest/skill fixture under
`tests/fixtures/vuln_agentic_skills_app/task_insights/` (see that
directory's README.md for provenance) wherever a real declaration is
needed, and small synthetic dicts only for isolating pure translation
logic (capability mapping, event translation) per the real/synthetic test
split required for this milestone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_conformance.adapters.vuln_agentic_skills_app.adapter import (
    VulnAgenticSkillsAppAdapter,
    load_manifest,
    resolve_entrypoint,
)
from agentic_conformance.core.interfaces import ConformanceAPI
from agentic_conformance.core.models import Decision, DecisionValue, SecurityEvent, Skill

_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "vuln_agentic_skills_app"
    / "task_insights"
)


class _RecordingConformanceAPI(ConformanceAPI):
    """A minimal concrete ConformanceAPI used only to observe adapter calls."""

    def __init__(self) -> None:
        self.registered: list[Skill] = []
        self.events: list[SecurityEvent] = []

    def register_skill(self, skill_profile: Skill) -> None:
        self.registered.append(skill_profile)

    def emit_event(self, security_event: SecurityEvent) -> None:
        self.events.append(security_event)

    def evaluate(self, skill_id: str) -> Decision:
        return Decision(skill_id=skill_id, value=DecisionValue.ALLOW)


_NATIVE_OBSERVATION = {
    "seq": 2,
    "invocation_id": "inv-001",
    "skill_id": "task_insights",
    "capability": "fs.read",
    "resource": "data/tasks.json",
    "detail": {"operation": "read", "bytes": 128},
    "outcome": "ok",
    "source": "broker",
    "ts": "2026-10-06T00:00:00.000Z",
}


# ---------------------------------------------------------------------------
# load_manifest / resolve_entrypoint — real fixture
# ---------------------------------------------------------------------------


def test_load_manifest_reads_real_manifest():
    manifest = load_manifest(_FIXTURE_DIR)

    assert manifest["id"] == "task_insights"
    assert manifest["entrypoint"] == "skill.py:run"
    assert [c["id"] for c in manifest["capabilities"]] == ["task.read"]


def test_resolve_entrypoint_matches_actual_discovered_entrypoint():
    manifest = load_manifest(_FIXTURE_DIR)

    entry_file, entry_attr = resolve_entrypoint(_FIXTURE_DIR, manifest)

    assert entry_file == _FIXTURE_DIR / "skill.py"
    assert entry_attr == "run"
    assert entry_file.exists()


# ---------------------------------------------------------------------------
# normalize_capability — every real native capability id from the testbed's
# shared vocabulary (backend/policy/capability_vocabulary.json)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("native_id", "expected_canonical"),
    [
        ("task.read", "task.read"),
        ("task.write", "task.write"),
        ("fs.read", "filesystem.read"),
        ("fs.write", "filesystem.write"),
        ("net.outbound", "network.egress"),
        ("env.read", "env.read"),
        ("proc.spawn", "process.execute"),
    ],
)
def test_normalize_capability_maps_every_real_native_id(native_id, expected_canonical):
    adapter = VulnAgenticSkillsAppAdapter(_RecordingConformanceAPI())

    capability = adapter.normalize_capability(native_id)

    assert capability.identifier == expected_canonical


def test_normalize_capability_rejects_unmapped_name():
    adapter = VulnAgenticSkillsAppAdapter(_RecordingConformanceAPI())

    with pytest.raises(ValueError):
        adapter.normalize_capability("totally_unknown_native_capability")


# ---------------------------------------------------------------------------
# translate_skill — real fixture: identity, purpose, capability mapping
# ---------------------------------------------------------------------------


def test_translate_skill_produces_canonical_skill_from_real_manifest():
    adapter = VulnAgenticSkillsAppAdapter(_RecordingConformanceAPI())

    skill = adapter.translate_skill(_FIXTURE_DIR)

    assert isinstance(skill, Skill)
    assert skill.skill_id == "task_insights"
    assert skill.name == "Task Insights"
    assert skill.version == "1.0.0"
    assert "private" in skill.description.lower()
    assert skill.source == "vuln_agentic_skills_app"
    assert skill.integrity == "unknown"
    assert [c.identifier for c in skill.declaration.declared_capabilities] == ["task.read"]
    assert skill.context["category"] == "reporting"
    assert skill.context["author"] == "Clearwater Tools"
    assert skill.context["entrypoint"] == "skill.py:run"


# ---------------------------------------------------------------------------
# translate_event — synthetic observation (isolates translation logic)
# ---------------------------------------------------------------------------


def test_translate_event_produces_canonical_security_event_with_normalized_capability():
    adapter = VulnAgenticSkillsAppAdapter(_RecordingConformanceAPI())

    event = adapter.translate_event(_NATIVE_OBSERVATION)

    assert isinstance(event, SecurityEvent)
    assert event.action.capability.identifier == "filesystem.read"
    assert event.context["skill_id"] == "task_insights"
    assert event.context["invocation_id"] == "inv-001"
    assert event.target.identifier == "data/tasks.json"
    assert event.event_id == "obs-inv-001-2"


# ---------------------------------------------------------------------------
# Integration with the generic core (via ProductAdapter.register/observe)
# ---------------------------------------------------------------------------


def test_register_delegates_real_translated_skill_to_conformance_api():
    api = _RecordingConformanceAPI()
    adapter = VulnAgenticSkillsAppAdapter(api)

    adapter.register(_FIXTURE_DIR)

    assert len(api.registered) == 1
    assert api.registered[0].skill_id == "task_insights"


def test_observe_delegates_translated_event_to_conformance_api():
    api = _RecordingConformanceAPI()
    adapter = VulnAgenticSkillsAppAdapter(api)

    adapter.observe(_NATIVE_OBSERVATION)

    assert len(api.events) == 1
    assert api.events[0].action.capability.identifier == "filesystem.read"


# ---------------------------------------------------------------------------
# Isolation of testbed-specific logic: core-facing surface carries only
# canonical types, never a manifest dict, a Path, or a native capability id.
# ---------------------------------------------------------------------------


def test_adapter_registration_never_leaks_native_representation():
    api = _RecordingConformanceAPI()
    adapter = VulnAgenticSkillsAppAdapter(api)

    adapter.register(_FIXTURE_DIR)

    registered_skill = api.registered[0]
    assert isinstance(registered_skill, Skill)
    assert not isinstance(registered_skill, Path)
    for capability in registered_skill.declaration.declared_capabilities:
        assert capability.identifier in {"task.read", "task.write", "filesystem.read",
                                          "filesystem.write", "network.egress", "env.read",
                                          "process.execute"}
