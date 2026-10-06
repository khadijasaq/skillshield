"""Canonical Severity classification (docs/downloaded-skill-assessment-spec.md §10.5).

A small, closed, non-probabilistic classification — a label, not a score.
No numeric or weighted risk value is introduced anywhere in this
milestone.
"""

from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    """How concerning an Assessment's result is, as a closed label."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
