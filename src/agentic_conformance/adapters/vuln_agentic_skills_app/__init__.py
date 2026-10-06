"""Adapter for the real `vuln-agentic-skills-app` testbed (second milestone, Phase 1)."""

from agentic_conformance.adapters.vuln_agentic_skills_app.adapter import (
    VulnAgenticSkillsAppAdapter,
    load_manifest,
    resolve_entrypoint,
)

__all__ = ["VulnAgenticSkillsAppAdapter", "load_manifest", "resolve_entrypoint"]
