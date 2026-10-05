"""Conformance core: structural checks, set-based rules, and the engine (docs/spec.md §8-§9)."""

from agentic_conformance.core.conformance.engine import ConformanceEngine
from agentic_conformance.core.conformance.rules import (
    policy_violating_capabilities,
    runtime_within_declared,
    runtime_within_declared_and_policy,
    runtime_within_policy,
    undeclared_capabilities,
)
from agentic_conformance.core.conformance.structural import (
    StructuralViolation,
    validate_capability_identifier,
    validate_security_event,
    validate_skill_declaration,
)

__all__ = [
    "ConformanceEngine",
    "StructuralViolation",
    "policy_violating_capabilities",
    "runtime_within_declared",
    "runtime_within_declared_and_policy",
    "runtime_within_policy",
    "undeclared_capabilities",
    "validate_capability_identifier",
    "validate_security_event",
    "validate_skill_declaration",
]
