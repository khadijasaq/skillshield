"""SkillArtifact: the downloaded physical artifact supplied by the user
(docs/product-spec.md §10).

``SkillArtifact`` describes the supplied artifact only. It intentionally has
no fields for D, S, R, P, findings, severity, or recommendation -- there is
nothing here for a caller to misuse, because those concepts have no
attribute to write to on this class.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ArtifactInputType(str, Enum):
    """How the artifact was supplied."""

    DIRECTORY = "directory"
    ZIP = "zip"


@dataclass(frozen=True)
class SkillArtifact:
    """Facts about the supplied artifact -- not a security assessment."""

    input_type: ArtifactInputType
    source_path: str
    working_path: str
    file_inventory: tuple[str, ...]
    content_digest: str
    original_name: str | None = None
    ingestion_warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.input_type, ArtifactInputType):
            raise TypeError("SkillArtifact.input_type must be an ArtifactInputType")
        for field_name, value in (
            ("source_path", self.source_path),
            ("working_path", self.working_path),
            ("content_digest", self.content_digest),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"SkillArtifact.{field_name} must be a non-empty string")
        if not isinstance(self.file_inventory, tuple) or not all(
            isinstance(f, str) for f in self.file_inventory
        ):
            raise TypeError("SkillArtifact.file_inventory must be a tuple of strings")
        if self.original_name is not None and not isinstance(self.original_name, str):
            raise TypeError("SkillArtifact.original_name must be a string or None")
        if not isinstance(self.ingestion_warnings, tuple) or not all(
            isinstance(w, str) for w in self.ingestion_warnings
        ):
            raise TypeError("SkillArtifact.ingestion_warnings must be a tuple of strings")
