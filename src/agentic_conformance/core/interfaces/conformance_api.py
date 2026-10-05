"""Generic integration contract (docs/spec.md §5).

Three in-process operations form the entire boundary between an adapter and
the conformance core. No networking, RPC, or API framework is introduced
here or anywhere else in this milestone.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agentic_conformance.core.models import Decision, SecurityEvent, Skill


class ConformanceAPI(ABC):
    """The integration contract adapters use to reach the conformance core."""

    @abstractmethod
    def register_skill(self, skill_profile: Skill) -> None:
        """Register a skill and its declaration with the conformance layer."""

    @abstractmethod
    def emit_event(self, security_event: SecurityEvent) -> None:
        """Provide a canonical security/lifecycle event to the conformance layer."""

    @abstractmethod
    def evaluate(self, skill_id: str) -> Decision:
        """Evaluate the currently available information for a skill."""
