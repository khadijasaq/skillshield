"""Canonical Evidence model (docs/product-spec.md §12, §20).

Static evidence means "the source code indicates this capability may be
used" -- never that it definitely occurs at runtime. Runtime evidence means
"this was observed during one controlled execution" -- its absence never
proves a capability can never occur. Both constraints are enforced only by
convention/wording in this milestone (docs/product-spec.md §14, §15); there
is no separate confidence/weighting mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EvidenceSource(str, Enum):
    """The origin of a piece of conformance evidence."""

    DECLARATION = "declaration"
    STATIC = "static"
    RUNTIME = "runtime"
    POLICY = "policy"


@dataclass(frozen=True)
class Evidence:
    """A single piece of information supporting a finding."""

    source: EvidenceSource
    capability: str
    detail: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.source, EvidenceSource):
            raise TypeError("Evidence.source must be an EvidenceSource")
        if not isinstance(self.capability, str) or not self.capability:
            raise ValueError("Evidence.capability must be a non-empty string")
        if not isinstance(self.detail, dict):
            raise TypeError("Evidence.detail must be a dict")
