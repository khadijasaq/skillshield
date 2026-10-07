"""Security policy loading (docs/product-spec.md §16; docs/product-plan.md P4).

A ``SecurityPolicy`` (``skillshield.core.models.policy``) is the simple,
deterministic permitted-capability allow-list the conformance engine
compares runtime evidence against (R - P). This package is how an operator
actually gets one: a conservative built-in default, or their own policy
file.
"""

from __future__ import annotations

from skillshield.policy.errors import PolicyLoadError
from skillshield.policy.loader import default_policy, load_policy

__all__ = ["PolicyLoadError", "default_policy", "load_policy"]
