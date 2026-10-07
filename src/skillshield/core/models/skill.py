"""Canonical Skill representation (docs/product-spec.md §11, §13).

The canonical ``Skill`` is the normalized, security-domain representation
the rest of the pipeline operates on. A skill directory and an equivalent
ZIP of the same content must produce an equivalent ``Skill``
(docs/product-plan.md P1 validation requirement).

A missing or malformed declaration must never be fatal to ingestion: it is
captured as a ``DeclarationProblem`` on the ``Skill`` so the conformance
stage can turn it into an ``INVALID_DECLARATION`` finding instead of
aborting the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = "1.0"

_PROBLEM_KINDS = ("missing", "malformed")


@dataclass(frozen=True)
class DeclaredCapability:
    """One capability entry from a skill's manifest."""

    identifier: str
    scope: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str) or not self.identifier:
            raise ValueError("DeclaredCapability.identifier must be a non-empty string")
        if not isinstance(self.scope, tuple):
            raise TypeError("DeclaredCapability.scope must be a tuple of strings")


@dataclass(frozen=True)
class DeclarationProblem:
    """A non-fatal problem discovered while reading a skill's declaration."""

    kind: str
    detail: str

    def __post_init__(self) -> None:
        if self.kind not in _PROBLEM_KINDS:
            raise ValueError(f"DeclarationProblem.kind must be one of {_PROBLEM_KINDS}")
        if not isinstance(self.detail, str) or not self.detail:
            raise ValueError("DeclarationProblem.detail must be a non-empty string")


@dataclass(frozen=True)
class Declaration:
    """The skill's claimed operational boundary (docs/product-spec.md §13).

    A declaration is an assertion of intended capability, not proof of
    actual behavior.
    """

    declared_capabilities: tuple[DeclaredCapability, ...] = ()
    entrypoint: str | None = None
    raw: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.declared_capabilities, tuple) or not all(
            isinstance(c, DeclaredCapability) for c in self.declared_capabilities
        ):
            raise TypeError("Declaration.declared_capabilities must be a tuple of DeclaredCapability")
        if self.entrypoint is not None and not isinstance(self.entrypoint, str):
            raise TypeError("Declaration.entrypoint must be a string or None")
        if not isinstance(self.raw, dict):
            raise TypeError("Declaration.raw must be a dict")

    def capability_ids(self) -> frozenset[str]:
        """The declared capability identifiers, as a plain set (D)."""
        return frozenset(c.identifier for c in self.declared_capabilities)


@dataclass(frozen=True)
class Skill:
    """Canonical representation of a downloaded Agentic Skill
    (docs/product-spec.md §11)."""

    skill_id: str
    name: str
    version: str
    description: str
    source_files: tuple[str, ...]
    declaration: Declaration | None
    declaration_problem: DeclarationProblem | None = None
    schema_version: str = SCHEMA_VERSION
    context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name, value in (
            ("schema_version", self.schema_version),
            ("skill_id", self.skill_id),
            ("name", self.name),
            ("version", self.version),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"Skill.{field_name} must be a non-empty string")
        if not isinstance(self.description, str):
            raise TypeError("Skill.description must be a string")
        if not isinstance(self.source_files, tuple) or not all(
            isinstance(f, str) for f in self.source_files
        ):
            raise TypeError("Skill.source_files must be a tuple of strings")
        if self.declaration is not None and not isinstance(self.declaration, Declaration):
            raise TypeError("Skill.declaration must be a Declaration or None")
        if self.declaration_problem is not None and not isinstance(
            self.declaration_problem, DeclarationProblem
        ):
            raise TypeError("Skill.declaration_problem must be a DeclarationProblem or None")
        if not isinstance(self.context, dict):
            raise TypeError("Skill.context must be a dict")

    def declared_capability_ids(self) -> frozenset[str]:
        """The declared capability set (D), or empty if there is no usable declaration."""
        if self.declaration is None:
            return frozenset()
        return self.declaration.capability_ids()
