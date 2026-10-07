"""SkillShield's local web UI server (docs/product-plan.md P6;
docs/product-spec.md §22-§23).

``ThreadingHTTPServer`` + three static files + one JSON API endpoint. No
new runtime dependency, no build chain (DECISIONS.md "P5/P6"). The UI
contains zero security logic: it calls ``skillshield.pipeline.assess()``
exactly once per ``/api/assess`` request and renders exactly what comes
back. It never itself compares D/S/R/P, applies a policy, computes
severity, or decides a recommendation.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from skillshield.ingestion.archive import MAX_UNCOMPRESSED_BYTES
from skillshield.ingestion.errors import IngestionError
from skillshield.pipeline import assess, assessment_to_jsonable
from skillshield.policy.errors import PolicyLoadError
from skillshield.ui.multipart import MultipartParseError, parse_multipart
from skillshield.ui.uploads import UploadError, cleanup_upload, reconstruct_upload

_STATIC_DIR = Path(__file__).resolve().parent / "static"

#: Reject a request body larger than the archive ingestion's own
#: uncompressed-size cap, plus a small allowance for multipart
#: boundaries/headers (which are not part of the actual file content).
MAX_REQUEST_BODY_BYTES = MAX_UNCOMPRESSED_BYTES + 1024 * 1024

#: Server-side default timeout for a UI-triggered assessment. The UI does
#: not currently expose a way to change this (no policy/timeout controls
#: in the page) -- see docs/batch-reports/batch-6.md.
DEFAULT_TIMEOUT_SECONDS = 10.0

_STATIC_FILES: dict[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
}


def _error_json(kind: str, exc: Exception) -> bytes:
    return json.dumps(
        {"error": {"kind": kind, "type": type(exc).__name__, "message": str(exc)}}
    ).encode("utf-8")


class SkillShieldRequestHandler(BaseHTTPRequestHandler):
    """Handles the UI's three static routes and the one assessment API route."""

    server_version = "SkillShieldUI/1.0"

    def log_message(self, format: str, *args) -> None:
        pass  # keep CLI/test output quiet; failures are still visible in HTTP responses

    def do_GET(self) -> None:
        entry = _STATIC_FILES.get(self.path)
        if entry is None:
            self.send_error(404, "Not found")
            return
        filename, content_type = entry
        data = (_STATIC_DIR / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if self.path != "/api/assess":
            self.send_error(404, "Not found")
            return

        content_length_header = self.headers.get("Content-Length")
        if content_length_header is None:
            self._send_json(400, _error_json("request", ValueError("Missing Content-Length")))
            return
        try:
            content_length = int(content_length_header)
        except ValueError:
            self._send_json(400, _error_json("request", ValueError("Invalid Content-Length")))
            return
        if content_length > MAX_REQUEST_BODY_BYTES:
            self._send_json(
                413,
                _error_json(
                    "request",
                    ValueError(
                        f"Request body too large ({content_length} > "
                        f"{MAX_REQUEST_BODY_BYTES} bytes)"
                    ),
                ),
            )
            return

        body = self.rfile.read(content_length)
        content_type = self.headers.get("Content-Type", "")

        upload_path: Path | None = None
        try:
            parts = parse_multipart(body, content_type)
            upload_path = reconstruct_upload(parts)
            assessment = assess(upload_path, timeout_seconds=DEFAULT_TIMEOUT_SECONDS)
        except (MultipartParseError, UploadError) as exc:
            self._send_json(400, _error_json("request", exc))
            return
        except IngestionError as exc:
            self._send_json(400, _error_json("ingestion", exc))
            return
        except PolicyLoadError as exc:
            self._send_json(400, _error_json("policy", exc))
            return
        finally:
            if upload_path is not None:
                cleanup_upload(upload_path)

        self._send_json(200, json.dumps(assessment_to_jsonable(assessment)).encode("utf-8"))

    def _send_json(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """Build (but do not start) a SkillShield UI server.

    ``port=0`` binds an OS-assigned ephemeral port, readable afterward via
    ``server.server_address`` -- used by tests so they never collide on a
    fixed port.
    """
    return ThreadingHTTPServer((host, port), SkillShieldRequestHandler)
