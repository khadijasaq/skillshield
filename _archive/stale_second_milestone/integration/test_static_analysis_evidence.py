"""Real-data integration test for the static analysis foundation (second
milestone, Phase 2).

Runs the analyzer against the real, unmodified `task_insights` skill
source (verbatim fixture — see tests/fixtures/vuln_agentic_skills_app/
README.md for provenance) and asserts genuine, non-fabricated static
evidence: this skill declares only `task.read` but its real code also
calls `ctx.files.read` and `ctx.net.post`, so static analysis is expected
to find `filesystem.read` and `network.egress` as well — undeclared
capabilities discovered purely from source inspection, before execution.
"""

from __future__ import annotations

from pathlib import Path

from agentic_conformance.adapters.vuln_agentic_skills_app import VulnAgenticSkillsAppAdapter
from agentic_conformance.analysis.static import (
    analyze,
    static_capability_identifiers,
    static_findings_to_evidence,
)
from agentic_conformance.core.models import EvidenceSource

_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "vuln_agentic_skills_app"
    / "task_insights"
)


def test_real_skill_static_analysis_finds_undeclared_capabilities():
    findings = analyze(_FIXTURE_DIR)

    capabilities_found = {f.capability for f in findings}
    assert "task.read" in capabilities_found
    assert "filesystem.read" in capabilities_found
    assert "network.egress" in capabilities_found

    for finding in findings:
        assert finding.file == "skill.py"
        assert finding.location > 0


def test_real_skill_static_evidence_is_canonical_and_traceable():
    findings = analyze(_FIXTURE_DIR)
    evidence = static_findings_to_evidence("task_insights", findings)

    assert len(evidence) == len(findings)
    for item in evidence:
        assert item.source is EvidenceSource.STATIC
        assert item.skill_id == "task_insights"
        assert item.data["file"] == "skill.py"
        assert item.data["location"] > 0
        assert item.data["detector"]
        assert item.data["description"]


def test_real_skill_s_is_not_a_subset_of_d():
    """S is not fully covered by D for this real skill — the entire point of AST04."""
    declared = {
        c.identifier
        for c in VulnAgenticSkillsAppAdapter(None).translate_skill(
            _FIXTURE_DIR
        ).declaration.declared_capabilities
    }
    findings = analyze(_FIXTURE_DIR)
    evidence = static_findings_to_evidence("task_insights", findings)
    static_set = static_capability_identifiers(evidence)

    undeclared_static = static_set - declared

    assert undeclared_static, "expected genuine real-data S - D mismatch, found none"
    assert undeclared_static == {"filesystem.read", "network.egress"}
