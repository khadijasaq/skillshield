"""Integration tests for the restricted-subprocess controlled execution
mechanism (second milestone, Phase 3).

Covers deterministic synthetic fixtures (invalid input, timeout, process
failure — edge cases that must not depend on any specific real skill) and
the real `task_insights` skill (the genuine, mandatory real-data path).
"""

from __future__ import annotations

from pathlib import Path

from agentic_conformance.adapters.vuln_agentic_skills_app.adapter import (
    load_manifest,
    resolve_entrypoint,
)
from agentic_conformance.execution.subprocess_sandbox import execute

_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "vuln_agentic_skills_app"
    / "task_insights"
)


# ---------------------------------------------------------------------------
# Deterministic synthetic fixtures — edge cases
# ---------------------------------------------------------------------------


def test_execute_invalid_entrypoint_produces_error_outcome(tmp_path):
    skill_file = tmp_path / "skill.py"
    skill_file.write_text("def run(ctx, params):\n    return 'ok'\n", encoding="utf-8")

    handle = execute("synthetic", skill_file, "does_not_exist", {})

    assert handle.outcome == "error"
    assert handle.error is not None


def test_execute_process_failure_is_captured_cleanly(tmp_path):
    skill_file = tmp_path / "skill.py"
    skill_file.write_text(
        "def run(ctx, params):\n    raise ValueError('boom')\n", encoding="utf-8"
    )

    handle = execute("synthetic", skill_file, "run", {})

    assert handle.outcome == "error"
    assert "boom" in (handle.error or "")
    # A crashing skill must not crash the controlled-execution mechanism itself.
    assert handle.exit_code == 0


def test_execute_timeout_is_enforced_and_reported(tmp_path):
    skill_file = tmp_path / "skill.py"
    skill_file.write_text(
        "import time\n\n\ndef run(ctx, params):\n    time.sleep(10)\n    return 'done'\n",
        encoding="utf-8",
    )

    handle = execute("synthetic", skill_file, "run", {}, timeout_seconds=1.0)

    assert handle.outcome == "timeout"
    assert handle.exit_code is None
    assert "timeout" in (handle.error or "").lower() or "exceeded" in (handle.error or "").lower()


def test_execute_captures_file_writes(tmp_path):
    skill_file = tmp_path / "skill.py"
    skill_file.write_text(
        "def run(ctx, params):\n"
        "    ctx.files.write('data/output.txt', 'hello')\n"
        "    return 'done'\n",
        encoding="utf-8",
    )

    handle = execute("synthetic", skill_file, "run", {})

    assert handle.outcome == "ok"
    written_names = {p.name for p in handle.created_or_modified_files}
    assert "output.txt" in written_names


# ---------------------------------------------------------------------------
# Real testbed integration path — mandatory
# ---------------------------------------------------------------------------


def test_execute_real_task_insights_skill_runs_successfully():
    manifest = load_manifest(_FIXTURE_DIR)
    entry_file, entry_attr = resolve_entrypoint(_FIXTURE_DIR, manifest)

    handle = execute("task_insights", entry_file, entry_attr, {})

    assert handle.outcome == "ok"
    assert handle.exit_code == 0
    assert handle.error is None
    assert handle.summary  # the real skill always returns a non-empty summary
    assert handle.data is not None
    assert "source_bytes" in handle.data  # unique to task_insights's real return shape


def test_execute_real_task_insights_skill_genuinely_observes_undeclared_actions():
    """The real skill genuinely calls ctx.files.read and ctx.net.post — this must be
    observed from actually running it, not asserted from reading its source again."""
    manifest = load_manifest(_FIXTURE_DIR)
    entry_file, entry_attr = resolve_entrypoint(_FIXTURE_DIR, manifest)

    handle = execute("task_insights", entry_file, entry_attr, {})

    observed_capabilities = {obs["capability"] for obs in handle.observations}
    assert "task.read" in observed_capabilities
    assert "fs.read" in observed_capabilities
    assert "net.outbound" in observed_capabilities
