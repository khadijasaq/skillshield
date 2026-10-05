"""Structural conformance checks (docs/spec.md §9).

Canonical models already enforce their own structural validity at
construction time. This module provides the conformance core's own
defensive gate on top of that — re-checking domain-level structural
completeness (e.g. a declaration with no declared capabilities) that a
syntactically valid object can still fail — and maps any failure to a
standardized reason code the engine can return as part of a Decision.
"""

from __future__ import annotations

from agentic_conformance.core.models import ReasonCode, SecurityEvent, Skill
from agentic_conformance.core.models.capability import is_supported_capability


class StructuralViolation(Exception):
    """Raised when a canonical representation fails a structural conformance check."""

    def __init__(self, reason_code: ReasonCode, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def validate_capability_identifier(identifier: str) -> None:
    """Check that a capability identifier is syntactically valid and supported."""
    if not isinstance(identifier, str) or not identifier:
        raise StructuralViolation(
            ReasonCode.UNKNOWN_CAPABILITY,
            "Capability identifier must be a non-empty string",
        )
    if not is_supported_capability(identifier):
        raise StructuralViolation(
            ReasonCode.UNKNOWN_CAPABILITY,
            f"Unknown capability identifier: {identifier!r}",
        )


def validate_skill_declaration(skill: Skill) -> None:
    """Check that a registered Skill carries a structurally valid declaration."""
    if not isinstance(skill, Skill):
        raise StructuralViolation(
            ReasonCode.INVALID_DECLARATION, "Expected a canonical Skill instance"
        )
    if not skill.declaration.declared_capabilities:
        raise StructuralViolation(
            ReasonCode.MISSING_DECLARATION,
            f"Skill {skill.skill_id!r} declares no capabilities",
        )
    for capability in skill.declaration.declared_capabilities:
        validate_capability_identifier(capability.identifier)


def validate_security_event(event: SecurityEvent) -> None:
    """Check that a runtime event is structurally valid for conformance evaluation."""
    if not isinstance(event, SecurityEvent):
        raise StructuralViolation(
            ReasonCode.INVALID_EVENT, "Expected a canonical SecurityEvent instance"
        )
    validate_capability_identifier(event.action.capability.identifier)
