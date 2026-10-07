"""ZIP archive ingestion (docs/product-spec.md §10; docs/product-plan.md P1
security requirements).

Safety checks reject path traversal, symlink members, and oversized/
over-populated archives before anything is extracted. On success, the
archive is extracted into a fresh temporary directory and handed to
``ingest_directory`` -- there is exactly one ingestion code path past that
point, which is what guarantees a ZIP and an equivalent directory produce
the same canonical Skill.
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from skillshield.core.models.artifact import ArtifactInputType, SkillArtifact
from skillshield.core.models.skill import Skill
from skillshield.ingestion.directory import ingest_directory
from skillshield.ingestion.errors import (
    MalformedArchiveError,
    PathTraversalError,
    UnsupportedArchiveError,
)

#: Reject archives larger than this when uncompressed (docs/DECISIONS.md P0/P1).
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB

#: Reject archives with more members than this.
MAX_MEMBER_COUNT = 10_000

#: zipfile encodes the Unix file mode in the high 16 bits of external_attr
#: when the archive was created on a Unix system; 0o120000 is S_IFLNK.
_UNIX_FILE_TYPE_MASK = 0o170000
_UNIX_SYMLINK_MODE = 0o120000


def _is_symlink_member(info: zipfile.ZipInfo) -> bool:
    unix_mode = info.external_attr >> 16
    return (unix_mode & _UNIX_FILE_TYPE_MASK) == _UNIX_SYMLINK_MODE


def _safe_member_path(name: str, extraction_root: Path) -> Path:
    """Resolve an archive member's path against extraction_root, rejecting
    anything that would escape it."""
    windows_view = PureWindowsPath(name)
    if windows_view.drive or windows_view.is_absolute():
        raise PathTraversalError(f"Archive member has an absolute/drive path: {name!r}")

    posix_view = PurePosixPath(name.replace("\\", "/"))
    if posix_view.is_absolute():
        raise PathTraversalError(f"Archive member has an absolute path: {name!r}")

    resolved_root = extraction_root.resolve()
    target = (extraction_root / Path(*posix_view.parts)).resolve()
    try:
        target.relative_to(resolved_root)
    except ValueError as exc:
        raise PathTraversalError(f"Archive member escapes extraction root: {name!r}") from exc
    return target


def ingest_archive(
    path: Path, *, original_name: str | None = None
) -> tuple[SkillArtifact, Skill]:
    """Ingest a skill supplied as a ZIP archive."""
    path = Path(path)
    if path.suffix.lower() != ".zip":
        raise UnsupportedArchiveError(f"Unsupported archive type: {path.suffix!r}")

    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise MalformedArchiveError(f"Not a valid ZIP archive: {exc}") from exc

    with zf:
        infos = zf.infolist()
        if len(infos) > MAX_MEMBER_COUNT:
            raise MalformedArchiveError(
                f"Archive has too many members ({len(infos)} > {MAX_MEMBER_COUNT})"
            )
        total_size = sum(info.file_size for info in infos)
        if total_size > MAX_UNCOMPRESSED_BYTES:
            raise MalformedArchiveError(
                f"Archive is too large uncompressed "
                f"({total_size} > {MAX_UNCOMPRESSED_BYTES} bytes)"
            )

        extract_dir = Path(tempfile.mkdtemp(prefix="skillshield_"))
        for info in infos:
            if info.is_dir():
                continue
            if _is_symlink_member(info):
                raise PathTraversalError(f"Archive member is a symlink: {info.filename!r}")
            target = _safe_member_path(info.filename, extract_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())

    return ingest_directory(
        extract_dir,
        original_name=original_name,
        source_path=str(path),
        input_type=ArtifactInputType.ZIP,
    )
