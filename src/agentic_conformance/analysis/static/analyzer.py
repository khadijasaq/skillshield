"""Static-analysis traversal/orchestration (second milestone, Phase 2).

```text
Skill Source
    v
run_all_detectors()   (detectors.py — pure pattern functions)
    v
analyze()              (this module — traversal + file attribution)
    v
list[StaticFinding]
```

`analyze()` never executes, imports, or evaluates any part of the skill it
inspects — it only reads file text. Capability inference (what a pattern
implies) is kept strictly separate from any maliciousness determination:
a `StaticFinding` only ever states "this pattern, implying this
capability, was found at this file/line" — nothing about whether that is
dangerous.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_conformance.analysis.static.detectors import run_all_detectors


@dataclass(frozen=True)
class StaticFinding:
    """One static-analysis finding (docs/downloaded-skill-assessment-spec.md §5.1)."""

    capability: str
    file: str
    location: int
    detector: str
    description: str


def _analyze_file(path: Path, root: Path) -> list[StaticFinding]:
    """Run every detector against one file, attributing matches to it.

    Malformed input handling: a file that cannot be decoded as UTF-8 is
    read with `errors="replace"` rather than raising — a skill's source
    containing non-UTF-8 bytes is not itself a reason to abort analysis
    of every other file, and a replaced/garbled byte cannot coincidentally
    satisfy any of the fixed regex patterns in `detectors.py` in a way
    that would fabricate a finding.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    relative = path.relative_to(root)
    findings: list[StaticFinding] = []
    for match in run_all_detectors(text):
        findings.append(
            StaticFinding(
                capability=match.capability,
                file=str(relative),
                location=match.line,
                detector=match.detector,
                description=match.description,
            )
        )
    return findings


def analyze(source_root: Path) -> list[StaticFinding]:
    """Inspect every `*.py` file under `source_root` and return all findings.

    In: the skill's source directory (as exposed by the Phase 1 adapter —
    the same directory `translate_skill` reads `manifest.json` from).
    Out: every `StaticFinding` across every source file, in a deterministic
    order (files sorted by relative path, matches in detector-then-line
    order within each file).

    A missing directory is a genuine setup error, not a "no findings"
    result, and is raised as such rather than silently swallowed.
    """
    root = Path(source_root)
    if not root.is_dir():
        raise FileNotFoundError(f"Static analysis source root does not exist: {root}")

    findings: list[StaticFinding] = []
    for path in sorted(root.rglob("*.py")):
        if path.is_file():
            findings.extend(_analyze_file(path, root))
    return findings


def static_capability_set(findings: list[StaticFinding]) -> set[str]:
    """The distinct canonical capability identifiers across a findings list — `S`."""
    return {finding.capability for finding in findings}
