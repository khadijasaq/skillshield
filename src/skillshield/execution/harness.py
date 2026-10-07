"""Controlled-execution child-process entry point (docs/product-spec.md §21).

Run as::

    python -m skillshield.execution.harness <skill_dir> <entry_file> <entry_attr> <events_file>

This process is the thing SkillShield's ``sandbox.py`` spawns and later
kills on timeout. It is a restricted subprocess, not a secure sandbox: it
adds no OS-level isolation of its own -- see SECURITY_LIMITATIONS.md. Its
only job is to (1) install an audit hook that logs capability-indicating
events to ``events_file`` as they happen, so a killed/timed-out process
still leaves partial evidence on disk, and (2) call the skill's declared
entrypoint once, reporting whether it succeeded or raised.

The events file is opened for writing *before* the audit hook is
installed, so the hook's own writes to it (via the already-open handle)
never re-trigger an "open" audit event -- there is nothing left to open.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import traceback
from pathlib import Path

from skillshield.execution.monitor import is_bytecode_cache_event, translate_event


def _run(skill_dir: str, entry_file: str, entry_attr: str, events_path: str) -> int:
    events_handle = open(events_path, "a", encoding="utf-8")  # noqa: SIM115 -- kept open for the hook's lifetime

    # The import machinery opens the entrypoint module's own source file to
    # compile it -- that is Python bootstrapping itself, not the skill
    # exercising a filesystem capability, so it is excluded by identity
    # rather than reported as filesystem.read.
    entry_abspath = os.path.abspath(os.path.join(skill_dir, entry_file))

    def _audit_hook(event: str, args: tuple) -> None:
        if is_bytecode_cache_event(event, args):
            return
        if (
            event == "open"
            and args
            and isinstance(args[0], str)
            and os.path.abspath(args[0]) == entry_abspath
        ):
            return
        translated = translate_event(event, args)
        if translated is None:
            return
        capability, detail = translated
        events_handle.write(json.dumps({"capability": capability, "detail": detail}) + "\n")
        events_handle.flush()

    sys.addaudithook(_audit_hook)

    sys.path.insert(0, skill_dir)
    module_name = Path(entry_file).stem

    try:
        module = importlib.import_module(module_name)
        entrypoint = getattr(module, entry_attr)
        entrypoint()
    except BaseException as exc:  # noqa: BLE001 -- must report any failure from untrusted code
        summary = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        events_handle.write(json.dumps({"status": "crashed", "error": summary}) + "\n")
        events_handle.flush()
        events_handle.close()
        return 1

    events_handle.write(json.dumps({"status": "ok"}) + "\n")
    events_handle.flush()
    events_handle.close()
    return 0


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: harness.py <skill_dir> <entry_file> <entry_attr> <events_file>", file=sys.stderr)
        return 2
    _, skill_dir, entry_file, entry_attr, events_path = sys.argv
    return _run(skill_dir, entry_file, entry_attr, events_path)


if __name__ == "__main__":
    sys.exit(main())
