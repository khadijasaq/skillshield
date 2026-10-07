"""Directory ingestion (docs/product-spec.md §10, §11; docs/product-plan.md P1).

This is the single ingestion code path: ZIP input (``archive.py``) is first
safely extracted into a temporary directory and then handed to
``ingest_directory`` here, which is what makes the directory and ZIP forms
of the same skill produce an equivalent canonical ``Skill`` by construction.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from skillshield.core.models.artifact import ArtifactInputType, SkillArtifact
from skillshield.core.models.skill import Skill
from skillshield.ingestion.declaration import load_declaration
from skillshield.ingestion.errors import InvalidSkillStructureError


def _file_inventory(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(str(p.relative_to(root).as_posix()) for p in root.rglob("*") if p.is_file())
    )


def _content_digest(root: Path, inventory: tuple[str, ...]) -> str:
    """SHA-256 over the sorted (relative path, content) pairs.

    Deterministic regardless of filesystem walk order or mtimes, and
    identical whether the skill arrived as a directory or was just
    extracted from a ZIP of the same content.
    """
    digest = hashlib.sha256()
    for rel_path in inventory:
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\x00")
        digest.update((root / rel_path).read_bytes())
        digest.update(b"\x00")
    return digest.hexdigest()


def ingest_directory(
    path: Path,
    *,
    original_name: str | None = None,
    source_path: str | None = None,
    input_type: ArtifactInputType = ArtifactInputType.DIRECTORY,
) -> tuple[SkillArtifact, Skill]:
    """Ingest a skill supplied as a local directory (or an already-extracted
    archive, via ``input_type``)."""
    path = Path(path)
    if not path.is_dir():
        raise InvalidSkillStructureError(f"Not a directory: {path}")

    inventory = _file_inventory(path)
    if not inventory:
        raise InvalidSkillStructureError(f"Skill directory is empty: {path}")

    digest = _content_digest(path, inventory)
    source_files = tuple(f for f in inventory if f.endswith(".py"))

    declaration, problem = load_declaration(path)
    manifest_data = declaration.raw if declaration is not None else {}

    skill = Skill(
        skill_id=str(manifest_data.get("id") or path.name),
        name=str(manifest_data.get("name") or path.name),
        version=str(manifest_data.get("version") or "0.0.0"),
        description=str(manifest_data.get("description") or ""),
        source_files=source_files,
        declaration=declaration,
        declaration_problem=problem,
    )

    artifact = SkillArtifact(
        input_type=input_type,
        source_path=source_path or str(path),
        working_path=str(path),
        file_inventory=inventory,
        content_digest=digest,
        original_name=original_name,
    )
    return artifact, skill
