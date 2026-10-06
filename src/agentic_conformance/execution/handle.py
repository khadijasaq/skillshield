"""The structured result of one controlled execution (second milestone, Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

#: "ok"     - the skill's entrypoint returned normally.
#: "error"  - the skill's entrypoint raised, or could not be loaded/called.
#: "timeout"- the process did not finish within the configured timeout and was killed.
Outcome = Literal["ok", "error", "timeout"]


@dataclass(frozen=True)
class ExecutionHandle:
    """Everything observed about one controlled execution of one skill.

    `observations` is the raw, native-shaped observation list (mirroring
    the real testbed's own `Observation` record — see
    `backend/app/monitor/observations.py` — discovered during Phase 1
    inspection) that Phase 4's runtime monitor converts into canonical
    `SecurityEvent` instances. `core/` never sees this type.
    """

    skill_id: str
    invocation_id: str
    outcome: Outcome
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    working_directory: Path
    created_or_modified_files: tuple[Path, ...]
    observations: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    summary: str = ""
    data: dict[str, Any] | None = None
    error: str | None = None
