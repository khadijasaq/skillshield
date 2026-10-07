"""Declaration discovery and parsing (docs/product-spec.md §13).

Expects a ``manifest.json`` file at the skill root. A missing or malformed
declaration is never fatal to ingestion: ``load_declaration`` never raises
out of this module -- it returns a ``(Declaration | None, DeclarationProblem
| None)`` pair so the conformance stage can turn a problem into an
``INVALID_DECLARATION`` finding instead of the pipeline crashing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skillshield.core.models.capability import is_supported_capability
from skillshield.core.models.skill import Declaration, DeclarationProblem, DeclaredCapability
from skillshield.ingestion.errors import MalformedDeclarationError, MissingDeclarationError

MANIFEST_FILENAME = "manifest.json"
_REQUIRED_FIELDS = ("id", "name", "version")


def _parse_capability(entry: Any) -> DeclaredCapability:
    if isinstance(entry, str):
        if not entry:
            raise MalformedDeclarationError("Capability identifier must be a non-empty string")
        return DeclaredCapability(identifier=entry)
    if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry.get("id"):
        scope = entry.get("scope", ())
        if not isinstance(scope, (list, tuple)):
            raise MalformedDeclarationError(f"Invalid capability 'scope' for entry: {entry!r}")
        return DeclaredCapability(
            identifier=entry["id"],
            scope=tuple(scope),
            reason=entry.get("reason"),
        )
    raise MalformedDeclarationError(f"Invalid capability entry in manifest: {entry!r}")


def load_declaration(
    skill_root: Path,
) -> tuple[Declaration | None, DeclarationProblem | None]:
    """Load and parse ``manifest.json`` from ``skill_root``.

    Never raises. On success returns ``(declaration, None)``. When the
    declaration declares an unsupported capability identifier, returns
    ``(declaration, problem)`` -- the declaration is still usable, but the
    problem is recorded. On a missing or otherwise malformed manifest,
    returns ``(None, problem)``.
    """
    manifest_path = skill_root / MANIFEST_FILENAME
    try:
        if not manifest_path.is_file():
            raise MissingDeclarationError(f"{MANIFEST_FILENAME} not found at skill root")

        try:
            raw_text = manifest_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise MalformedDeclarationError(
                f"Could not read {MANIFEST_FILENAME}: {exc}"
            ) from exc

        try:
            raw = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise MalformedDeclarationError(
                f"{MANIFEST_FILENAME} is not valid JSON: {exc}"
            ) from exc

        if not isinstance(raw, dict):
            raise MalformedDeclarationError(f"{MANIFEST_FILENAME} must contain a JSON object")

        missing_fields = [f for f in _REQUIRED_FIELDS if not raw.get(f)]
        if missing_fields:
            raise MalformedDeclarationError(
                f"{MANIFEST_FILENAME} is missing required field(s): {', '.join(missing_fields)}"
            )

        capability_entries = raw.get("capabilities", [])
        if not isinstance(capability_entries, list):
            raise MalformedDeclarationError("'capabilities' must be a list")
        declared_capabilities = tuple(_parse_capability(e) for e in capability_entries)

        entrypoint = raw.get("entrypoint")
        if entrypoint is not None and not isinstance(entrypoint, str):
            raise MalformedDeclarationError("'entrypoint' must be a string")

        declaration = Declaration(
            declared_capabilities=declared_capabilities,
            entrypoint=entrypoint,
            raw=raw,
        )

        unsupported = [
            c.identifier
            for c in declared_capabilities
            if not is_supported_capability(c.identifier)
        ]
        if unsupported:
            return declaration, DeclarationProblem(
                kind="malformed",
                detail=(
                    "Declared unsupported capability identifier(s): " + ", ".join(unsupported)
                ),
            )
        return declaration, None

    except MissingDeclarationError as exc:
        return None, DeclarationProblem(kind="missing", detail=str(exc))
    except MalformedDeclarationError as exc:
        return None, DeclarationProblem(kind="malformed", detail=str(exc))
