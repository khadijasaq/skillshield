"""Tests for the canonical Severity model (second milestone, Phase 6)."""

from __future__ import annotations

from agentic_conformance.core.models import Severity


def test_severity_values():
    assert Severity.LOW.value == "LOW"
    assert Severity.MEDIUM.value == "MEDIUM"
    assert Severity.HIGH.value == "HIGH"


def test_severity_is_closed_three_values():
    assert {s.value for s in Severity} == {"LOW", "MEDIUM", "HIGH"}
