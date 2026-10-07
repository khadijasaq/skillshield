"""D/S/R/P correlation (docs/product-spec.md §17).

Pure set operations over plain capability-identifier strings. These
functions have no dependency on ingestion, static analysis, or runtime
execution -- they work identically whether D/S/R/P came from real analysis
or were handed in directly as synthetic sets, which is what P0 relies on to
be testable before P2/P3 exist.
"""

from __future__ import annotations


def undeclared_static(declared: frozenset[str], static: frozenset[str]) -> frozenset[str]:
    """S - D: a capability indicated by source code but not declared."""
    return static - declared


def undeclared_runtime(declared: frozenset[str], runtime: frozenset[str]) -> frozenset[str]:
    """R - D: a capability observed during execution but not declared."""
    return runtime - declared


def static_only(static: frozenset[str], runtime: frozenset[str]) -> frozenset[str]:
    """S - R: statically indicated but not observed at runtime.

    Absence from the runtime set does not prove the capability can never
    occur -- the exercised runtime scenario may simply not have reached
    that code path.
    """
    return static - runtime


def runtime_only(static: frozenset[str], runtime: frozenset[str]) -> frozenset[str]:
    """R - S: observed at runtime but not indicated by static analysis.

    Typically means the static analyzer missed a dynamic code path (for
    example, a capability reached through reflection, a dynamic import, or
    a call pattern the detectors do not recognize).
    """
    return runtime - static


def policy_violations(runtime: frozenset[str], permitted: frozenset[str]) -> frozenset[str]:
    """R - P: an observed capability not permitted by policy."""
    return runtime - permitted
