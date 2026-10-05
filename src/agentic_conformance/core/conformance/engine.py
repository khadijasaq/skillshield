"""Minimal conformance engine (docs/spec.md §8, §9).

A deterministic, in-process implementation of the ConformanceAPI (§5). It
evaluates a registered skill's declaration against its accumulated runtime
events, and against a policy when one has been provided, producing a
standardized Decision (§7.5).

Policy (P) is represented as the simplest possible structure satisfying
§8 — an optional, per-skill set of permitted capability identifiers — with
no complex policy language. It is supplied out-of-band via `set_policy`,
since the three-operation integration contract (§5) does not define a
policy-setting operation.
"""

from __future__ import annotations

from agentic_conformance.core.conformance.rules import (
    policy_violating_capabilities,
    undeclared_capabilities,
)
from agentic_conformance.core.conformance.structural import (
    StructuralViolation,
    validate_security_event,
    validate_skill_declaration,
)
from agentic_conformance.core.interfaces.conformance_api import ConformanceAPI
from agentic_conformance.core.models import (
    Decision,
    DecisionValue,
    ReasonCode,
    SecurityEvent,
    Skill,
)


class ConformanceEngine(ConformanceAPI):
    """In-process conformance core: structural checks + R⊆D / R⊆P evaluation."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._events: dict[str, list[SecurityEvent]] = {}
        self._policies: dict[str, frozenset[str]] = {}

    def register_skill(self, skill_profile: Skill) -> None:
        self._skills[skill_profile.skill_id] = skill_profile
        self._events.setdefault(skill_profile.skill_id, [])

    def emit_event(self, security_event: SecurityEvent) -> None:
        skill_id = security_event.context.get("skill_id")
        self._events.setdefault(skill_id, []).append(security_event)

    def set_policy(self, skill_id: str, permitted_capabilities: frozenset[str]) -> None:
        """Register the permitted-capability policy (P) for a skill."""
        self._policies[skill_id] = frozenset(permitted_capabilities)

    def evaluate(self, skill_id: str) -> Decision:
        skill = self._skills.get(skill_id)
        if skill is None:
            return Decision(
                skill_id=skill_id,
                value=DecisionValue.DENY,
                reason_code=ReasonCode.MISSING_DECLARATION,
            )

        try:
            validate_skill_declaration(skill)
        except StructuralViolation as violation:
            return Decision(
                skill_id=skill_id, value=DecisionValue.DENY, reason_code=violation.reason_code
            )

        events = self._events.get(skill_id, [])
        for event in events:
            try:
                validate_security_event(event)
            except StructuralViolation as violation:
                return Decision(
                    skill_id=skill_id,
                    value=DecisionValue.DENY,
                    reason_code=violation.reason_code,
                )

        declared = {c.identifier for c in skill.declaration.declared_capabilities}
        observed = {event.action.capability.identifier for event in events}

        if undeclared_capabilities(declared, observed):
            return Decision(
                skill_id=skill_id,
                value=DecisionValue.FLAG,
                reason_code=ReasonCode.UNDECLARED_CAPABILITY,
            )

        policy = self._policies.get(skill_id)
        if policy is not None and policy_violating_capabilities(policy, observed):
            return Decision(
                skill_id=skill_id,
                value=DecisionValue.DENY,
                reason_code=ReasonCode.POLICY_VIOLATION,
            )

        return Decision(skill_id=skill_id, value=DecisionValue.ALLOW)
