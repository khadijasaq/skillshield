"""Tests for minimal policy-rule evaluation (second milestone, Phase 6;
docs/downloaded-skill-assessment-spec.md §10.1)."""

from __future__ import annotations

import pytest

from agentic_conformance.core.conformance.policy import (
    PolicyRule,
    denied_capabilities,
    evaluate_policy,
    flagged_capabilities,
)
from agentic_conformance.core.models import DecisionValue


def test_policy_rule_rejects_invalid_effect():
    with pytest.raises(TypeError):
        PolicyRule(capability="task.read", effect="not-a-decision-value")  # type: ignore[arg-type]


def test_evaluate_policy_resolves_allow_effect():
    rules = (PolicyRule("task.read", DecisionValue.ALLOW),)
    effects = evaluate_policy(rules, {"task.read"})

    assert effects == {"task.read": DecisionValue.ALLOW}
    assert denied_capabilities(effects) == set()
    assert flagged_capabilities(effects) == set()


def test_evaluate_policy_resolves_deny_effect():
    rules = (PolicyRule("process.execute", DecisionValue.DENY),)
    effects = evaluate_policy(rules, {"process.execute"})

    assert denied_capabilities(effects) == {"process.execute"}


def test_evaluate_policy_resolves_flag_effect():
    rules = (PolicyRule("filesystem.read", DecisionValue.FLAG),)
    effects = evaluate_policy(rules, {"filesystem.read"})

    assert flagged_capabilities(effects) == {"filesystem.read"}
    assert denied_capabilities(effects) == set()


def test_evaluate_policy_unmatched_capability_defaults_to_deny():
    rules = (PolicyRule("task.read", DecisionValue.ALLOW),)
    effects = evaluate_policy(rules, {"task.read", "network.egress"})

    assert effects["network.egress"] is DecisionValue.DENY
    assert denied_capabilities(effects) == {"network.egress"}


def test_evaluate_policy_only_resolves_observed_capabilities():
    rules = (PolicyRule("task.read", DecisionValue.DENY),)
    effects = evaluate_policy(rules, {"network.egress"})

    assert "task.read" not in effects
    assert effects == {"network.egress": DecisionValue.DENY}
