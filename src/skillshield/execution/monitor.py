"""Audit-event -> capability translation (docs/product-spec.md §15).

The event names and argument shapes used here were confirmed empirically
against CPython 3.12 (this project's venv) with a throwaway probe script,
not assumed from documentation alone -- see docs/batch-reports/batch-3.md.
Notably, ``os.environ.get``/``os.getenv`` fire **no** audit event at all on
this Python version: runtime observation is blind to plain environment-
variable reads (only ``os.putenv``/``os.unsetenv``-style writes are
audited). This is a real, documented limitation, not an omission --
see SECURITY_LIMITATIONS.md.

``translate_event`` is a pure function: given one audit event's name and
argument tuple, it returns the capability it indicates plus a detail dict,
or ``None`` if the event isn't one SkillShield maps to a capability. It
does no I/O and knows nothing about subprocesses or file handles.
"""

from __future__ import annotations

from typing import Any

_WRITE_OPEN_MODE_PREFIXES = ("w", "a", "x")

#: Audit event name -> capability, for events whose mere occurrence is
#: sufficient (no argument-dependent branching needed).
_FIXED_EVENTS: dict[str, str] = {
    "os.remove": "filesystem.write",
    "os.rmdir": "filesystem.write",
    "os.rename": "filesystem.write",
    "os.mkdir": "filesystem.write",
    "os.listdir": "filesystem.read",
    "os.scandir": "filesystem.read",
    "socket.connect": "network.egress",
    "subprocess.Popen": "process.execute",
    "os.system": "process.execute",
    "os.posix_spawn": "process.execute",
    "os.exec": "process.execute",
}


def _resource_for(event: str, args: tuple[Any, ...]) -> str:
    """Best-effort human-readable resource description for an event's
    first argument (path, command, address, ...)."""
    if not args:
        return ""
    first = args[0]
    if event == "socket.connect" and len(args) >= 2:
        return repr(args[1])
    return repr(first) if not isinstance(first, str) else first


def is_bytecode_cache_event(event: str, args: tuple[Any, ...]) -> bool:
    """True for an event caused by CPython's own bytecode-cache machinery
    (reading/writing/renaming a ``.pyc`` file under some ``__pycache__``
    directory), not by anything the skill's code itself did.

    Discovered empirically: importing *any* module -- including the
    skill's own entrypoint module, and every stdlib module it imports --
    makes CPython probe for and (absent ``-B``) write a ``.pyc`` cache,
    which fires ``open``/``os.mkdir``/``os.rename`` audit events that would
    otherwise be misreported as the skill's own ``filesystem.read``/
    ``filesystem.write`` capability use. ``sandbox.py`` also passes ``-B``
    to the interpreter to avoid writing new caches at all, but reads of
    *pre-existing* stdlib caches in the shared venv still occur and must be
    filtered here regardless.
    """
    for value in args:
        if isinstance(value, str):
            lowered = value.replace("\\", "/").lower()
            if "__pycache__" in lowered or lowered.endswith(".pyc"):
                return True
    return False


def translate_event(event: str, args: tuple[Any, ...]) -> tuple[str, dict] | None:
    """Translate one ``sys.addaudithook`` event into (capability, detail),
    or ``None`` if this event carries no capability SkillShield tracks."""
    if event == "open":
        if len(args) < 2:
            return None
        path, mode = args[0], args[1]
        mode_str = mode if isinstance(mode, str) else ""
        if mode_str.startswith(_WRITE_OPEN_MODE_PREFIXES):
            return "filesystem.write", {"event": event, "resource": path, "mode": mode_str}
        return "filesystem.read", {"event": event, "resource": path, "mode": mode_str}

    if event.startswith(("os.exec", "os.spawn")):
        return "process.execute", {"event": event, "resource": _resource_for(event, args)}

    capability = _FIXED_EVENTS.get(event)
    if capability is None:
        return None
    return capability, {"event": event, "resource": _resource_for(event, args)}
