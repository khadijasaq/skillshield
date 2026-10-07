"""Controlled-execution result model (docs/product-spec.md §15, §21).

Runtime observation is not proof of absence: a capability missing from
``runtime_capabilities`` only means it was not observed during this one
controlled execution, not that the skill can never do it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from skillshield.core.models.evidence import Evidence


class ExecutionStatus(str, Enum):
    """The outcome of one controlled-execution attempt."""

    OK = "ok"
    TIMEOUT = "timeout"
    CRASHED = "crashed"
    NO_ENTRYPOINT = "no_entrypoint"


@dataclass(frozen=True)
class ExecutionResult:
    """What happened when SkillShield ran a skill's entrypoint under
    controlled execution, and what runtime evidence was collected."""

    status: ExecutionStatus
    runtime_capabilities: frozenset[str] = frozenset()
    events: tuple[Evidence, ...] = ()
    duration_seconds: float = 0.0
    exit_code: int | None = None
    failure_reason: str | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, ExecutionStatus):
            raise TypeError("ExecutionResult.status must be an ExecutionStatus")
        if not isinstance(self.runtime_capabilities, frozenset):
            raise TypeError("ExecutionResult.runtime_capabilities must be a frozenset")
        if not isinstance(self.events, tuple) or not all(
            isinstance(e, Evidence) for e in self.events
        ):
            raise TypeError("ExecutionResult.events must be a tuple of Evidence")
        if not isinstance(self.duration_seconds, (int, float)):
            raise TypeError("ExecutionResult.duration_seconds must be a number")
        if self.exit_code is not None and not isinstance(self.exit_code, int):
            raise TypeError("ExecutionResult.exit_code must be an int or None")
        if self.failure_reason is not None and not isinstance(self.failure_reason, str):
            raise TypeError("ExecutionResult.failure_reason must be a string or None")
