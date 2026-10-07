"""Policy-loading errors (docs/product-plan.md P4).

A malformed policy *file* is an operator configuration error, not a skill
finding -- deliberately different from ``skillshield.ingestion.errors``'
``MissingDeclarationError``/``MalformedDeclarationError``, which must never
be fatal because a skill's own declaration is attacker/author-controlled
content SkillShield is assessing. A policy file is something the operator
running SkillShield wrote themselves; failing loudly and immediately is the
right behavior, not a finding about the skill being assessed. See
DECISIONS.md ("P4 (Batch 4)") for the full rationale.
"""

from __future__ import annotations


class PolicyLoadError(Exception):
    """The policy file could not be loaded: bad JSON, wrong shape, or an
    unsupported capability identifier."""
