"""Runs *inside* the controlled-execution subprocess (second milestone, Phase 3).

THIS FILE EXECUTES UNTRUSTED CODE. It is invoked as a standalone script
(`python -u _runner.py <entry_file> <entry_attr> <params_json> <config_json>`)
by `subprocess_sandbox.execute()`, in a dedicated temporary working
directory, under a timeout, with a restricted environment — never
imported by any other module in this codebase.

WHAT THIS DOES. It loads the real, unmodified skill entrypoint discovered
during Phase 1 inspection (`skill.py:run`, called with `(ctx, params)`,
exactly as the real app's `SkillHost.invoke()` calls it —
`backend/app/skills/host.py`) and calls it with a minimal, self-contained
capability broker (`ctx`) that this module implements itself.

WHY A SELF-CONTAINED BROKER, NOT THE REAL APP'S. The real skill's source
imports `from app.skills.context import SkillResult, CapabilityRefused`
(and, for this milestone's primary skill, `from app.skills.scope import
get_collector_url`). The real versions of those modules
(`backend/app/skills/context.py`, `backend/app/skills/scope.py`) are part
of a full FastAPI/pydantic/httpx application with its own on-disk task
store, settings, and collector service — depending on all of that here
would mean adding runtime dependencies this project's own discipline
(`docs/plan.md` "Implementation Practices — Minimalism") explicitly avoids,
and would mean a "controlled execution environment" built from the very
same application being assessed, which is circular for an independent
conformance tool. Instead, this module installs minimal, narrowly-scoped
stand-ins for exactly the two names (`SkillResult`, `CapabilityRefused`)
and one function (`get_collector_url`) the real skill code actually
imports — verified by inspecting the real source in Phase 1 — under the
same module path (`app.skills.context`, `app.skills.scope`), so the real,
byte-for-byte unmodified `skill.py` runs against them unchanged.

LIMITATION, STATED EXPLICITLY: this stand-in broker is self-contained
(its own seeded task list, its own temp-directory file roots, no real
HTTP dispatch — see NetBroker below) rather than the real application's
actual storage/collector. The *capability usage itself* (that the skill
called ctx.tasks.list, ctx.files.read, ctx.net.post, with these arguments)
is genuinely observed, not fabricated; only the *data behind the broker*
(the seeded task list, the absence of a real collector) is a minimal
fixture, not production state. Extending this broker to more skills than
the one this milestone targets (`task_insights`) may require adding more
stand-in names, which would be a documented, additive change — not a
silent one.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class _Observations:
    """The notebook this run writes to — same shape as the real app's
    `ObservationLog`/`Observation` (`backend/app/monitor/observations.py`):
    `seq, capability, resource, detail, outcome, refusal_reason, source,
    ts`. `invocation_id` and `skill_id` are added by the caller
    (`subprocess_sandbox.execute`), which already knows them."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def record(self, capability: str, resource: str, detail: dict[str, Any] | None = None,
               outcome: str = "ok", source: str = "broker") -> dict[str, Any]:
        entry = {
            "seq": len(self.entries) + 1,
            "capability": capability,
            "resource": resource,
            "detail": dict(detail or {}),
            "outcome": outcome,
            "refusal_reason": None,
            "source": source,
            "ts": _now_iso(),
        }
        self.entries.append(entry)
        return entry

    def mark_refused(self, entry: dict[str, Any], reason: str) -> None:
        entry["outcome"] = "refused"
        entry["refusal_reason"] = reason


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _install_compat_modules() -> tuple[type, type]:
    """Install minimal `app.skills.context` / `app.skills.scope` stand-ins.

    Returns (SkillResult, CapabilityRefused) so the broker below can raise
    the *same* exception class the real skill's `except CapabilityRefused`
    clause will catch.
    """

    class SkillResult:
        def __init__(self, summary: str, data: dict[str, Any] | None = None) -> None:
            self.summary = summary
            self.data = data

    class CapabilityRefused(Exception):
        def __init__(self, capability: str, resource: str, reason: str) -> None:
            super().__init__(f"{capability} on {resource!r} was refused: {reason}")
            self.capability = capability
            self.resource = resource
            self.reason = reason

    def get_collector_url(params: dict[str, Any] | None = None) -> str:
        base_url = ""
        if params:
            base_url = params.get("_self_url") or ""
        if not base_url:
            base_url = "http://127.0.0.1:8000"
        return f"{base_url}/mock/collector"

    app_module = types.ModuleType("app")
    skills_module = types.ModuleType("app.skills")
    context_module = types.ModuleType("app.skills.context")
    scope_module = types.ModuleType("app.skills.scope")

    context_module.SkillResult = SkillResult
    context_module.CapabilityRefused = CapabilityRefused
    scope_module.get_collector_url = get_collector_url

    app_module.skills = skills_module
    skills_module.context = context_module
    skills_module.scope = scope_module

    sys.modules["app"] = app_module
    sys.modules["app.skills"] = skills_module
    sys.modules["app.skills.context"] = context_module
    sys.modules["app.skills.scope"] = scope_module

    return SkillResult, CapabilityRefused


class _TaskBroker:
    """Minimal stand-in for the real app's TaskBroker — seeded JSON task list."""

    def __init__(self, log: _Observations, tasks: list[dict[str, Any]]) -> None:
        self._log = log
        self._tasks = tasks

    def list(self, scope: str = "all") -> list[dict[str, Any]]:
        self._log.record("task.read", "*", {"operation": "list", "scope": scope})
        if scope == "all":
            return list(self._tasks)
        want_done = scope == "done"
        return [t for t in self._tasks if bool(t.get("done")) == want_done]

    def get(self, task_id: str) -> dict[str, Any]:
        self._log.record("task.read", task_id, {"operation": "get"})
        for task in self._tasks:
            if task.get("id") == task_id:
                return dict(task)
        raise KeyError(task_id)

    def add(self, title: str, notes: str = "") -> dict[str, Any]:
        self._log.record("task.write", "*", {"operation": "add", "title": title})
        new_task = {"id": f"tsk-{len(self._tasks) + 1}", "title": title, "notes": notes,
                    "done": False, "created_at": _now_iso(), "completed_at": None}
        self._tasks.append(new_task)
        return dict(new_task)

    def update(self, task_id: str, **fields: Any) -> dict[str, Any]:
        self._log.record("task.write", task_id, {"operation": "update", "fields": sorted(fields)})
        for task in self._tasks:
            if task.get("id") == task_id:
                task.update(fields)
                return dict(task)
        raise KeyError(task_id)

    def delete(self, task_id: str) -> None:
        self._log.record("task.write", task_id, {"operation": "delete"})
        self._tasks[:] = [t for t in self._tasks if t.get("id") != task_id]


class _FileBroker:
    """Minimal stand-in for the real app's FileBroker — confined to one data root."""

    def __init__(self, log: _Observations, data_root: Path) -> None:
        self._log = log
        self._data_root = data_root.resolve()

    def _resolve(self, raw_path: str) -> Path:
        candidate = Path(raw_path)
        resolved = (candidate if candidate.is_absolute() else Path.cwd() / candidate).resolve()
        return resolved

    def read(self, path: str) -> str:
        entry = self._log.record("fs.read", str(path), {"operation": "read"})
        resolved = self._resolve(path)
        if not (resolved == self._data_root or resolved.is_relative_to(self._data_root)):
            self._log.mark_refused(entry, "path_outside_allowed_roots")
            raise sys.modules["app.skills.context"].CapabilityRefused(
                "fs.read", str(path), "path_outside_allowed_roots"
            )
        if not resolved.exists():
            self._log.mark_refused(entry, "file_not_found")
            raise sys.modules["app.skills.context"].CapabilityRefused(
                "fs.read", str(path), "file_not_found"
            )
        return resolved.read_text(encoding="utf-8", errors="replace")

    def write(self, path: str, content: str) -> None:
        entry = self._log.record("fs.write", str(path), {"operation": "write", "bytes": len(content)})
        resolved = self._resolve(path)
        if not (resolved == self._data_root or resolved.is_relative_to(self._data_root)):
            self._log.mark_refused(entry, "path_outside_allowed_roots")
            raise sys.modules["app.skills.context"].CapabilityRefused(
                "fs.write", str(path), "path_outside_allowed_roots"
            )
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")


class _BrokeredResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class _NetBroker:
    """Minimal stand-in for the real app's NetBroker.

    Faithfully RECORDS every attempted request (method, url). It then
    attempts a real loopback request only to local addresses, with a
    short timeout, and treats any failure (e.g. no listener on that port)
    as a normal, expected, recorded outcome rather than a crash — there is
    no real collector service running in this controlled environment.
    Non-local hosts are refused outright, exactly as the real app does.
    """

    _LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

    def __init__(self, log: _Observations, timeout_seconds: float = 2.0) -> None:
        self._log = log
        self._timeout_seconds = timeout_seconds

    def get(self, url: str) -> _BrokeredResponse:
        return self._request("GET", url, None)

    def post(self, url: str, json: dict[str, Any] | None = None) -> _BrokeredResponse:
        return self._request("POST", url, json)

    def _request(self, method: str, url: str, payload: dict[str, Any] | None) -> _BrokeredResponse:
        detail: dict[str, Any] = {"operation": method}
        entry = self._log.record("net.outbound", url, detail)

        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or hostname not in self._LOCAL_HOSTS:
            self._log.mark_refused(entry, "non_local_host")
            raise sys.modules["app.skills.context"].CapabilityRefused(
                "net.outbound", url, "non_local_host"
            )

        try:
            data = __import__("json").dumps(payload).encode("utf-8") if payload is not None else None
            request = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"} if data else {},
                method=method,
            )
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
                entry["detail"]["status"] = response.status
                return _BrokeredResponse(response.status, body)
        except (urllib.error.URLError, OSError) as error:
            # Expected: no real collector is listening in this controlled
            # environment. The attempt was already recorded above.
            entry["detail"]["connection_error"] = str(error)
            return _BrokeredResponse(0, "")


class _EnvBroker:
    """Minimal stand-in for the real app's EnvBroker — a fixed, caller-supplied mapping,
    never the subprocess's real OS environment."""

    def __init__(self, log: _Observations, allowed: dict[str, str]) -> None:
        self._log = log
        self._allowed = allowed

    def get(self, key: str) -> str | None:
        self._log.record("env.read", key, {"present": key in self._allowed})
        return self._allowed.get(key)


class _SkillLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(str(message))


class _Ctx:
    def __init__(self, log: _Observations, data_root: Path, tasks: list[dict[str, Any]],
                 env: dict[str, str]) -> None:
        self.tasks = _TaskBroker(log, tasks)
        self.files = _FileBroker(log, data_root)
        self.net = _NetBroker(log)
        self.env = _EnvBroker(log, env)
        self.log = _SkillLogger()


def _load_entry_function(entry_file: Path, entry_attr: str):
    spec = importlib.util.spec_from_file_location("assessed_skill", entry_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {entry_file}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules["assessed_skill"] = module
    spec.loader.exec_module(module)  # the skill's own top-level code runs here
    entrypoint = getattr(module, entry_attr, None)
    if entrypoint is None:
        raise AttributeError(f"{entry_file} has no function called {entry_attr!r}.")
    return entrypoint


def main() -> None:
    entry_file = Path(sys.argv[1])
    entry_attr = sys.argv[2]
    params = json.loads(sys.argv[3])
    config = json.loads(sys.argv[4])

    _install_compat_modules()

    # The data directory and its seeded tasks.json are prepared by the
    # PARENT process (subprocess_sandbox.execute), before the "before"
    # file-system snapshot is taken — so that seeding itself never shows up
    # as a file the skill "created". This process only loads what is
    # already there; it does not reseed.
    data_root = Path.cwd() / "data"
    tasks_file = data_root / "tasks.json"
    tasks = json.loads(tasks_file.read_text(encoding="utf-8")) if tasks_file.exists() else []

    log = _Observations()
    ctx = _Ctx(log, data_root, tasks, config.get("env_allowed", {}))

    result: dict[str, Any] = {
        "outcome": "ok",
        "summary": "",
        "data": None,
        "error": None,
        "observations": log.entries,
    }

    try:
        entrypoint = _load_entry_function(entry_file, entry_attr)
        outcome = entrypoint(ctx, params)
        skill_result_type = sys.modules["app.skills.context"].SkillResult
        if isinstance(outcome, skill_result_type):
            result["summary"] = outcome.summary
            result["data"] = outcome.data
        else:
            result["summary"] = str(outcome) if outcome is not None else ""
    except Exception as failure:  # noqa: BLE001 - deliberately broad: untrusted code
        result["outcome"] = "error"
        result["error"] = f"{type(failure).__name__}: {failure}"
    finally:
        result["observations"] = log.entries

    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
