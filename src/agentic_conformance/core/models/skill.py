"""Canonical Skill model (docs/spec.md §6, §7.1)."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentic_conformance.core.models.capability import Capability

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Declaration:
    """The skill's claimed operational boundary (docs/spec.md §6).

    A declaration is an assertion of intended capability, not proof of
    actual behavior.
    """

    declared_capabilities: tuple[Capability, ...]
    permissions: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.declared_capabilities, tuple) or not all(
            isinstance(c, Capability) for c in self.declared_capabilities
        ):
            raise ValueError("declared_capabilities must be a tuple of Capability")
        if not isinstance(self.permissions, tuple):
            raise TypeError("permissions must be a tuple of strings")
        if not isinstance(self.constraints, tuple):
            raise TypeError("constraints must be a tuple of strings")


@dataclass(frozen=True)
class Skill:
    """Canonical representation of an Agentic Skill (docs/spec.md §7.1)."""

    skill_id: str
    name: str
    version: str
    description: str
    source: str
    integrity: str
    declaration: Declaration
    schema_version: str = SCHEMA_VERSION
    dependencies: tuple[str, ...] = ()
    context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        required_strings = {
            "schema_version": self.schema_version,
            "skill_id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "source": self.source,
            "integrity": self.integrity,
        }
        for field_name, value in required_strings.items():
            if not isinstance(value, str) or not value:
                raise ValueError(f"Skill.{field_name} must be a non-empty string")
        if not isinstance(self.declaration, Declaration):
            raise TypeError("Skill.declaration must be a Declaration instance")
        if not isinstance(self.dependencies, tuple):
            raise TypeError("Skill.dependencies must be a tuple of strings")
        if not isinstance(self.context, dict):
            raise TypeError("Skill.context must be a dict")
