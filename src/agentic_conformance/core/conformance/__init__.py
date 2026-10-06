"""Conformance core: structural checks, set-based rules, correlation, policy,
severity, and the engine (docs/spec.md §8-§9;
docs/downloaded-skill-assessment-spec.md §8-§10)."""

from agentic_conformance.core.conformance.assessment import build_assessment, format_assessment
from agentic_conformance.core.conformance.correlation import (
    correlate,
    runtime_not_statically_identified,
    static_within_declared,
    statically_identified_not_observed,
    statically_undeclared_capabilities,
)
from agentic_conformance.core.conformance.engine import ConformanceEngine
from agentic_conformance.core.conformance.policy import (
    PolicyRule,
    denied_capabilities,
    evaluate_policy,
    flagged_capabilities,
)
from agentic_conformance.core.conformance.rules import (
    policy_violating_capabilities,
    runtime_within_declared,
    runtime_within_declared_and_policy,
    runtime_within_policy,
    undeclared_capabilities,
)
from agentic_conformance.core.conformance.severity import classify_severity
from agentic_conformance.core.conformance.structural import (
    StructuralViolation,
    validate_capability_identifier,
    validate_security_event,
    validate_skill_declaration,
)

__all__ = [
    "ConformanceEngine",
    "PolicyRule",
    "StructuralViolation",
    "build_assessment",
    "classify_severity",
    "correlate",
    "denied_capabilities",
    "evaluate_policy",
    "flagged_capabilities",
    "format_assessment",
    "policy_violating_capabilities",
    "runtime_not_statically_identified",
    "runtime_within_declared",
    "runtime_within_declared_and_policy",
    "runtime_within_policy",
    "static_within_declared",
    "statically_identified_not_observed",
    "statically_undeclared_capabilities",
    "undeclared_capabilities",
    "validate_capability_identifier",
    "validate_security_event",
    "validate_skill_declaration",
]
