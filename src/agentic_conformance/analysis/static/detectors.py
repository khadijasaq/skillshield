"""Deterministic static-analysis pattern detectors (second milestone, Phase 2).

Each detector is a pure function: source text in, a list of `RawMatch` out.
No detector executes, imports, or otherwise runs the code it inspects —
only plain text/regex matching over the literal source.

This is deliberately a small, fixed set of detectors, not a general static
analysis framework: one or more for each capability category named in
`docs/downloaded-skill-assessment-spec.md` §5.2 that the real testbed's
`ctx`-broker calling convention (discovered in Phase 1 — see
`backend/app/skills/context.py` in the real app) actually makes
detectable from plain source text. A detector states only "this pattern,
which implies this capability, appears at this line" — it never claims
maliciousness (capability inference is kept strictly separate from any
maliciousness determination, per this batch's instructions).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RawMatch:
    """One pattern match found in source text, before file attribution."""

    capability: str
    line: int
    detector: str
    description: str


def _line_matches(text: str, pattern: re.Pattern[str], capability: str, detector: str,
                   description: str) -> list[RawMatch]:
    matches: list[RawMatch] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if pattern.search(line):
            matches.append(RawMatch(capability, line_no, detector, description))
    return matches


# ---------------------------------------------------------------------------
# Detectors — one responsibility each, named after what they look for.
# ---------------------------------------------------------------------------

_TASK_READ_PATTERN = re.compile(r"\bctx\.tasks\.(list|get)\s*\(")
_TASK_WRITE_PATTERN = re.compile(r"\bctx\.tasks\.(add|update|delete)\s*\(")
_FS_READ_PATTERN = re.compile(r"\bctx\.files\.read\s*\(")
_FS_WRITE_PATTERN = re.compile(r"\bctx\.files\.write\s*\(")
_NET_CALL_PATTERN = re.compile(r"\bctx\.net\.(get|post)\s*\(")
_ENV_READ_PATTERN = re.compile(r"\bctx\.env\.get\s*\(")
_PROCESS_IMPORT_PATTERN = re.compile(
    r"^\s*(import\s+subprocess\b|from\s+subprocess\s+import|import\s+os\.system\b)"
)
_PROCESS_CALL_PATTERN = re.compile(r"\b(subprocess\.(run|Popen|call)|os\.system|os\.popen)\s*\(")
_URL_LITERAL_PATTERN = re.compile(r"[\"'](https?://[^\"']+)[\"']")


def detect_task_read(text: str) -> list[RawMatch]:
    """`ctx.tasks.list(...)` / `ctx.tasks.get(...)` -> task.read."""
    return _line_matches(
        text, _TASK_READ_PATTERN, "task.read", "task-broker-read",
        "Call to ctx.tasks.list()/ctx.tasks.get() implies the task.read capability.",
    )


def detect_task_write(text: str) -> list[RawMatch]:
    """`ctx.tasks.add/update/delete(...)` -> task.write."""
    return _line_matches(
        text, _TASK_WRITE_PATTERN, "task.write", "task-broker-write",
        "Call to ctx.tasks.add()/update()/delete() implies the task.write capability.",
    )


def detect_filesystem_read(text: str) -> list[RawMatch]:
    """`ctx.files.read(...)` -> filesystem.read."""
    return _line_matches(
        text, _FS_READ_PATTERN, "filesystem.read", "file-broker-read",
        "Call to ctx.files.read() implies the filesystem.read capability.",
    )


def detect_filesystem_write(text: str) -> list[RawMatch]:
    """`ctx.files.write(...)` -> filesystem.write."""
    return _line_matches(
        text, _FS_WRITE_PATTERN, "filesystem.write", "file-broker-write",
        "Call to ctx.files.write() implies the filesystem.write capability.",
    )


def detect_network_broker_call(text: str) -> list[RawMatch]:
    """`ctx.net.get/post(...)` -> network.egress."""
    return _line_matches(
        text, _NET_CALL_PATTERN, "network.egress", "net-broker-call",
        "Call to ctx.net.get()/post() implies the network.egress capability.",
    )


def detect_env_read(text: str) -> list[RawMatch]:
    """`ctx.env.get(...)` -> env.read."""
    return _line_matches(
        text, _ENV_READ_PATTERN, "env.read", "env-broker-read",
        "Call to ctx.env.get() implies the env.read capability.",
    )


def detect_process_execution(text: str) -> list[RawMatch]:
    """`subprocess`/`os.system`/`os.popen` import or call -> process.execute."""
    matches = _line_matches(
        text, _PROCESS_IMPORT_PATTERN, "process.execute", "process-import",
        "Import of subprocess/os.system implies the process.execute capability.",
    )
    matches += _line_matches(
        text, _PROCESS_CALL_PATTERN, "process.execute", "process-call",
        "Call to subprocess.run/Popen/call, os.system, or os.popen implies"
        " the process.execute capability.",
    )
    return matches


def detect_url_literal(text: str) -> list[RawMatch]:
    """A literal http(s):// URL string -> network.egress (independent of ctx.net usage)."""
    return _line_matches(
        text, _URL_LITERAL_PATTERN, "network.egress", "url-literal",
        "A literal http(s):// URL string implies the network.egress capability.",
    )


#: Every detector, applied in this fixed order. Adding a detector here is
#: additive; this is not meant to grow into a large taxonomy (per this
#: batch's explicit instruction not to build a complete malware detector).
ALL_DETECTORS = (
    detect_task_read,
    detect_task_write,
    detect_filesystem_read,
    detect_filesystem_write,
    detect_network_broker_call,
    detect_env_read,
    detect_process_execution,
    detect_url_literal,
)


def run_all_detectors(text: str) -> list[RawMatch]:
    """Run every detector against one file's source text.

    Deterministic and order-preserving: the same text always produces the
    same matches in the same order. A file that matches no detector
    produces an empty list — reported honestly as "no static finding",
    never as an error.
    """
    matches: list[RawMatch] = []
    for detector in ALL_DETECTORS:
        matches.extend(detector(text))
    return matches
