"""Minimal policy-rule evaluation (second milestone, Phase 6;
docs/downloaded-skill-assessment-spec.md §10.1).

Extends, but does not replace, the first milestone's policy mechanism
(`ConformanceEngine.set_policy(skill_id, frozenset[str])`, representing
`P` as a flat permitted-capability set). This module adds the smallest
structure that can additionally distinguish a capability that is actively
*denied* from one that is merely *flagged* — not a general-purpose policy
language (no wildcards, no conditions, no composition operators).
"""

from __future__ import annotations

from dataclasses import dataclass

from agentic_conformance.core.models import DecisionValue


@dataclass(frozen=True)
class PolicyRule:
    """One rule: a capability identifier and the effect observing it has."""

    capability: str
    effect: DecisionValue

    def __post_init__(self) -> None:
        if not isinstance(self.capability, str) or not self.capability:
            raise ValueError("PolicyRule.capability must be a non-empty string")
        if not isinstance(self.effect, DecisionValue):
            raise TypeError("PolicyRule.effect must be a DecisionValue")


def evaluate_policy(
    rules: tuple[PolicyRule, ...], observed: set[str]
) -> dict[str, DecisionValue]:
    """Resolve the effect for every observed capability.

    Each capability has at most one rule in this minimal model (no
    wildcards to make "most specific" ambiguous); if the same capability
    appears more than once, the last rule for it wins. A capability with
    no matching rule defaults to `DENY` — the same "absent from the
    permitted set is a violation" default the existing `set_policy`
    (flat frozenset) mechanism already uses, so a flat permitted set is
    exactly the special case where every listed capability has effect
    `ALLOW` and everything else defaults to `DENY`.
    """
    rule_map: dict[str, DecisionValue] = {rule.capability: rule.effect for rule in rules}
    return {capability: rule_map.get(capability, DecisionValue.DENY) for capability in observed}


def denied_capabilities(effects: dict[str, DecisionValue]) -> set[str]:
    """Capabilities whose resolved effect is DENY."""
    return {capability for capability, effect in effects.items() if effect is DecisionValue.DENY}


def flagged_capabilities(effects: dict[str, DecisionValue]) -> set[str]:
    """Capabilities whose resolved effect is FLAG."""
    return {capability for capability, effect in effects.items() if effect is DecisionValue.FLAG}
