"""Tests for deterministic static-analysis pattern detectors (second milestone, Phase 2)."""

from __future__ import annotations

from agentic_conformance.analysis.static.detectors import (
    detect_env_read,
    detect_filesystem_read,
    detect_filesystem_write,
    detect_network_broker_call,
    detect_process_execution,
    detect_task_read,
    detect_task_write,
    detect_url_literal,
    run_all_detectors,
)


def test_detect_task_read_matches_list_and_get():
    text = "tasks = ctx.tasks.list('all')\none = ctx.tasks.get(task_id)\n"
    matches = detect_task_read(text)
    assert [m.line for m in matches] == [1, 2]
    assert all(m.capability == "task.read" for m in matches)


def test_detect_task_read_no_match_on_unrelated_text():
    assert detect_task_read("tasks = []\n") == []


def test_detect_task_write_matches_add_update_delete():
    text = "ctx.tasks.add('x')\nctx.tasks.update(id)\nctx.tasks.delete(id)\n"
    matches = detect_task_write(text)
    assert len(matches) == 3
    assert all(m.capability == "task.write" for m in matches)


def test_detect_filesystem_read_matches_files_read():
    matches = detect_filesystem_read("raw = ctx.files.read(TASK_FILE)\n")
    assert len(matches) == 1
    assert matches[0].capability == "filesystem.read"
    assert matches[0].line == 1


def test_detect_filesystem_write_matches_files_write():
    matches = detect_filesystem_write("ctx.files.write(path, content)\n")
    assert len(matches) == 1
    assert matches[0].capability == "filesystem.write"


def test_detect_network_broker_call_matches_get_and_post():
    text = "ctx.net.get(url)\nctx.net.post(url, json={})\n"
    matches = detect_network_broker_call(text)
    assert len(matches) == 2
    assert all(m.capability == "network.egress" for m in matches)


def test_detect_env_read_matches_env_get():
    matches = detect_env_read("value = ctx.env.get('TASKBOT_FOO')\n")
    assert len(matches) == 1
    assert matches[0].capability == "env.read"


def test_detect_process_execution_matches_import_and_call():
    text = "import subprocess\nsubprocess.run(['ls'])\n"
    matches = detect_process_execution(text)
    assert len(matches) == 2
    assert all(m.capability == "process.execute" for m in matches)


def test_detect_process_execution_no_match_on_unrelated_import():
    assert detect_process_execution("import json\n") == []


def test_detect_url_literal_matches_http_and_https():
    text = 'url = "http://127.0.0.1:8000/mock/collector"\nother = "https://example.com"\n'
    matches = detect_url_literal(text)
    assert len(matches) == 2
    assert all(m.capability == "network.egress" for m in matches)


def test_run_all_detectors_on_clean_source_finds_nothing():
    """A skill that genuinely does none of these things must report no findings."""
    clean_source = (
        "def run(ctx, params):\n"
        "    return {'summary': 'nothing to see here'}\n"
    )
    assert run_all_detectors(clean_source) == []


def test_run_all_detectors_is_deterministic():
    text = "ctx.tasks.list('all')\nctx.files.read('x')\nctx.net.post(url)\n"
    first = run_all_detectors(text)
    second = run_all_detectors(text)
    assert first == second
    assert [m.capability for m in first] == ["task.read", "filesystem.read", "network.egress"]
