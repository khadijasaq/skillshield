"""Tests for the canonical Finding model (second milestone, Phase 5;
docs/downloaded-skill-assessment-spec.md §10.4)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from agentic_conformance.core.models import ReasonCode
from agentic_conformance.core.models.finding import Finding

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"


def _load_schema(name: str) -> dict:
    with open(SCHEMAS_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


def _top_level_field_names(model_cls) -> set[str]:
    return {f.name for f in dataclasses.fields(model_cls)}


def test_finding_valid_construction():
    finding = Finding(
        reason_code=ReasonCode.UNDECLARED_CAPABILITY,
        capabilities=("network.egress",),
        evidence_refs=("obs-inv-1-2",),
        description="network.egress observed but not declared.",
    )

    assert finding.reason_code is ReasonCode.UNDECLARED_CAPABILITY
    assert finding.capabilities == ("network.egress",)
    assert finding.schema_version == "1.0"


def test_finding_rejects_invalid_reason_code():
    with pytest.raises(TypeError):
        Finding(
            reason_code="not-a-reason-code",  # type: ignore[arg-type]
            capabilities=("x",),
            evidence_refs=("y",),
            description="z",
        )


def test_finding_rejects_empty_capabilities_entry():
    with pytest.raises(ValueError):
        Finding(
            reason_code=ReasonCode.UNDECLARED_CAPABILITY,
            capabilities=("",),
            evidence_refs=("y",),
            description="z",
        )


def test_finding_rejects_empty_description():
    with pytest.raises(ValueError):
        Finding(
            reason_code=ReasonCode.UNDECLARED_CAPABILITY,
            capabilities=("x",),
            evidence_refs=("y",),
            description="",
        )


def test_finding_schema_model_alignment():
    schema = _load_schema("finding.schema.json")
    assert set(schema["properties"].keys()) == _top_level_field_names(Finding)
