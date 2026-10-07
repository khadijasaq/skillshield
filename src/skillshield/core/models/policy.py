"""SecurityPolicy model (docs/product-spec.md §16).

Deliberately simple and deterministic: a named set of permitted
capabilities. Anything not in the set is denied. The project must not
attempt to create a universal policy language.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityPolicy:
    """A simple permitted-capability allow-list policy."""

    name: str
    permitted_capabilities: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("SecurityPolicy.name must be a non-empty string")
        if not isinstance(self.permitted_capabilities, frozenset):
            raise TypeError("SecurityPolicy.permitted_capabilities must be a frozenset")

    def permits(self, capability: str) -> bool:
        return capability in self.permitted_capabilities

    def denied(self, capabilities: frozenset[str]) -> frozenset[str]:
        """The subset of ``capabilities`` this policy does not permit."""
        return frozenset(c for c in capabilities if not self.permits(c))
