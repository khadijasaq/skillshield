"""Reconstructing an HTTP upload (parsed multipart parts) into a filesystem
path usable by ``skillshield.pipeline.assess()``.

A client-supplied filename here is exactly as untrustworthy as a ZIP
archive member's name (docs/product-plan.md P1 security requirements) --
the same traversal-resolution discipline used in
``skillshield.ingestion.archive`` is applied here. Unlike that module,
which is reached only after this one hands ``assess()`` a path, this is the
first line of defense for a browser-submitted *directory* upload (there is
no ZIP/archive safety check to fall back on for that path, since there is
no archive).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from skillshield.ingestion.archive import MAX_UNCOMPRESSED_BYTES
from skillshield.ui.multipart import Part


class UploadError(ValueError):
    """Raised when an upload cannot be reconstructed into a usable skill input."""


def _safe_relative_path(name: str, root: Path) -> Path | None:
    """Resolve a client-supplied relative filename against ``root``.

    Returns ``None`` (reject -- do not write) if the name is absolute, is a
    Windows drive/UNC path, or would resolve outside ``root`` via ``..``
    segments. Mirrors ``skillshield.ingestion.archive._safe_member_path``
    exactly, since the threat model is identical.
    """
    windows_view = PureWindowsPath(name)
    if windows_view.drive or windows_view.is_absolute():
        return None

    posix_view = PurePosixPath(name.replace("\\", "/"))
    if posix_view.is_absolute():
        return None

    resolved_root = root.resolve()
    target = (root / Path(*posix_view.parts)).resolve()
    try:
        target.relative_to(resolved_root)
    except ValueError:
        return None
    return target


def reconstruct_upload(parts: list[Part]) -> Path:
    """Build a filesystem path suitable for ``skillshield.pipeline.assess()``
    from the parsed multipart parts of one ``/api/assess`` request.

    A single ``skill_zip`` file part -> a path to a temp ``.zip`` file.
    One or more ``skill_files`` file parts (each ``filename`` may carry a
    relative path, e.g. a browser directory picker's ``webkitRelativePath``)
    -> a path to a temp directory with that structure reconstructed.

    Raises ``UploadError`` if neither field is present, if the total upload
    size exceeds the same cap ``ingestion.archive`` enforces for ZIP
    archives, or if any ``skill_files`` part names an unsafe relative path --
    the whole upload is rejected in that case (not just the one bad part),
    for the same reason a ZIP containing one traversal member is rejected
    as a whole rather than partially extracted.
    """
    total_size = sum(len(p.content) for p in parts)
    if total_size > MAX_UNCOMPRESSED_BYTES:
        raise UploadError(f"Upload is too large ({total_size} > {MAX_UNCOMPRESSED_BYTES} bytes)")

    zip_parts = [p for p in parts if p.name == "skill_zip" and p.filename]
    file_parts = [p for p in parts if p.name == "skill_files" and p.filename]

    if zip_parts:
        temp_dir = Path(tempfile.mkdtemp(prefix="skillshield_upload_"))
        zip_path = temp_dir / "upload.zip"
        zip_path.write_bytes(zip_parts[0].content)
        return zip_path

    if file_parts:
        temp_dir = Path(tempfile.mkdtemp(prefix="skillshield_upload_"))
        for part in file_parts:
            target = _safe_relative_path(part.filename, temp_dir)
            if target is None:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise UploadError(f"Upload contains an unsafe relative path: {part.filename!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(part.content)
        return temp_dir

    raise UploadError("No 'skill_zip' or 'skill_files' field found in upload")


def cleanup_upload(path: Path) -> None:
    """Best-effort removal of whatever temp file/directory
    ``reconstruct_upload`` created, mirroring
    ``execution.sandbox``'s own cleanup posture: a locked file on the
    host filesystem must not turn into a failed response."""
    target = path if path.is_dir() else path.parent
    try:
        shutil.rmtree(target, ignore_errors=True)
    except OSError:
        pass
