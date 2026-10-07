"""Tests for the ExecutionHandle structured result (second milestone, Phase 3)."""

from __future__ import annotations

from pathlib import Path

from agentic_conformance.execution.handle import ExecutionHandle


def test_execution_handle_construction_minimal():
    handle = ExecutionHandle(
        skill_id="task_insights",
        invocation_id="inv-1",
        outcome="ok",
        exit_code=0,
        duration_seconds=0.01,
        stdout="{}",
        stderr="",
        working_directory=Path("/tmp/x"),
        created_or_modified_files=(),
    )

    assert handle.outcome == "ok"
    assert handle.observations == ()
    assert handle.data is None
    assert handle.error is None


def test_execution_handle_carries_observations_and_data():
    handle = ExecutionHandle(
        skill_id="task_insights",
        invocation_id="inv-2",
        outcome="ok",
        exit_code=0,
        duration_seconds=0.02,
        stdout="{}",
        stderr="",
        working_directory=Path("/tmp/x"),
        created_or_modified_files=(Path("/tmp/x/data/tasks.json"),),
        observations=({"capability": "task.read", "resource": "*"},),
        summary="3 tasks",
        data={"total": 3},
    )

    assert len(handle.observations) == 1
    assert handle.observations[0]["capability"] == "task.read"
    assert handle.data == {"total": 3}
