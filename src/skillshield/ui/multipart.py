"""Minimal, dependency-free ``multipart/form-data`` request-body parser.

Python's ``cgi.FieldStorage`` is deprecated (PEP 594) and removed in newer
Python versions, so it must not be used. This module implements exactly
what the SkillShield UI needs: named parts, each either a plain field or a
file field (carrying a ``filename``), as raw bytes. It does not handle
nested multipart, non-form content types, or boundary bytes that happen to
collide with uploaded content -- browser-chosen boundaries are
high-entropy specifically to avoid that, and this is a local single-user
development UI, not a hardened general-purpose form parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_BOUNDARY_RE = re.compile(r'boundary="?([^";]+)"?', re.IGNORECASE)
_DISPOSITION_RE = re.compile(r"Content-Disposition:\s*form-data;(.*)", re.IGNORECASE)
_NAME_RE = re.compile(r'name="([^"]*)"')
_FILENAME_RE = re.compile(r'filename="([^"]*)"')


class MultipartParseError(ValueError):
    """Raised when a request body cannot be parsed as its content-type claims."""


@dataclass(frozen=True)
class Part:
    """One parsed part of a multipart/form-data body."""

    name: str
    filename: str | None
    content: bytes


def parse_boundary(content_type: str) -> bytes:
    """Extract the boundary token from a ``Content-Type`` header value."""
    if not content_type or "multipart/form-data" not in content_type.lower():
        raise MultipartParseError(f"Not a multipart/form-data content-type: {content_type!r}")
    match = _BOUNDARY_RE.search(content_type)
    if match is None:
        raise MultipartParseError(f"No boundary found in content-type: {content_type!r}")
    return match.group(1).encode("ascii")


def parse_multipart(body: bytes, content_type: str) -> list[Part]:
    """Parse a raw ``multipart/form-data`` request body into ``Part`` objects."""
    boundary = parse_boundary(content_type)
    delimiter = b"--" + boundary
    if delimiter not in body:
        raise MultipartParseError("Boundary not found in request body")

    segments = body.split(delimiter)
    # segments[0] is the preamble before the first boundary (normally empty);
    # segments[-1] is the remainder after the final boundary (the "--" close
    # suffix and anything after it). Everything in between is one part.
    parts: list[Part] = []
    for segment in segments[1:-1]:
        if segment.startswith(b"\r\n"):
            segment = segment[2:]
        if b"\r\n\r\n" not in segment:
            raise MultipartParseError("Malformed multipart part: no header/body separator")
        header_block, content = segment.split(b"\r\n\r\n", 1)
        if content.endswith(b"\r\n"):
            content = content[:-2]

        headers = header_block.decode("utf-8", errors="replace")
        disposition_match = _DISPOSITION_RE.search(headers)
        if disposition_match is None:
            raise MultipartParseError("Malformed multipart part: missing Content-Disposition")
        disposition = disposition_match.group(1)

        name_match = _NAME_RE.search(disposition)
        if name_match is None:
            raise MultipartParseError("Malformed multipart part: missing field name")
        name = name_match.group(1)

        filename_match = _FILENAME_RE.search(disposition)
        filename = filename_match.group(1) if filename_match else None

        parts.append(Part(name=name, filename=filename, content=content))
    return parts
