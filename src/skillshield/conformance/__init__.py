"""Conformance logic for SkillShield: correlation, severity, findings, assessment
(docs/product-spec.md §17-§19; docs/conformance-rules.md).
"""

from skillshield.conformance.assessment import recommend
from skillshield.conformance.engine import build_findings

__all__ = ["build_findings", "recommend"]
