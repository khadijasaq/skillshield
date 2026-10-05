"""Set-based conformance rules (docs/spec.md §8, §9).

Operates on plain sets of canonical capability identifiers:

    D = declared capabilities
    R = runtime observed capabilities
    P = policy-permitted capabilities

Static evidence (S) is conceptually supported by the model but no static
analyzer contributes to it in this milestone, so it is not part of these
rules.
"""

from __future__ import annotations


def runtime_within_declared(declared: set[str], observed: set[str]) -> bool:
    """R ⊆ D — every runtime-observed capability should be declared."""
    return observed <= declared


def runtime_within_policy(policy: set[str], observed: set[str]) -> bool:
    """R ⊆ P — every runtime-observed capability should be policy-permitted."""
    return observed <= policy


def runtime_within_declared_and_policy(
    declared: set[str], policy: set[str], observed: set[str]
) -> bool:
    """R ⊆ D ∩ P — combined declaration and policy conformance."""
    return observed <= (declared & policy)


def undeclared_capabilities(declared: set[str], observed: set[str]) -> set[str]:
    """Capabilities observed at runtime but absent from the declaration (R - D)."""
    return observed - declared


def policy_violating_capabilities(policy: set[str], observed: set[str]) -> set[str]:
    """Capabilities observed at runtime but not permitted by policy (R - P)."""
    return observed - policy
