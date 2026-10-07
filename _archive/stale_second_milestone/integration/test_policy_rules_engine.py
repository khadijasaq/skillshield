"""Integration tests for the Phase 6 `set_policy_rules` extension to the
existing, otherwise-unmodified `ConformanceEngine` (second milestone,
Phase 6).

Confirms: (1) the new ALLOW/FLAG/DENY-effect policy mechanism works
end-to-end through the real engine, and (2) the first milestone's legacy
`set_policy(skill_id, frozenset)` behavior — including its exact Case C
decision/reason code — is completely unaffected by this addition.
"""

from __future__ import annotations

from agentic_conformance.adapters.reference_app import ReferenceAppAdapter
from agentic_conformance.core.conformance.engine import ConformanceEngine
from agentic_conformance.core.conformance.policy import PolicyRule
from agentic_conformance.core.models import DecisionValue, ReasonCode


def _native_skill(skill_id: str, *declared_capabilities: str) -> dict:
    return {
        "id": skill_id,
        "name": "Policy Rules Test Skill",
        "version": "1.0.0",
        "description": "x",
        "integrity": "sha256:deadbeef",
        "declared_capabilities": list(declared_capabilities),
    }


def _native_event(skill_id: str, event_id: str, native_capability: str) -> dict:
    return {
        "id": event_id,
        "timestamp": "2026-10-06T00:00:00Z",
        "skill_id": skill_id,
        "capability": native_capability,
    }


def test_allow_effect_capability_allows():
    engine = ConformanceEngine()
    adapter = ReferenceAppAdapter(engine)

    adapter.register(_native_skill("allow-case", "read_task"))
    engine.set_policy_rules("allow-case", (PolicyRule("task.read", DecisionValue.ALLOW),))
    adapter.observe(_native_event("allow-case", "evt-1", "read_task"))

    decision = adapter.evaluate("allow-case")

    assert decision.value is DecisionValue.ALLOW
    assert decision.reason_code is None


def test_deny_effect_capability_denies_with_policy_violation():
    engine = ConformanceEngine()
    adapter = ReferenceAppAdapter(engine)

    adapter.register(_native_skill("deny-case", "read_task", "execute_process"))
    engine.set_policy_rules(
        "deny-case",
        (PolicyRule("task.read", DecisionValue.ALLOW), PolicyRule("process.execute", DecisionValue.DENY)),
    )
    adapter.observe(_native_event("deny-case", "evt-1", "execute_process"))

    decision = adapter.evaluate("deny-case")

    assert decision.value is DecisionValue.DENY
    assert decision.reason_code is ReasonCode.POLICY_VIOLATION


def test_flag_effect_capability_flags_with_policy_violation():
    engine = ConformanceEngine()
    adapter = ReferenceAppAdapter(engine)

    adapter.register(_native_skill("flag-case", "read_task", "write_file"))
    engine.set_policy_rules(
        "flag-case",
        (PolicyRule("task.read", DecisionValue.ALLOW), PolicyRule("filesystem.write", DecisionValue.FLAG)),
    )
    adapter.observe(_native_event("flag-case", "evt-1", "write_file"))

    decision = adapter.evaluate("flag-case")

    assert decision.value is DecisionValue.FLAG
    assert decision.reason_code is ReasonCode.POLICY_VIOLATION


def test_allow_and_deny_effects_distinguished_for_same_skill():
    """The central Phase 6 requirement: ALLOW-effect vs DENY-effect capability,
    for the same skill, in the same evaluation run."""
    engine = ConformanceEngine()
    adapter = ReferenceAppAdapter(engine)

    adapter.register(_native_skill("mixed-case", "read_task", "execute_process"))
    engine.set_policy_rules(
        "mixed-case",
        (PolicyRule("task.read", DecisionValue.ALLOW), PolicyRule("process.execute", DecisionValue.DENY)),
    )

    # Only the ALLOW-effect capability observed -> ALLOW.
    adapter.observe(_native_event("mixed-case", "evt-1", "read_task"))
    assert adapter.evaluate("mixed-case").value is DecisionValue.ALLOW

    # Now the DENY-effect capability is also observed -> DENY.
    adapter.observe(_native_event("mixed-case", "evt-2", "execute_process"))
    decision = adapter.evaluate("mixed-case")
    assert decision.value is DecisionValue.DENY
    assert decision.reason_code is ReasonCode.POLICY_VIOLATION


def test_legacy_set_policy_behavior_is_completely_unchanged():
    """Exact regression of the first milestone's Case C
    (tests/integration/test_end_to_end.py::test_case_c_policy_violation_denies),
    reproduced here to confirm `set_policy_rules` existing alongside
    `set_policy` changes nothing about the legacy path."""
    engine = ConformanceEngine()
    adapter = ReferenceAppAdapter(engine)

    adapter.register(_native_skill("case-c", "read_task", "execute_process"))
    engine.set_policy("case-c", frozenset({"task.read"}))
    adapter.observe(_native_event("case-c", "evt-1", "execute_process"))

    decision = adapter.evaluate("case-c")

    assert decision.value is DecisionValue.DENY
    assert decision.reason_code is ReasonCode.POLICY_VIOLATION
