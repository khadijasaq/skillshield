"""Static analysis: generates S (statically inferred capabilities) plus
evidence, by AST-inspecting a skill's source files (docs/product-plan.md P2).
"""

from __future__ import annotations

from skillshield.analysis.static.analyzer import StaticAnalysisResult, analyze
from skillshield.analysis.static.detectors import Hit, run_all_detectors

__all__ = ["Hit", "StaticAnalysisResult", "analyze", "run_all_detectors"]
