"""Tests for static-analysis traversal/orchestration (second milestone, Phase 2)."""

from __future__ import annotations

import pytest

from agentic_conformance.analysis.static.analyzer import analyze, static_capability_set


def test_analyze_fixture_directory_attributes_findings_to_file_and_line(tmp_path):
    skill_file = tmp_path / "skill.py"
    skill_file.write_text(
        "def run(ctx, params):\n"
        "    tasks = ctx.tasks.list('all')\n"
        "    ctx.net.post('http://127.0.0.1:8000/mock/collector', json={})\n"
        "    return tasks\n",
        encoding="utf-8",
    )

    findings = analyze(tmp_path)

    assert {f.capability for f in findings} == {"task.read", "network.egress"}
    by_capability = {f.capability: f for f in findings}
    assert by_capability["task.read"].file == "skill.py"
    assert by_capability["task.read"].location == 2
    assert by_capability["network.egress"].location == 3


def test_analyze_no_match_behavior_is_empty_not_error(tmp_path):
    skill_file = tmp_path / "skill.py"
    skill_file.write_text("def run(ctx, params):\n    return 'ok'\n", encoding="utf-8")

    findings = analyze(tmp_path)

    assert findings == []


def test_analyze_missing_source_root_raises_filenotfounderror(tmp_path):
    missing = tmp_path / "does_not_exist"

    with pytest.raises(FileNotFoundError):
        analyze(missing)


def test_analyze_malformed_encoding_does_not_crash(tmp_path):
    """A file containing non-UTF-8 bytes must not abort analysis of the directory."""
    skill_file = tmp_path / "skill.py"
    skill_file.write_bytes(b"def run(ctx, params):\n    x = b'\xff\xfe'\n    return x\n")

    findings = analyze(tmp_path)  # must not raise

    assert isinstance(findings, list)


def test_analyze_traverses_multiple_files_deterministically(tmp_path):
    (tmp_path / "a.py").write_text("ctx.tasks.list('all')\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("ctx.files.read('x')\n", encoding="utf-8")

    first = analyze(tmp_path)
    second = analyze(tmp_path)

    assert first == second
    assert {f.file for f in first} == {"a.py", "b.py"}


def test_static_capability_set_deduplicates():
    from agentic_conformance.analysis.static.analyzer import StaticFinding

    findings = [
        StaticFinding("task.read", "skill.py", 1, "task-broker-read", "x"),
        StaticFinding("task.read", "skill.py", 5, "task-broker-read", "x"),
        StaticFinding("network.egress", "skill.py", 2, "net-broker-call", "x"),
    ]

    assert static_capability_set(findings) == {"task.read", "network.egress"}
