"""Ingestion error hierarchy (docs/product-plan.md P1 security requirements).

``PathTraversalError``, ``MalformedArchiveError``, ``UnsupportedArchiveError``,
and ``InvalidSkillStructureError`` are fatal: ingestion aborts because there
is no safe artifact to analyze.

``MissingDeclarationError`` and ``MalformedDeclarationError`` are
deliberately NOT fatal to the public ``ingest()`` entry point -- they are
raised and caught internally by ``skillshield.ingestion.declaration`` and
converted into a ``DeclarationProblem`` on the resulting ``Skill``, per
docs/product-spec.md §13 ("missing or malformed declarations must be
represented as findings or structured assessment limitations rather than
silently ignored").
"""

from __future__ import annotations


class IngestionError(Exception):
    """Base class for all ingestion failures."""


class PathTraversalError(IngestionError):
    """An archive member resolves outside the intended extraction root."""


class MalformedArchiveError(IngestionError):
    """The archive cannot be safely read (corrupt, oversized, or too many members)."""


class UnsupportedArchiveError(IngestionError):
    """The input is not a supported archive format."""


class InvalidSkillStructureError(IngestionError):
    """The input does not contain a valid skill directory structure."""


class MissingDeclarationError(IngestionError):
    """The skill has no manifest.json. Non-fatal: caught internally."""


class MalformedDeclarationError(IngestionError):
    """manifest.json is present but structurally invalid. Non-fatal: caught internally."""
