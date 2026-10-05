"""Canonical Security Event model (docs/spec.md §7.3)."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_conformance.core.models.capability import Capability

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Actor:
    """Who/what performed the observed action."""

    type: str
    id: str

    def __post_init__(self) -> None:
        if not isinstance(self.type, str) or not self.type:
            raise ValueError("Actor.type must be a non-empty string")
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("Actor.id must be a non-empty string")


@dataclass(frozen=True)
class Action:
    """The capability-bearing action that was observed."""

    capability: Capability
    operation: str

    def __post_init__(self) -> None:
        if not isinstance(self.capability, Capability):
            raise TypeError("Action.capability must be a Capability instance")
        if not isinstance(self.operation, str) or not self.operation:
            raise ValueError("Action.operation must be a non-empty string")


@dataclass(frozen=True)
class Target:
    """What the action was performed against."""

    type: str
    identifier: str

    def __post_init__(self) -> None:
        if not isinstance(self.type, str) or not self.type:
            raise ValueError("Target.type must be a non-empty string")
        if not isinstance(self.identifier, str) or not self.identifier:
            raise ValueError("Target.identifier must be a non-empty string")


@dataclass(frozen=True)
class SecurityEvent:
    """Canonical representation of a lifecycle/runtime event (docs/spec.md §7.3)."""

    event_id: str
    timestamp: str
    event_type: str
    context: dict
    actor: Actor
    action: Action
    target: Target
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        required_strings = {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
        }
        for field_name, value in required_strings.items():
            if not isinstance(value, str) or not value:
                raise ValueError(f"SecurityEvent.{field_name} must be a non-empty string")
        if not isinstance(self.context, dict):
            raise TypeError("SecurityEvent.context must be a dict")
        if not isinstance(self.actor, Actor):
            raise TypeError("SecurityEvent.actor must be an Actor instance")
        if not isinstance(self.action, Action):
            raise TypeError("SecurityEvent.action must be an Action instance")
        if not isinstance(self.target, Target):
            raise TypeError("SecurityEvent.target must be a Target instance")
