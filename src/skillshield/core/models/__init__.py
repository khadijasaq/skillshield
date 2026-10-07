"""Canonical models for SkillShield (docs/product-spec.md §9-§19)."""

from skillshield.core.models.artifact import ArtifactInputType, SkillArtifact
from skillshield.core.models.assessment import Assessment, CapabilitySummary, Recommendation
from skillshield.core.models.capability import (
    Capability,
    is_supported_capability,
    register_capability,
    supported_capabilities,
)
from skillshield.core.models.evidence import Evidence, EvidenceSource
from skillshield.core.models.finding import (
    Finding,
    FindingType,
    PolicyInfo,
    Severity,
    severity_rank,
)
from skillshield.core.models.policy import SecurityPolicy
from skillshield.core.models.skill import (
    Declaration,
    DeclarationProblem,
    DeclaredCapability,
    Skill,
)

__all__ = [
    "ArtifactInputType",
    "Assessment",
    "Capability",
    "CapabilitySummary",
    "Declaration",
    "DeclarationProblem",
    "DeclaredCapability",
    "Evidence",
    "EvidenceSource",
    "Finding",
    "FindingType",
    "PolicyInfo",
    "Recommendation",
    "SecurityPolicy",
    "Severity",
    "Skill",
    "SkillArtifact",
    "is_supported_capability",
    "register_capability",
    "severity_rank",
    "supported_capabilities",
]
