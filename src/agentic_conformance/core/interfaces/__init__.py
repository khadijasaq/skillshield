"""Integration and adapter contracts (docs/spec.md §5, §10)."""

from agentic_conformance.core.interfaces.adapter import ProductAdapter
from agentic_conformance.core.interfaces.conformance_api import ConformanceAPI

__all__ = ["ConformanceAPI", "ProductAdapter"]
