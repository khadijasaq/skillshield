"""Generic Skill ingestion entrypoint (docs/product-spec.md §10;
docs/product-plan.md P1).

Accepts exactly two input shapes: a local directory, or a ZIP archive.
Deliberately does not implement GitHub/SkillsMP downloading, marketplace
APIs, or any other remote retrieval -- the user supplies an
already-downloaded artifact.
"""

from __future__ import annotations

from pathlib import Path

from skillshield.core.models.artifact import SkillArtifact
from skillshield.core.models.skill import Skill
from skillshield.ingestion.archive import ingest_archive
from skillshield.ingestion.directory import ingest_directory
from skillshield.ingestion.errors import (
    IngestionError,
    InvalidSkillStructureError,
    MalformedArchiveError,
    MalformedDeclarationError,
    MissingDeclarationError,
    PathTraversalError,
    UnsupportedArchiveError,
)

__all__ = [
    "IngestionError",
    "InvalidSkillStructureError",
    "MalformedArchiveError",
    "MalformedDeclarationError",
    "MissingDeclarationError",
    "PathTraversalError",
    "UnsupportedArchiveError",
    "ingest",
]


def ingest(path: str | Path) -> tuple[SkillArtifact, Skill]:
    """Ingest a downloaded skill supplied as a directory or a ZIP archive.

    Raises an ``IngestionError`` subclass for anything that makes the input
    unsafe or structurally invalid to analyze. A missing/malformed
    *declaration* is not such a case -- see ``skillshield.ingestion.declaration``.
    """
    path = Path(path)
    if not path.exists():
        raise InvalidSkillStructureError(f"Input path does not exist: {path}")
    if path.is_dir():
        return ingest_directory(path, original_name=path.name)
    if path.is_file():
        if path.suffix.lower() == ".zip":
            return ingest_archive(path, original_name=path.name)
        raise UnsupportedArchiveError(f"Unsupported file type: {path.suffix!r}")
    raise InvalidSkillStructureError(f"Unsupported input path: {path}")
