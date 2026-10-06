"""Canonical Assessment model (docs/downloaded-skill-assessment-spec.md §10.3).

The aggregate, canonical output of evaluating one Downloaded Skill. A new
model, additive to the existing five (`Skill`, `Capability`,
`SecurityEvent`, `Evidence`, `Decision`) — it does not modify any of them.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentic_conformance.core.models.decision import Decision
from agentic_conformance.core.models.finding import Finding
from agentic_conformance.core.models.severity import Severity

SCHEMA_VERSION = "1.0"

#: The fixed, small set of recommendation strings — never freeform/generated
#: text (docs/downloaded-skill-assessment-spec.md §10.3).
RECOMMENDATIONS = frozenset({"NO ISSUES FOUND", "REVIEW BEFORE USE", "DO NOT USE"})


@dataclass(frozen=True)
class Assessment:
    """Canonical, aggregate assessment of one evaluated skill."""

    skill_id: str
    skill_name: str
    skill_version: str
    source: str
    declared_capabilities: tuple[str, ...]
    static_capabilities: tuple[str, ...]
    runtime_capabilities: tuple[str, ...]
    findings: tuple[Finding, ...]
    policy_results: tuple[dict, ...]
    decision: Decision
    severity: Severity
    recommendation: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        required_strings = {
            "schema_version": self.schema_version,
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "skill_version": self.skill_version,
            "source": self.source,
            "recommendation": self.recommendation,
        }
        for field_name, value in required_strings.items():
            if not isinstance(value, str) or not value:
                raise ValueError(f"Assessment.{field_name} must be a non-empty string")
        if self.recommendation not in RECOMMENDATIONS:
            raise ValueError(
                f"Assessment.recommendation must be one of {sorted(RECOMMENDATIONS)}, "
                f"got {self.recommendation!r}"
            )
        for tuple_field_name, tuple_value in (
            ("declared_capabilities", self.declared_capabilities),
            ("static_capabilities", self.static_capabilities),
            ("runtime_capabilities", self.runtime_capabilities),
        ):
            if not isinstance(tuple_value, tuple) or not all(
                isinstance(c, str) and c for c in tuple_value
            ):
                raise ValueError(f"Assessment.{tuple_field_name} must be a tuple of strings")
        if not isinstance(self.findings, tuple) or not all(
            isinstance(f, Finding) for f in self.findings
        ):
            raise TypeError("Assessment.findings must be a tuple of Finding")
        if not isinstance(self.policy_results, tuple) or not all(
            isinstance(p, dict) for p in self.policy_results
        ):
            raise TypeError("Assessment.policy_results must be a tuple of dict")
        if not isinstance(self.decision, Decision):
            raise TypeError("Assessment.decision must be a Decision instance")
        if not isinstance(self.severity, Severity):
            raise TypeError("Assessment.severity must be a Severity")
