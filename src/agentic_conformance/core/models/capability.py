"""Canonical Capability model (docs/spec.md §7.2).

Capabilities use normalized identifiers that are independent of any host
product's native naming. The vocabulary is intentionally small for this
milestone but must remain extensible, so it is implemented as a mutable
registry rather than a closed enum.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Initial canonical capability vocabulary (docs/spec.md §7.2).
_INITIAL_VOCABULARY = frozenset(
    {
        "task.read",
        "network.egress",
        "process.execute",
        "filesystem.write",
        "credential.read",
    }
)

_vocabulary: set[str] = set(_INITIAL_VOCABULARY)


def register_capability(identifier: str) -> None:
    """Extend the supported canonical capability vocabulary.

    Keeps the vocabulary open to future extension without requiring the
    model itself to be a closed enum.
    """
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("Capability identifier must be a non-empty string")
    _vocabulary.add(identifier)


def supported_capabilities() -> frozenset[str]:
    """Return the currently supported canonical capability vocabulary."""
    return frozenset(_vocabulary)


def is_supported_capability(identifier: str) -> bool:
    """Check whether an identifier belongs to the currently supported vocabulary."""
    return identifier in _vocabulary


@dataclass(frozen=True)
class Capability:
    """A single normalized capability identifier."""

    identifier: str

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str) or not self.identifier:
            raise ValueError("Capability identifier must be a non-empty string")
        if not is_supported_capability(self.identifier):
            raise ValueError(f"Unknown capability identifier: {self.identifier!r}")
