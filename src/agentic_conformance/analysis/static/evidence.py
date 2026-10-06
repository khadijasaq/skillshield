"""StaticFinding -> canonical Evidence conversion (second milestone, Phase 2).

Reuses the existing, unmodified `Evidence` model
(`core/models/evidence.py`) exactly as the first milestone defined it —
`source=EvidenceSource.STATIC`, with finding detail carried in `data`
(already an untyped dict on the canonical model, per
`docs/downloaded-skill-assessment-spec.md` §5.3: "no new fields are added
to Evidence for this milestone").
"""

from __future__ import annotations

from agentic_conformance.analysis.static.analyzer import StaticFinding
from agentic_conformance.core.models import Evidence, EvidenceSource


def static_findings_to_evidence(skill_id: str, findings: list[StaticFinding]) -> list[Evidence]:
    """Convert every StaticFinding for one skill into canonical STATIC Evidence.

    Traceability (docs/downloaded-skill-assessment-spec.md §5.3, §9.2) is
    preserved verbatim: `file`, `location`, `detector`, and `description`
    all survive into `Evidence.data` unchanged, so a Finding referencing
    this Evidence later can still answer "what was discovered, how, and
    where" without a parallel explanation mechanism.
    """
    return [
        Evidence(
            source=EvidenceSource.STATIC,
            skill_id=skill_id,
            data={
                "capability": finding.capability,
                "file": finding.file,
                "location": finding.location,
                "detector": finding.detector,
                "description": finding.description,
            },
        )
        for finding in findings
    ]


def static_capability_identifiers(evidence: list[Evidence]) -> set[str]:
    """The distinct canonical capability identifiers across STATIC Evidence — `S`."""
    return {
        item.data["capability"]
        for item in evidence
        if item.source is EvidenceSource.STATIC and "capability" in item.data
    }
