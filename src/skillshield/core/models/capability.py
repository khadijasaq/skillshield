"""Capability vocabulary for SkillShield (docs/product-spec.md §12).

Reuses the open, product-independent capability registry already implemented
in ``agentic_conformance`` rather than duplicating it -- that registry is
itself product-independent and fits SkillShield's needs as-is. SkillShield
adds exactly one new identifier, ``filesystem.read``, to the existing
vocabulary (``task.read``, ``network.egress``, ``process.execute``,
``filesystem.write``, ``credential.read``).
"""

from __future__ import annotations

from agentic_conformance.core.models.capability import (
    Capability,
    is_supported_capability,
    register_capability,
    supported_capabilities,
)

register_capability("filesystem.read")

__all__ = [
    "Capability",
    "is_supported_capability",
    "register_capability",
    "supported_capabilities",
]
