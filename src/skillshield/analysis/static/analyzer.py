"""Static analysis over an ingested skill's source files (docs/product-spec.md §14;
docs/product-plan.md P2).

Runs the detectors in ``detectors.py`` over every ``.py`` file
``skillshield.ingestion`` discovered for a skill, and aggregates the result
into the static capability set (S) plus the Evidence needed by the
conformance engine. Never imports, executes, or ``exec``'s the analyzed
code -- this is pure source (AST) inspection.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from skillshield.analysis.static.detectors import run_all_detectors
from skillshield.core.models.artifact import SkillArtifact
from skillshield.core.models.evidence import Evidence, EvidenceSource
from skillshield.core.models.skill import Skill


@dataclass(frozen=True)
class StaticAnalysisResult:
    """The outcome of running static analysis over one skill."""

    capabilities: frozenset[str]
    evidence: tuple[Evidence, ...]
    analysis_failures: tuple[str, ...] = field(default_factory=tuple)


def _analyze_file(working_root: Path, relative_path: str) -> tuple[list[Evidence], str | None]:
    """Analyze one source file. Returns (evidence, failure_description).

    Exactly one of the two is populated: a parse/read failure never raises
    out of this function -- it is reported as a failure description so the
    caller can continue analyzing the skill's other files.
    """
    full_path = working_root / relative_path
    try:
        source_text = full_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [], f"{relative_path}: could not read file ({exc})"

    try:
        tree = ast.parse(source_text, filename=relative_path)
    except (SyntaxError, ValueError) as exc:
        return [], f"{relative_path}: could not parse ({exc})"

    hits = run_all_detectors(tree)
    seen: set[tuple[str, str, int]] = set()
    evidence: list[Evidence] = []
    for hit in hits:
        key = (hit.capability, hit.operation, hit.lineno)
        if key in seen:
            continue
        seen.add(key)
        evidence.append(
            Evidence(
                source=EvidenceSource.STATIC,
                capability=hit.capability,
                detail={
                    "file": relative_path,
                    "line": hit.lineno,
                    "detector": hit.detector,
                    "operation": hit.operation,
                },
            )
        )
    return evidence, None


def analyze(skill: Skill, artifact: SkillArtifact) -> StaticAnalysisResult:
    """Run static analysis over every source file discovered for ``skill``."""
    working_root = Path(artifact.working_path)
    all_evidence: list[Evidence] = []
    failures: list[str] = []

    for relative_path in skill.source_files:
        if not relative_path.endswith(".py"):
            continue
        evidence, failure = _analyze_file(working_root, relative_path)
        all_evidence.extend(evidence)
        if failure is not None:
            failures.append(failure)

    capabilities = frozenset(e.capability for e in all_evidence)
    return StaticAnalysisResult(
        capabilities=capabilities,
        evidence=tuple(all_evidence),
        analysis_failures=tuple(failures),
    )
