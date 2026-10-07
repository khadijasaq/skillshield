# Batch 6 Report — P6 (Functional SkillShield UI)

## Scope implemented

Per `docs/product-plan.md` §10-§11 and `docs/product-spec.md` §22. This is
the last implementation batch before final end-to-end acceptance
verification (AC1-AC13).

### Shared JSON serialization (small refactor)

- `cli._assessment_to_jsonable` was moved into `pipeline.py` as a public
  `assessment_to_jsonable()`. `cli.py` now imports it. Pure move — the
  existing CLI tests pass unchanged.

### `src/skillshield/ui/` (new package)

- `multipart.py` — a from-scratch, dependency-free `multipart/form-data`
  parser (`parse_multipart`, `parse_boundary`, `Part`, `MultipartParseError`).
  `cgi.FieldStorage` was deliberately avoided (deprecated/removed in recent
  Python).
- `uploads.py` — `reconstruct_upload(parts) -> Path` (a single `skill_zip`
  field → a temp `.zip` file; one or more `skill_files` fields → a
  reconstructed temp directory, applying the same path-traversal
  resolution discipline as `ingestion/archive.py`'s ZIP member-path check),
  `cleanup_upload()`, `UploadError`.
- `server.py` — `SkillShieldRequestHandler` (`ThreadingHTTPServer`-based):
  `GET /`, `GET /app.js`, `GET /app.css` (three fixed named routes, no
  generic static-file server), `POST /api/assess` (parses the upload, calls
  `skillshield.pipeline.assess()` once, returns its JSON rendering or a
  structured `{"error": {...}}` body on `IngestionError`/`PolicyLoadError`/
  a malformed or oversized request). `create_server(host, port)` factory
  (port `0` for an OS-assigned ephemeral port, used by tests).
- `static/index.html`, `static/app.css`, `static/app.js` — the page itself.
  Zero security logic in the JS: it renders exactly what `/api/assess`
  returns (recommendation, D/S/R/P capability summary with names, findings
  with an expandable "View Evidence" section per finding, limitations) and
  simulates staged progress messages client-side around the one real
  request, per the decision already recorded under "P5/P6" in
  `DECISIONS.md`. Supports both required-and-optional upload shapes: a
  `.zip` file input (always available) and an optional local-folder picker
  via the browser's `webkitdirectory` attribute.

### CLI integration

- `skillshield ui [--host 127.0.0.1] [--port 8765]` — builds the server via
  `create_server()` and calls `serve_forever()` in the foreground, printing
  the bound URL first. `Ctrl+C` stops it cleanly (`server.server_close()`
  in a `finally`).

## Changed files

- `src/skillshield/pipeline.py` (added `assessment_to_jsonable`)
- `src/skillshield/cli.py` (uses the moved function; added the `ui` subcommand)
- `DECISIONS.md` (new `### P6 (Batch 6) implementation notes` subsection)

## New files

- `src/skillshield/ui/{__init__,multipart,uploads,server}.py`
- `src/skillshield/ui/static/{index.html,app.css,app.js}`
- `tests/unit/test_skillshield_ui_multipart.py` (9 tests)
- `tests/unit/test_skillshield_ui_uploads.py` (9 tests)
- `tests/integration/test_skillshield_ui_server.py` (7 tests)
- `docs/batch-reports/batch-6.md` (this file)

## Validation results

```text
.venv/Scripts/python.exe -m ruff check .
All checks passed!

.venv/Scripts/python.exe -m pytest -q
245 passed
```

245 passed = 220 pre-existing + 25 new (9 multipart unit + 9 upload unit +
7 server integration).

A manual, independent live smoke test was also run directly against
`create_server()` (not through the CLI, to isolate the server itself): a
real `ThreadingHTTPServer` started in a background thread, a real
in-memory ZIP of the `clean_pipeline` fixture built and POSTed as a real
`multipart/form-data` body over a real socket (`urllib.request`, no
mocks), and the JSON response's `recommendation` field confirmed to read
`"NO ISSUES FOUND"`. `GET /` was confirmed to return HTTP 200 with
`SkillShield` present in the HTML body.

## Honesty note — what "verified" means for the UI in this batch

**No actual web browser was driven in this headless CLI environment.**
This is stated plainly rather than implied away. What was verified, with
real (not mocked) HTTP traffic:

- Every route (`GET /`, `GET /app.js`, `GET /app.css`, `POST /api/assess`)
  responds with the correct status, content-type, and body shape.
- Both upload forms (`skill_zip` single-file, `skill_files` multi-part
  directory reconstruction) correctly reach `pipeline.assess()` and produce
  the expected recommendation for a known fixture.
- The error path (a deliberately malformed/path-traversal ZIP) returns
  `400` with a structured `{"error": {...}}` body, distinct from a
  completed assessment.
- The oversized-request-body rejection path (`413`) is reachable via the
  `Content-Length` check before the body is even read.

What was **not** verified by driving an actual browser: that `app.js`'s
DOM-manipulation code renders correctly when a human clicks through it,
that the `webkitdirectory` folder picker behaves as expected in a real
browser, that the CSS actually looks right visually. `app.js` was read
carefully end-to-end and its logic traced against the exact JSON shape
`assessment_to_jsonable()` produces (confirmed to match field-for-field),
but reading code is not the same as seeing it render. This gap is honest
and intentional to disclose, not hidden behind "the UI works."

## Known limitations

- No actual browser-driven visual verification (see above) — a genuine
  constraint of this headless environment, not a shortcut taken for
  convenience.
- Directory upload depends on the non-standard (though widely supported in
  Chromium-based browsers) `webkitdirectory` attribute; it has a graceful
  fallback (the ZIP input always works) and local-directory assessment is
  already proven end-to-end through the CLI (Batch 5) regardless.
- The server is a single-user local development tool: no authentication,
  no TLS, and it is not intended to be exposed beyond `127.0.0.1`.
- The UI does not expose policy-file selection or a custom timeout — it
  always uses `pipeline.assess()`'s default policy and a fixed server-side
  timeout (`DEFAULT_TIMEOUT_SECONDS = 10.0` in `server.py`). The CLI's
  `--policy`/`--timeout` flags remain the way to use a non-default policy
  or timeout in this prototype.
- `--json`'s schema (reused here for the UI's API response) is still
  whatever `Assessment`'s current fields are, not a versioned/frozen
  contract (same limitation already noted in `docs/batch-reports/batch-5.md`).
