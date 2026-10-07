"""Finding and Severity models (docs/product-spec.md §18; docs/conformance-rules.md).

Finding terminology must describe observable evidence. SkillShield must
never label a skill "malicious" simply because a finding exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FindingType(str, Enum):
    """The only finding types SkillShield produces (docs/product-spec.md §18)."""

    UNDECLARED_CAPABILITY = "UNDECLARED_CAPABILITY"
    STATIC_RUNTIME_MISMATCH = "STATIC_RUNTIME_MISMATCH"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    INVALID_DECLARATION = "INVALID_DECLARATION"
    ANALYSIS_FAILURE = "ANALYSIS_FAILURE"
    EXECUTION_FAILURE = "EXECUTION_FAILURE"


class Severity(str, Enum):
    """Deterministic severity levels, ordered low to high."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


_SEVERITY_ORDER = (Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL)


def severity_rank(severity: Severity) -> int:
    """An orderable rank for a Severity, low to high."""
    return _SEVERITY_ORDER.index(severity)


@dataclass(frozen=True)
class PolicyInfo:
    """Policy context attached to a finding that involves a policy decision."""

    policy_name: str
    permitted: bool

    def __post_init__(self) -> None:
        if not isinstance(self.policy_name, str) or not self.policy_name:
            raise ValueError("PolicyInfo.policy_name must be a non-empty string")
        if not isinstance(self.permitted, bool):
            raise TypeError("PolicyInfo.permitted must be a bool")


@dataclass(frozen=True)
class Finding:
    """An observable discrepancy, violation, or analysis problem.

    A finding describes evidence; it never asserts that a skill is
    malicious.
    """

    finding_type: FindingType
    severity: Severity
    explanation: str
    capability: str | None = None
    evidence: tuple = field(default_factory=tuple)
    source_location: str | None = None
    policy_info: PolicyInfo | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.finding_type, FindingType):
            raise TypeError("Finding.finding_type must be a FindingType")
        if not isinstance(self.severity, Severity):
            raise TypeError("Finding.severity must be a Severity")
        if not isinstance(self.explanation, str) or not self.explanation:
            raise ValueError("Finding.explanation must be a non-empty string")
        if not isinstance(self.evidence, tuple):
            raise TypeError("Finding.evidence must be a tuple of Evidence")
        if self.capability is not None and not isinstance(self.capability, str):
            raise TypeError("Finding.capability must be a string or None")
        if self.source_location is not None and not isinstance(self.source_location, str):
            raise TypeError("Finding.source_location must be a string or None")
        if self.policy_info is not None and not isinstance(self.policy_info, PolicyInfo):
            raise TypeError("Finding.policy_info must be a PolicyInfo or None")
