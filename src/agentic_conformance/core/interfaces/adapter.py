"""Generic adapter contract (docs/spec.md §10).

Adapter = translation + integration.
Core = conformance evaluation.

An adapter translates a host product's native representations into
canonical models and reaches the conformance core only through a
ConformanceAPI. It must never implement conformance rules itself.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agentic_conformance.core.interfaces.conformance_api import ConformanceAPI
from agentic_conformance.core.models import Capability, Decision, SecurityEvent, Skill


class ProductAdapter(ABC):
    """Base contract for translating a host product into canonical models."""

    def __init__(self, conformance_api: ConformanceAPI) -> None:
        self._conformance_api = conformance_api

    @abstractmethod
    def translate_skill(self, native_skill: Any) -> Skill:
        """Translate native skill/declaration information into a canonical Skill."""

    @abstractmethod
    def normalize_capability(self, native_capability: Any) -> Capability:
        """Normalize a native capability into the canonical capability vocabulary."""

    @abstractmethod
    def translate_event(self, native_event: Any) -> SecurityEvent:
        """Translate a native runtime action into a canonical SecurityEvent."""

    def register(self, native_skill: Any) -> None:
        """Translate and register a native skill with the conformance core."""
        self._conformance_api.register_skill(self.translate_skill(native_skill))

    def observe(self, native_event: Any) -> None:
        """Translate and forward a native runtime action to the conformance core."""
        self._conformance_api.emit_event(self.translate_event(native_event))

    def evaluate(self, skill_id: str) -> Decision:
        """Request a standardized conformance decision from the core."""
        return self._conformance_api.evaluate(skill_id)
