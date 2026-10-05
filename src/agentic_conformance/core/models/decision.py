"""Canonical Decision model (docs/spec.md §7.5)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

SCHEMA_VERSION = "1.0"


class DecisionValue(str, Enum):
    """The standardized outcome of a conformance evaluation."""

    ALLOW = "ALLOW"
    FLAG = "FLAG"
    DENY = "DENY"


class ReasonCode(str, Enum):
    """Standardized reason codes for a conformance Decision."""

    INVALID_DECLARATION = "INVALID_DECLARATION"
    MISSING_DECLARATION = "MISSING_DECLARATION"
    UNDECLARED_CAPABILITY = "UNDECLARED_CAPABILITY"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    STATIC_RUNTIME_MISMATCH = "STATIC_RUNTIME_MISMATCH"
    INVALID_EVENT = "INVALID_EVENT"
    UNKNOWN_CAPABILITY = "UNKNOWN_CAPABILITY"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"


@dataclass(frozen=True)
class Decision:
    """The standardized output of a conformance evaluation."""

    skill_id: str
    value: DecisionValue
    reason_code: ReasonCode | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise ValueError("Decision.schema_version must be a non-empty string")
        if not isinstance(self.skill_id, str) or not self.skill_id:
            raise ValueError("Decision.skill_id must be a non-empty string")
        if not isinstance(self.value, DecisionValue):
            raise TypeError("Decision.value must be a DecisionValue")
        if self.reason_code is not None and not isinstance(self.reason_code, ReasonCode):
            raise ValueError("Decision.reason_code must be a ReasonCode or None")
