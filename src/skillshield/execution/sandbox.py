"""Controlled execution of a skill's entrypoint (docs/product-spec.md §21).

This is a restricted subprocess, not a secure sandbox -- see
SECURITY_LIMITATIONS.md for exactly what is and is not guaranteed. It:

* copies the ingested artifact into a fresh temp directory before running
  anything, so the skill cannot mutate the original ingested content;
* strips the subprocess's environment down to a small allow-list, instead
  of inheriting the operator's full environment (reduces, but does not
  eliminate, incidental credential exposure);
* enforces a wall-clock timeout only -- there is no CPU/memory limiting;
* on timeout, kills the whole process tree it spawned, best-effort
  (``taskkill /F /T`` on Windows, a process-group signal on POSIX);
* reads back whatever runtime-event evidence the harness managed to flush
  before it was killed, so a timed-out or crashed run still yields partial
  evidence rather than none.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from skillshield.core.models.artifact import SkillArtifact
from skillshield.core.models.evidence import Evidence, EvidenceSource
from skillshield.core.models.skill import Skill
from skillshield.execution.result import ExecutionResult, ExecutionStatus

_OUTPUT_TAIL_CHARS = 2000


def _minimal_environment() -> dict[str, str]:
    """A small environment allow-list for the executed skill -- not the
    operator's full ``os.environ`` (docs/batch-reports/batch-3.md)."""
    env: dict[str, str] = {}
    for key in ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "PATHEXT"):
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _entry_attr_exists(working_path: str, entry_file: str, entry_attr: str) -> bool:
    """Cheap static check for whether ``entry_attr`` is defined at module
    level in ``entry_file``, so a manifest pointing at a nonexistent
    function is reported as NO_ENTRYPOINT without spawning a subprocess
    (rather than only discovered as a runtime AttributeError crash)."""
    try:
        source = (Path(working_path) / entry_file).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == entry_attr:
                return True
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == entry_attr:
                    return True
    return False


def _resolve_entrypoint(skill: Skill, working_path: str) -> tuple[str, str] | None:
    if skill.declaration is None or not skill.declaration.entrypoint:
        return None
    entrypoint = skill.declaration.entrypoint
    if ":" not in entrypoint:
        return None
    entry_file, entry_attr = entrypoint.split(":", 1)
    entry_file = entry_file.strip()
    entry_attr = entry_attr.strip()
    if not entry_file or not entry_attr:
        return None
    if entry_file not in skill.source_files:
        return None
    if not _entry_attr_exists(working_path, entry_file, entry_attr):
        return None
    return entry_file, entry_attr


def _read_events(events_path: Path) -> tuple[frozenset[str], tuple[Evidence, ...], str | None]:
    """Parse whatever JSONL the harness managed to write, tolerating a
    truncated final line (the process may have been killed mid-write)."""
    capabilities: set[str] = set()
    evidence: list[Evidence] = []
    crash_reason: str | None = None
    if not events_path.exists():
        return frozenset(), (), None

    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # partial/truncated line from a killed process -- not fatal
        if "capability" in record:
            capability = record["capability"]
            capabilities.add(capability)
            evidence.append(Evidence(EvidenceSource.RUNTIME, capability, detail=record.get("detail", {})))
        elif record.get("status") == "crashed":
            crash_reason = record.get("error")

    return frozenset(capabilities), tuple(evidence), crash_reason


def _kill_tree(proc: subprocess.Popen) -> None:
    """Best-effort termination of the whole process tree (see
    SECURITY_LIMITATIONS.md -- this is not guaranteed on every platform)."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
    else:
        import signal

        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _popen_kwargs() -> dict:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def execute(
    skill: Skill,
    artifact: SkillArtifact,
    *,
    timeout_seconds: float = 10.0,
) -> ExecutionResult:
    """Run ``skill``'s declared entrypoint under controlled execution and
    return the runtime evidence collected."""
    resolved = _resolve_entrypoint(skill, artifact.working_path)
    if resolved is None:
        return ExecutionResult(
            status=ExecutionStatus.NO_ENTRYPOINT,
            failure_reason="No usable entrypoint (missing declaration, missing "
            "entrypoint field, entrypoint file not among the skill's source "
            "files, or the declared function/class is not defined there).",
        )
    entry_file, entry_attr = resolved

    run_dir = Path(tempfile.mkdtemp(prefix="skillshield-exec-"))
    exec_tree = run_dir / "skill"
    shutil.copytree(artifact.working_path, exec_tree)
    events_path = run_dir / "events.jsonl"
    events_path.touch()

    env = _minimal_environment()
    cmd = [
        sys.executable,
        "-B",  # never write .pyc bytecode caches -- see docstring note on import noise
        "-m",
        "skillshield.execution.harness",
        str(exec_tree),
        entry_file,
        entry_attr,
        str(events_path),
    ]

    start = time.monotonic()
    timed_out = False
    exit_code: int | None = None
    stdout = ""
    stderr = ""
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(exec_tree),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **_popen_kwargs(),
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(proc)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", ""
            exit_code = proc.returncode
    finally:
        duration = time.monotonic() - start

    runtime_capabilities, events, crash_reason = _read_events(events_path)

    try:
        shutil.rmtree(run_dir, ignore_errors=True)
    except OSError:
        pass  # best-effort cleanup -- a locked file must not fail the assessment

    if timed_out:
        status = ExecutionStatus.TIMEOUT
        failure_reason = f"Execution exceeded the {timeout_seconds}s timeout and was terminated."
    elif exit_code == 0:
        status = ExecutionStatus.OK
        failure_reason = None
    else:
        status = ExecutionStatus.CRASHED
        failure_reason = crash_reason or f"Entrypoint process exited with code {exit_code}."

    return ExecutionResult(
        status=status,
        runtime_capabilities=runtime_capabilities,
        events=events,
        duration_seconds=duration,
        exit_code=exit_code,
        failure_reason=failure_reason,
        stdout_tail=(stdout or "")[-_OUTPUT_TAIL_CHARS:],
        stderr_tail=(stderr or "")[-_OUTPUT_TAIL_CHARS:],
    )
