"""Reference application adapter (docs/spec.md §11).

Translates the reference application's native skill, declaration, and
runtime-event representations into canonical models, and integrates with
the conformance core only through the generic ConformanceAPI inherited
from ProductAdapter. Contains product-specific translation only — no
conformance rules.
"""

from __future__ import annotations

from typing import Any

from agentic_conformance.adapters.reference_app.mapping import normalize_capability_name
from agentic_conformance.core.interfaces.adapter import ProductAdapter
from agentic_conformance.core.models import (
    Action,
    Actor,
    Capability,
    Declaration,
    SecurityEvent,
    Skill,
    Target,
)


class ReferenceAppAdapter(ProductAdapter):
    """Adapter for the reference (vulnerable) Agentic Skills application."""

    def normalize_capability(self, native_capability: Any) -> Capability:
        return Capability(identifier=normalize_capability_name(native_capability))

    def translate_skill(self, native_skill: Any) -> Skill:
        declared = tuple(
            self.normalize_capability(name) for name in native_skill["declared_capabilities"]
        )
        return Skill(
            skill_id=native_skill["id"],
            name=native_skill["name"],
            version=native_skill["version"],
            description=native_skill.get("description", native_skill["name"]),
            source="reference_app",
            integrity=native_skill.get("integrity", "unknown"),
            declaration=Declaration(declared_capabilities=declared),
        )

    def translate_event(self, native_event: Any) -> SecurityEvent:
        capability = self.normalize_capability(native_event["capability"])
        return SecurityEvent(
            event_id=native_event["id"],
            timestamp=native_event["timestamp"],
            event_type=native_event.get("type", capability.identifier),
            context={"skill_id": native_event["skill_id"]},
            actor=Actor(type="skill", id=native_event["skill_id"]),
            action=Action(
                capability=capability, operation=native_event.get("operation", "invoke")
            ),
            target=Target(
                type=native_event.get("target_type", "resource"),
                identifier=native_event.get("target", "unknown"),
            ),
        )
