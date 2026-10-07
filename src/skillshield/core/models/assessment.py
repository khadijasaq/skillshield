"""Recommendation and Assessment models (docs/product-spec.md §19, §29).

SkillShield outputs exactly one of three recommendations and never labels a
skill "malicious".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from skillshield.core.models.finding import Finding


class Recommendation(str, Enum):
    """The only three outputs SkillShield may ever produce."""

    NO_ISSUES_FOUND = "NO ISSUES FOUND"
    REVIEW_BEFORE_USE = "REVIEW BEFORE USE"
    DO_NOT_USE = "DO NOT USE"


@dataclass(frozen=True)
class CapabilitySummary:
    """The D/S/R/P capability-count summary shown to the user."""

    declared: frozenset[str] = frozenset()
    static: frozenset[str] = frozenset()
    runtime: frozenset[str] = frozenset()
    policy_permitted: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Assessment:
    """The final, user-facing output of one SkillShield run
    (docs/product-spec.md §19, §29)."""

    skill_id: str
    skill_name: str
    skill_version: str
    recommendation: Recommendation
    capabilities: CapabilitySummary
    findings: tuple[Finding, ...]
    limitations: tuple[str, ...] = ()
    artifact_digest: str | None = None
    policy_name: str | None = None
    generated_at: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("skill_id", self.skill_id),
            ("skill_name", self.skill_name),
            ("skill_version", self.skill_version),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"Assessment.{field_name} must be a non-empty string")
        if not isinstance(self.recommendation, Recommendation):
            raise TypeError("Assessment.recommendation must be a Recommendation")
        if not isinstance(self.capabilities, CapabilitySummary):
            raise TypeError("Assessment.capabilities must be a CapabilitySummary")
        if not isinstance(self.findings, tuple) or not all(
            isinstance(f, Finding) for f in self.findings
        ):
            raise TypeError("Assessment.findings must be a tuple of Finding")
        if not isinstance(self.limitations, tuple) or not all(
            isinstance(entry, str) for entry in self.limitations
        ):
            raise TypeError("Assessment.limitations must be a tuple of strings")
