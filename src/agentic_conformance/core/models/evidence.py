"""Canonical Evidence model (docs/spec.md §7.4).

Evidence is treated as present/absent information grouped by source, not as
a scored or weighted signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

SCHEMA_VERSION = "1.0"


class EvidenceSource(str, Enum):
    """The origin of a piece of conformance evidence."""

    DECLARATION = "declaration"
    STATIC = "static"
    RUNTIME = "runtime"
    POLICY = "policy"


@dataclass(frozen=True)
class Evidence:
    """A single piece of information supporting a conformance evaluation."""

    source: EvidenceSource
    skill_id: str
    schema_version: str = SCHEMA_VERSION
    data: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise ValueError("Evidence.schema_version must be a non-empty string")
        if not isinstance(self.skill_id, str) or not self.skill_id:
            raise ValueError("Evidence.skill_id must be a non-empty string")
        if not isinstance(self.source, EvidenceSource):
            raise TypeError("Evidence.source must be an EvidenceSource")
        if not isinstance(self.data, dict):
            raise TypeError("Evidence.data must be a dict")
