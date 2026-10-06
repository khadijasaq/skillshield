"""Controlled execution via a restricted subprocess (second milestone, Phase 3).

IMPORTANT SECURITY LIMITATION — read before using this against anything
other than the fixed reference testbed skill this milestone targets.

This is a research/testbed execution mechanism, not a secure sandbox for
arbitrary untrusted or malicious code. It provides:

  * a separate OS process (the skill's code does not share the calling
    Python interpreter's memory/state);
  * a dedicated, disposable temporary working directory;
  * a hard wall-clock timeout, after which the process is killed;
  * a minimal, explicitly-constructed environment (not the full inherited
    parent environment);
  * capability mediation through `_runner.py`'s self-contained broker —
    the assessed skill's code never gets real, ambient filesystem/network/
    OS access; every `ctx.tasks` / `ctx.files` / `ctx.net` / `ctx.env` call
    is intercepted and recorded, exactly as the real application's own
    broker does (see Phase 1 inspection notes in `adapter.py`).

It does **not** provide:

  * OS-level resource limits (CPU, memory, open-file-descriptor caps).
    `resource.setrlimit` is POSIX-only; this implementation runs on
    Windows (see this repository's environment), where no equivalent is
    applied in this milestone. This is a genuine, stated gap, not an
    oversight — `docs/downloaded-skill-assessment-plan.md` Phase 3
    anticipates applying such limits "where the host OS supports it" and
    this host does not, for the mechanism actually used here;
  * filesystem isolation below the Python level: if the assessed skill's
    code imports `os`/`open`/`socket`/`subprocess` directly (bypassing the
    `ctx` broker entirely, the way `backend/app/monitor/audit_hook.py`'s
    "process-wide watcher" is designed to catch in the real app), nothing
    in *this* implementation stops it — there is no OS-level sandbox,
    seccomp profile, or container boundary underneath the subprocess;
  * network isolation: the restricted environment does not block outbound
    sockets at the OS level. `_runner.py`'s NetBroker only intercepts
    calls made *through* `ctx.net`; a skill that imported `socket`/`httpx`
    directly could still reach the real network from this process.

Given these gaps, this mechanism is deliberately run in this milestone
only against the fixed reference testbed skill
(`docs/downloaded-skill-assessment-spec.md` §4.4, §12), whose real,
unmodified source has already been read and is known not to import
`os`/`socket`/`subprocess`/`httpx` directly (confirmed during Phase 1/2
inspection — see the static-analysis findings, which found none of those
patterns for `task_insights`). It must not be treated as safe to run
against arbitrary, unvetted skills.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from agentic_conformance.execution.handle import ExecutionHandle

_RUNNER_PATH = Path(__file__).resolve().parent / "_runner.py"

#: A small, believable starter task list — the same *shape* the real app's
#: own `seed.py` uses (id, title, notes, done, created_at, completed_at) —
#: used only because the assessed skill genuinely needs *some* task data to
#: operate on. This is sandbox setup data, not a fabricated observation:
#: what is observed and recorded is the skill's own real behavior against
#: it (which brokers it calls, with what arguments), never invented.
DEFAULT_TASKS_SEED: tuple[dict[str, Any], ...] = (
    {"id": "tsk-1", "title": "Renew passport", "notes": "", "done": False,
     "created_at": "2026-09-01T00:00:00.000Z", "completed_at": None},
    {"id": "tsk-2", "title": "Book dentist check-up", "notes": "", "done": False,
     "created_at": "2026-09-10T00:00:00.000Z", "completed_at": None},
    {"id": "tsk-3", "title": "Reply to the landlord", "notes": "", "done": True,
     "created_at": "2026-09-15T00:00:00.000Z", "completed_at": "2026-09-16T00:00:00.000Z"},
)

_DEFAULT_TIMEOUT_SECONDS = 30.0


def _snapshot(root: Path) -> dict[Path, float]:
    return {p: p.stat().st_mtime for p in root.rglob("*") if p.is_file()}


def _minimal_env() -> dict[str, str]:
    """A deliberately small environment — not the full inherited parent
    environment, so real host secrets are not ambiently available to the
    assessed skill's process even though no broker mediates `os.environ`
    directly (see the module docstring's stated gaps)."""
    keep = {}
    for key in ("SYSTEMROOT", "PATH", "PATHEXT", "TEMP", "TMP"):
        if key in os.environ:
            keep[key] = os.environ[key]
    return keep


def execute(
    skill_id: str,
    entry_file: Path,
    entry_attr: str,
    params: dict[str, Any] | None = None,
    *,
    tasks_seed: tuple[dict[str, Any], ...] = DEFAULT_TASKS_SEED,
    env_allowed: dict[str, str] | None = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
) -> ExecutionHandle:
    """Run one real skill's real entrypoint in a restricted subprocess.

    `entry_file`/`entry_attr` are the actual runtime entry point resolved
    by `adapters.vuln_agentic_skills_app.adapter.resolve_entrypoint` from
    the skill's real manifest — never invented here.
    """
    invocation_id = f"inv-{skill_id}-{int(time.time() * 1000)}"
    workdir = Path(tempfile.mkdtemp(prefix="skillshield-exec-"))
    data_root = workdir / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "tasks.json").write_text(json.dumps(list(tasks_seed)), encoding="utf-8")

    before = _snapshot(workdir)

    config = {"env_allowed": dict(env_allowed or {})}
    argv = [
        sys.executable, "-u", str(_RUNNER_PATH),
        str(entry_file), entry_attr,
        json.dumps(params or {}), json.dumps(config),
    ]

    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv, cwd=workdir, env=_minimal_env(), capture_output=True,
            text=True, timeout=timeout_seconds, check=False,
        )
        duration = time.monotonic() - started
        after = _snapshot(workdir)
        changed = tuple(sorted(p for p, mtime in after.items() if before.get(p) != mtime))

        try:
            payload = json.loads(completed.stdout)
        except (json.JSONDecodeError, ValueError):
            return ExecutionHandle(
                skill_id=skill_id, invocation_id=invocation_id, outcome="error",
                exit_code=completed.returncode, duration_seconds=duration,
                stdout=completed.stdout, stderr=completed.stderr,
                working_directory=workdir, created_or_modified_files=changed,
                observations=(), summary="", data=None,
                error="Runner produced no parseable result (see stderr).",
            )

        return ExecutionHandle(
            skill_id=skill_id, invocation_id=invocation_id,
            outcome=payload.get("outcome", "error"),
            exit_code=completed.returncode, duration_seconds=duration,
            stdout=completed.stdout, stderr=completed.stderr,
            working_directory=workdir, created_or_modified_files=changed,
            observations=tuple(payload.get("observations", ())),
            summary=payload.get("summary", ""), data=payload.get("data"),
            error=payload.get("error"),
        )
    except subprocess.TimeoutExpired as timeout_error:
        duration = time.monotonic() - started
        after = _snapshot(workdir)
        changed = tuple(sorted(p for p, mtime in after.items() if before.get(p) != mtime))
        return ExecutionHandle(
            skill_id=skill_id, invocation_id=invocation_id, outcome="timeout",
            exit_code=None, duration_seconds=duration,
            stdout=timeout_error.stdout or "", stderr=timeout_error.stderr or "",
            working_directory=workdir, created_or_modified_files=changed,
            observations=(), summary="", data=None,
            error=f"Execution exceeded {timeout_seconds}s and was terminated.",
        )
