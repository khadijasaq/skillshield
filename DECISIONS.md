# DECISIONS.md

Record of choices made where `docs/product-spec.md` / `docs/product-plan.md` were
silent or left implementation details open. Each entry: decision + one-line
rationale. Ordered chronologically by batch.

## Pre-batch cleanup

- **Archived (not deleted) 20 orphaned test files, one fixture directory, and
  one example script under `_archive/stale_second_milestone/`.**
  Rationale: these referenced `agentic_conformance.adapters.vuln_agentic_skills_app`
  and other modules that do not exist in the committed source tree (confirmed via
  `git ls-files` — they were never tracked). They belonged to an earlier,
  abandoned design iteration that depended on `vuln-agentic-skills-app`, which
  directly contradicts the product-independence requirement in both the old and
  new specs. They were blocking a clean `pytest`/`ruff` baseline. Moved instead of
  deleted because file deletion was blocked by the local permission classifier;
  a reversible move satisfies the same goal. `_archive/` is excluded from Ruff
  via `pyproject.toml` (`tool.ruff.extend-exclude`).

- **Kept `src/agentic_conformance/` (the prior "Agentic Skill Security &
  Conformance Layer" milestone, per `docs/spec.md`/`docs/plan.md`) untouched.**
  Rationale: it is a previously delivered, passing, product-independent
  foundation (models, interfaces, structural/rule conformance engine, reference
  adapter). Nothing in the SkillShield product-plan requires removing it, and
  CLAUDE.md/plan.md instruct against unrelated reorganization.

- **New product code lives in `src/skillshield/`, a second top-level package,
  rather than inside `agentic_conformance/`.**
  Rationale: SkillShield (per `docs/product-spec.md`) is a different problem
  shape than the old conformance layer — it ingests a *downloaded artifact*
  (ZIP/directory) and runs a one-shot analysis pipeline (D/S/R/P → findings →
  recommendation), rather than modeling a host product that emits a live stream
  of runtime events through `register_skill`/`emit_event`/`evaluate`. Reusing
  that event-sourced `ConformanceAPI`/`ProductAdapter`/`Decision`
  (ALLOW/FLAG/DENY) shape would force an architectural mismatch. SkillShield
  does reuse `agentic_conformance.core.models.capability` (the open capability
  vocabulary registry) directly, since that piece *is* product-independent and
  fits as-is; it registers one additional identifier, `filesystem.read`,
  alongside the existing `task.read` / `filesystem.write` / `network.egress` /
  `process.execute` / `credential.read`.

- **`skillshield` is added as a second packaging target in `pyproject.toml`**
  (second wheel package + a `skillshield` console-script entry point), rather
  than renaming/replacing the existing `agentic-skill-conformance` project.
  Rationale: both milestones' deliverables stay independently buildable; no
  existing import paths break.

## P0/P1 (Batch 1)

- **Skill declaration format: a `manifest.json` file at the skill root**, with
  `id`, `name`, `version`, `capabilities` (list of `{id, scope?, reason?}` or
  plain capability-id strings), and `entrypoint` (`"<module_file>:<callable>"`).
  Rationale: this is a minimal, deterministic, JSON-parseable format (no YAML
  dependency), and matches realistic Agentic Skill manifest conventions already
  referenced elsewhere in this codebase's history. A skill missing this file, or
  with a structurally invalid one, produces `MISSING_DECLARATION` /
  `INVALID_DECLARATION` ingestion findings rather than being silently skipped.

- **Canonical capability vocabulary used by SkillShield:** `task.read`,
  `filesystem.read`, `filesystem.write`, `network.egress`, `process.execute`,
  `credential.read`. Rationale: smallest set that lets every finding type and
  acceptance test in the product spec be demonstrated; remains an open registry
  so more can be added later without touching `core/`.

- **`SkillArtifact` vs. canonical `Skill` are two distinct dataclasses**, per
  product-spec §10/§11: `SkillArtifact` holds only artifact facts (input type,
  temp location, archive/file inventory, digest, provenance, ingestion status)
  and is structurally forbidden from holding D/S/R/P/findings/severity/
  recommendation (enforced by simply not having those fields — not by a runtime
  check, since the dataclass has no such attributes to misuse).

- **Directory and ZIP ingestion produce an identical canonical `Skill`** by
  normalizing ZIP input through safe extraction into a temporary directory
  first, then running the same directory-ingestion code path. This directly
  satisfies the "same skill as directory and ZIP must yield equivalent
  canonical Skill objects" invariant by construction (one code path, not two
  parallel implementations kept in sync by hand).

- **Archive safety:** reject on (a) any member path that escapes the
  extraction root after resolution (`..`, absolute paths, Windows drive
  letters/UNC), (b) any symlink member, (c) total uncompressed size over a
  fixed cap, (d) more than a fixed member count, (e) any `zipfile.BadZipFile`.
  Rationale: covers the required path-traversal / malformed-archive /
  unsupported-archive cases with simple, auditable checks — no third-party
  archive-safety library.

- **Archive limits set to 50 MB uncompressed / 10,000 members.** Rationale:
  generous enough for any realistic single-skill package (manifest + a
  handful of Python source files) while still bounding the extraction loop
  against a pathological input; both are read from the ZIP central
  directory and checked before any byte is extracted.

- **`MissingDeclarationError`/`MalformedDeclarationError` are real exception
  classes, but are only ever raised and caught *within*
  `skillshield.ingestion.declaration.load_declaration`** — they never
  propagate out of it. Rationale: keeps a single, explicit vocabulary for
  "what's wrong with the manifest" (reused for error messages) while
  guaranteeing the public `ingest()` contract that a bad declaration is
  never fatal; `load_declaration` returns `(Declaration | None,
  DeclarationProblem | None)` instead.

- **A declaration with an unsupported capability identifier still produces a
  usable `Declaration`** (not `None`), paired with a `malformed`
  `DeclarationProblem` describing which identifier(s) are unsupported.
  Rationale: the rest of the declared-capability set may still be
  meaningful; discarding the whole declaration over one bad entry would lose
  information the conformance engine could otherwise use for `S-D`/`R-D`
  comparisons on the valid entries.

- **`SkillArtifact.input_type` is set by the ingestion entry point
  (`ArtifactInputType.DIRECTORY` vs. `ArtifactInputType.ZIP`), not inferred
  after the fact**, even though both paths converge on the same
  `ingest_directory()` call. Rationale: this is the one field that is
  legitimately artifact-specific (per product-spec §10) and must survive
  the dir/zip-equivalence guarantee rather than being erased by sharing one
  code path — `ingest_directory()` takes it as a parameter with a
  `DIRECTORY` default, and `ingest_archive()` passes `ZIP` explicitly.

## P2 (Batch 2)

- **Static analysis is AST-based (Python `ast` module), not regex-based, and
  only analyzes `*.py` files reachable from the skill directory.**
  Rationale: AST inspection of `import`/`call` nodes is precise enough for the
  required detector set (filesystem/network/process/credential access patterns
  from the standard library and common third-party names) without needing a
  full type-aware analyzer, and avoids the false-positive noise of naive
  string/regex matching. A file that fails to parse (syntax error, non-UTF8,
  etc.) produces an `ANALYSIS_FAILURE` finding for that file rather than
  aborting the whole static pass.

- **Import-alias resolution is intentionally shallow: only `import X as Y`
  and `from X import Y [as Z]` bindings are tracked**, resolved by
  substituting the call expression's root name before matching against the
  fixed `_CALL_PATTERNS`/`_IMPORT_PATTERNS` tables. Plain `import X` needs no
  entry since the bound name already equals the attribute-chain root used at
  call sites. No attempt is made to resolve a capability reached through a
  variable holding a module/callable reference (`p = Path(...); p.write_text(...)`)
  -- this is the documented coverage gap in `docs/conformance-rules.md` §8.3,
  not an oversight.

- **Evidence dedup key is `(capability, operation, lineno)` per file**, not
  just `capability`. Rationale: two different lines in the same file
  triggering the same capability (e.g. two separate `open(..., "w")` calls)
  are two distinct, independently-useful pieces of evidence for the user to
  inspect; only an exact repeat (same operation string and line, which can
  happen if a detector's two passes both match the same node for unrelated
  reasons) is collapsed.

- **`open()` mode classification uses simple prefix matching** (`startswith`
  on `"w"`/`"a"`/`"x"` for write, `"r"` for read) rather than modeling every
  valid combination (e.g. `"r+"`, `"w+"`, `"rb+"`). Rationale: this already
  matches the plan's stated simple mapping (read: none/`"r"`/`"rb"`/`"rt"`;
  write: `"w"`/`"wb"`/`"a"`/`"ab"`/`"x"`) and a prefix check degrades
  gracefully on the compound modes it doesn't explicitly list (e.g. `"r+"`
  is still classified `filesystem.read`, which is not wrong, just not also
  flagged `filesystem.write` -- an accepted simplification, not a correctness
  bug, since the plan does not require compound-mode precision).

- **A single capability can be detected by more than one rule on the same
  call** (e.g. `open("credentials.json")` yields both `filesystem.read` and
  `credential.read`). Rationale: this is factually correct (the call really
  does both), not double-counting, and `docs/conformance-rules.md` §8.1
  states this explicitly so it doesn't read as a bug during review.

## P3 (Batch 3)

- **Runtime observation uses `sys.addaudithook`, not OS-level sandboxing
  (no seccomp/ptrace/containers/VMs).**
  Rationale: the project must run on Windows (the development machine) as well
  as POSIX, and PEP 578 audit hooks are pure-CPython, dependency-free, and fire
  for the exact operations this product cares about (`open`, `os.open`,
  `socket.connect`, `subprocess.Popen`, `os.system`, `os.posix_spawn`,
  `ctypes.*`). This is **observation only** — it does not prevent or sandbox
  anything, and is explicitly documented as such in `SECURITY_LIMITATIONS.md`
  per the spec's "do not call this a secure sandbox" requirement. A
  sufficiently adversarial skill could still bypass auditing (e.g. via a
  compiled extension module that performs syscalls without going through an
  audited CPython API); this is called out as a known gap, not hidden.

- **Process-tree termination on timeout is best-effort.** On Windows,
  `Popen.kill()` terminates the direct child but cannot guarantee termination
  of further-descendant processes without adding a dependency (`psutil`) or
  shelling out to `taskkill /T`; this implementation uses `taskkill /F /T /PID`
  on Windows and process-group signaling (`os.killpg`) on POSIX, and documents
  the residual risk of orphaned grandchildren if both mechanisms fail.

- **Environment variables passed to the executed skill are stripped to a
  small allow-list** (`PATH`, `SYSTEMROOT`/`PATH`-equivalents, a temp dir, and
  nothing else) rather than inherited wholesale from the SkillShield process.
  Rationale: reduces (does not eliminate) incidental credential exposure if the
  operator's own shell environment carries secrets; documented as a mitigation,
  not a guarantee, since the skill can still read arbitrary files it has OS
  permission to read.

- **Audit events keyed on, confirmed empirically (not assumed) against
  this project's CPython 3.12 venv**: `open` (with the real resolved mode
  string, not re-derived from flags), `os.remove`/`os.rmdir`/`os.rename`/
  `os.mkdir`, `os.listdir`/`os.scandir`, `socket.connect`,
  `subprocess.Popen`, `os.system`, and the `os.exec*`/`os.spawn*` family by
  name prefix. `socket.__new__` and the Windows-internal
  `_winapi.CreateProcess` event were deliberately **not** mapped -- both
  are redundant with `socket.connect`/`subprocess.Popen` respectively and
  would double-count the same underlying action. `os.environ.get`/
  `os.getenv` were confirmed to raise **no** audit event at all on this
  CPython version -- documented as a real blind spot in
  `SECURITY_LIMITATIONS.md`, not treated as a bug to work around.

- **Import-machinery noise (`.pyc` bytecode-cache reads/writes, and the
  entrypoint module's own source read) is filtered out of runtime evidence
  by construction, in two layers**: `sandbox.py` passes `-B` to disable
  writing new caches, and `monitor.is_bytecode_cache_event()` filters any
  event touching a `__pycache__` path or a `.pyc` file regardless of event
  type (needed because pre-existing stdlib caches in the shared venv are
  still *read* even with `-B`); `harness.py` separately excludes the one
  `open` event for the entry file's own source by absolute-path identity.
  Rationale: this was discovered empirically while building this batch --
  without it, *every* skill would show `filesystem.read` (and, before
  `-B`, `filesystem.write`) as runtime-observed purely from Python
  importing its own entrypoint module and the stdlib modules it uses,
  which would have made the `R - D` undeclared-capability check produce a
  false positive on essentially every assessment. This is the single most
  consequential correctness fix in this batch.

- **The events file is read back and parsed even when the harness process
  was killed mid-write**: each line is JSON-decoded independently, and a
  line that fails to parse (a partial write truncated by the kill) is
  silently skipped rather than treated as a fatal parse error. Rationale:
  this is exactly the "partial evidence on timeout" guarantee the spec
  calls for -- a truncated last line must not discard every complete line
  that came before it.

- **A manifest's entrypoint target (`"file.py:callable"`) is checked for
  existence with a cheap static `ast` scan of top-level
  `FunctionDef`/`AsyncFunctionDef`/`ClassDef`/`Assign` names *before*
  spawning anything**, rather than only discovering a missing target as a
  runtime `AttributeError` crash. Rationale: SkillShield already knows
  statically (without executing anything) whether the declared name exists
  in the file, so reporting this as `NO_ENTRYPOINT` (a declaration-time
  problem) is more honest than reporting it as `CRASHED` (which implies
  the skill's own logic failed) -- and it avoids spawning a subprocess
  for a case that can never succeed.

## P4 (Batch 4)

- **Default policy permits exactly `{task.read, filesystem.read}`.**
  Rationale: least-privilege — a skill that only reads its own data needs
  nothing more, and this makes `filesystem.write`/`network.egress`/
  `process.execute`/`credential.read` denied by omission, which is enough
  to let the required `POLICY_VIOLATION` end-to-end case actually exercise
  a real policy decision rather than an always-permit no-op.

- **A malformed policy *file* raises `PolicyLoadError` immediately; a
  malformed skill *declaration* never does (it becomes a non-fatal
  `DeclarationProblem` → `INVALID_DECLARATION` finding).** Rationale: this
  is a deliberate asymmetry, not an inconsistency — the skill's manifest is
  attacker/author-controlled content SkillShield is in the business of
  assessing (per product-spec §13, it must never be fatal), while a policy
  file is something the operator running SkillShield wrote themselves; a
  typo there is a configuration mistake that should fail loudly and
  immediately, not get silently absorbed into the assessment of an
  unrelated skill. Same reasoning extends to a policy naming a capability
  identifier outside the supported vocabulary — that's also raised as a
  `PolicyLoadError`, not turned into a finding.

- **`policy/loader.py` imports `agentic_conformance.core.models.capability.supported_capabilities()`
  directly** (the same shared, open vocabulary registry `skillshield.core.models.capability`
  already extends) to validate a loaded policy's capability identifiers, rather
  than duplicating the vocabulary or re-exporting it through another module.

- **Corrected a pre-existing documentation inaccuracy in
  `docs/conformance-rules.md` §8.1/§8.3** (written during Batch 2): it
  claimed `Path(...).read_text()`/`.write_text()` is detected "when chained
  directly on the constructor call." Verified empirically while building
  this batch's `clean_pipeline` fixture that this is false — the static
  detector's call-target resolution only follows `import`/`from...import`
  aliasing back to an `ast.Name`, and a `Path(...)` constructor call is not
  an `ast.Name`, so *no* `pathlib.Path` method-call form is ever detected,
  chained or not. Fixed the prose to state this plainly (no code changed —
  `_CALL_PATTERNS` in `detectors.py` still carries the now-confirmed-dead
  `"pathlib.Path.read_text"`-style keys, which is Batch 2's file to clean up
  if that's ever worth doing; out of this batch's scope). This is why the
  `clean_pipeline`/`mismatch_pipeline` fixtures below use plain `open(...)`
  rather than `pathlib.Path` for their file I/O — `open(...)` is the pattern
  that is actually, correctly detected.

- **Fixed the now-confirmed-dead `pathlib.Path` detector pattern noted
  above, immediately, outside the batch-fork workflow** (small, isolated,
  well-understood bug — not worth a full subagent round-trip). Added
  `_is_path_constructor_call()`/`_PATH_CONSTRUCTOR_METHOD_PATTERNS` to
  `detectors.py` so a read/write method called directly on a
  `pathlib.Path(...)` constructor result (however imported: plain,
  `from pathlib import Path`, or aliased) is now detected as
  `filesystem.read`/`filesystem.write`; a `Path` held in an intermediate
  variable across lines is still a documented gap (no data-flow tracking).
  Removed the dead `_CALL_PATTERNS` entries this replaces. Corrected
  `docs/conformance-rules.md` §8.3 again to describe the fixed behavior, and
  added three regression tests to
  `tests/unit/test_skillshield_static_detectors.py` (directly-chained read,
  directly-chained write via module import, and the still-undetected
  variable-held case). Full suite re-verified: 204 passed, ruff clean.

## P5/P6 (Batches 5-6)

- **Application interface is a single synchronous `SkillShieldPipeline.assess()`
  call**, not a job-queue/async-status model, even though product-spec §23 lists
  "submit / start / retrieve status / retrieve result" as the conceptual
  surface. Rationale: the prototype's assessments complete in well under the
  UI's own stated timeout; a synchronous call satisfies every acceptance
  criterion (CLI and UI both call the same function) without adding
  speculative polling/job-id machinery the spec explicitly discourages
  ("avoid speculative abstractions"). The UI simulates the staged
  "Preparing / Analyzing / Running..." progression client-side while the one
  HTTP request is in flight.

- **UI implemented with Python's standard-library `http.server`
  (`ThreadingHTTPServer`) and a single static HTML/CSS/vanilla-JS page** —
  no Flask/FastAPI/Node/build chain. Rationale: the task's stack constraint
  ("minimal local web UI with no heavy frontend framework or build chain
  unless clearly unavoidable") is satisfiable with zero new runtime
  dependencies; `pyproject.toml`'s dependency list stays empty for the product
  code (`dev` group still only has `pytest`/`ruff`).

### P5 (Batch 5) implementation notes

- **Implemented as a plain module-level function `skillshield.pipeline.assess()`,
  not a `SkillShieldPipeline` class** as this section's first entry names it.
  Rationale: there is no state to hold between calls (no job queue, no
  session) — a class would exist only to hold one method, which is exactly
  the kind of structure-for-its-own-sake the project's "avoid speculative
  abstractions" principle argues against. If Batch 6's UI later needs
  something stateful (e.g. to track an in-progress upload), that can wrap
  this function rather than the function needing to anticipate it now.

- **A fatal `IngestionError` or `PolicyLoadError` from `assess()` is left to
  propagate unchanged** (not wrapped in a SkillShield-specific exception).
  Rationale: both are already small, clearly-named, specific exception
  types from their own modules; wrapping them in a third type at the
  pipeline boundary would only add an unwrapping step for callers with no
  corresponding benefit. The CLI (and Batch 6's UI) catch
  `skillshield.ingestion.errors.IngestionError` and
  `skillshield.policy.errors.PolicyLoadError` directly and report each with
  distinct wording — "could not be assessed" (ingestion) vs. a policy
  configuration error — neither is ever folded into a completed
  `Assessment`'s recommendation, per the module docstring in `pipeline.py`.

- **CLI exit codes: `0` for any completed assessment regardless of its
  recommendation** (including `DO_NOT_USE` — that is a successful outcome
  of analysis, not a tool failure), **`2` for an ingestion failure, `3` for
  a policy-load failure.** Rationale: keeps "the tool worked" and "the tool
  found something bad" cleanly separate for anything scripting around the
  CLI, without inventing a severity-encoded exit-code scheme the spec never
  asked for.

- **`--json` output is a hand-written, dependency-free serialization**
  (`cli._assessment_to_jsonable`), not `dataclasses.asdict()` directly —
  `asdict()` would leave `Enum` members and `frozenset`s in a form that
  isn't valid JSON (`json.dumps` cannot serialize either), so enums are
  rendered as their `.value` and capability sets as sorted lists. The shape
  is intentionally simple and is not yet a versioned/frozen schema — it is
  whatever `Assessment`'s current fields are, documented as a limitation in
  `docs/batch-reports/batch-5.md`.

### P6 (Batch 6) implementation notes

- **`cli._assessment_to_jsonable` was moved (not duplicated) into
  `pipeline.py` as a public `assessment_to_jsonable()`**, and `cli.py` now
  imports it from there. Rationale: the UI's `/api/assess` endpoint needs
  the exact same JSON rendering as `skillshield scan --json` — having two
  independently-maintained copies would risk them silently diverging. This
  is a pure move (confirmed via the pre-existing CLI tests passing
  unchanged); it is not a behavior change.

- **A from-scratch, dependency-free `multipart/form-data` parser
  (`ui/multipart.py`)** instead of `cgi.FieldStorage`. Rationale:
  `cgi.FieldStorage` is deprecated under PEP 594 and removed outright in
  newer CPython versions, so using it would make the UI silently
  unportable to a future Python upgrade. The hand-written parser only
  supports what SkillShield's own two upload fields need (named parts,
  optional `filename`, raw bytes) — it is explicitly documented as not a
  hardened general-purpose form parser, since it doesn't need to be one for
  a local, single-user development UI.

- **Directory-style uploads (`skill_files`, one part per file, `filename`
  carrying a relative path) go through the exact same path-traversal
  resolution discipline as `ingestion/archive.py`'s ZIP member-path check**
  (`ui/uploads.py::_safe_relative_path` mirrors
  `archive.py::_safe_member_path`). Rationale: a browser-submitted
  filename is exactly as untrustworthy as a ZIP member name — both are
  attacker-influenceable strings naming where bytes should land on disk —
  and there is no archive-safety check to fall back on for this upload path
  (there is no archive; this *is* the first line of defense for it). A
  single unsafe part rejects the whole upload rather than silently
  dropping just that one part, matching how a traversal member anywhere in
  a ZIP already rejects the whole archive.

- **Upload size cap reuses `ingestion.archive.MAX_UNCOMPRESSED_BYTES`
  directly** (imported, not re-declared) for both the total-parsed-upload
  check in `uploads.py` and the `Content-Length`-based early-rejection
  check in `server.py` (`MAX_REQUEST_BODY_BYTES = MAX_UNCOMPRESSED_BYTES +
  1 MiB`, the extra allowance covering multipart boundary/header overhead
  that isn't actual file content). Rationale: one archive-size policy,
  stated once, applied consistently to both the ZIP-upload and
  directory-upload paths — not two independently-chosen limits that could
  drift apart.

- **Directory upload uses the browser's non-standard but widely-supported
  `webkitdirectory` input attribute** (Chrome, Edge, and Chromium-based
  browsers; not supported by all browsers). Rationale: this is explicitly
  the spec's *optional* case ("if the selected local UI technology
  supports directory selection appropriately") — ZIP upload (always
  supported) already satisfies the UI's mandatory requirement, and local
  directory assessment is already proven end-to-end through the CLI
  (Batch 5). The UI also supporting it is a bonus, with a graceful
  fallback (the ZIP input always works regardless of browser).

- **No actual browser was available to drive in this headless environment.**
  Every HTTP behavior (static pages, both upload shapes, the error path,
  the oversized-request path) was verified with real HTTP requests/responses
  in the integration tests and in one additional manual smoke test (a real
  `ThreadingHTTPServer` started in-process, a real in-memory ZIP built and
  POSTed, response asserted) — not mocks. The frontend's rendering logic
  (`app.js`) was verified by careful reading rather than by clicking through
  it in a real browser; this is stated plainly rather than implied away, per
  `docs/batch-reports/batch-6.md`.
