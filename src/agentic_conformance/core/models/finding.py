"""Canonical Finding model (docs/downloaded-skill-assessment-spec.md §10.4).

A Finding is a single, standardized statement that a comparison among `D`
(declared), `S` (static), `R` (runtime), `P` (policy) produced a notable
result. It is distinct from a `Decision` (docs/spec.md §7.5, unchanged):
one evaluation produces exactly one `Decision` and zero or more `Finding`s
explaining why.

Reuses the existing, closed `ReasonCode` enum (docs/spec.md §7.5) — no new
reason codes are introduced, per
docs/downloaded-skill-assessment-spec.md §9.1 ("No new ReasonCode values
are required by this milestone").

Per docs/downloaded-skill-assessment-spec.md §9.3, a Finding never claims
maliciousness — only a standardized reason code, the capabilities
involved, and a reference to the evidence behind it.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentic_conformance.core.models.decision import ReasonCode

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Finding:
    """One standardized conformance/security finding."""

    reason_code: ReasonCode
    capabilities: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    description: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise ValueError("Finding.schema_version must be a non-empty string")
        if not isinstance(self.reason_code, ReasonCode):
            raise TypeError("Finding.reason_code must be a ReasonCode")
        if not isinstance(self.capabilities, tuple) or not all(
            isinstance(c, str) and c for c in self.capabilities
        ):
            raise ValueError("Finding.capabilities must be a tuple of non-empty strings")
        if not isinstance(self.evidence_refs, tuple) or not all(
            isinstance(r, str) and r for r in self.evidence_refs
        ):
            raise ValueError("Finding.evidence_refs must be a tuple of non-empty strings")
        if not isinstance(self.description, str) or not self.description:
            raise ValueError("Finding.description must be a non-empty string")
