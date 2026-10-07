# Batch 4 Report — P4 (D/S/R/P Conformance and Assessment)

## Scope implemented

Per `docs/product-plan.md` §8 and `docs/product-spec.md` §16-§19. All of
P0-P3's correlation/severity/assessment/finding logic already existed and
was correct and was **not** reimplemented. This batch added the one
missing piece (real policy loading) and proved, with real fixtures run
through the real ingestion → static → execution pipeline, that the four
required P4 end-to-end outcomes actually occur.

### New: `src/skillshield/policy/`

- `errors.py` — `PolicyLoadError`.
- `loader.py` — `default_policy()` (permits `{task.read, filesystem.read}`
  only); `load_policy(path | None)` (JSON file → `SecurityPolicy`, `None` →
  default). A malformed policy file (bad JSON, wrong shape, missing/empty
  `name`, or a capability identifier outside the supported vocabulary)
  raises `PolicyLoadError` immediately — deliberately different from how a
  skill's own malformed declaration is handled (never fatal). See
  `DECISIONS.md` ("P4 (Batch 4)").
- `__init__.py` — re-exports `default_policy`, `load_policy`, `PolicyLoadError`.

### New fixtures (`tests/fixtures/skillshield/`)

- `clean_pipeline/` — declares and uses only `filesystem.read` via a plain
  `open(...)` read of a bundled `data.txt`. Under the default policy: zero
  findings.
- `policy_violation_pipeline/` — declares `network.egress` and performs a
  `socket.connect` to a closed local port. Isolates `POLICY_VIOLATION` from
  the undeclared-capability case (the capability *is* honestly declared;
  the default policy still denies it).
- `mismatch_pipeline/` — declares `filesystem.write`; its code's write
  branch is gated on an environment variable (`SKILLSHIELD_FORCE_WRITE`)
  that `execution/sandbox.py`'s environment allow-list never passes
  through, so static analysis sees the `open(..., "w")` call (the AST
  doesn't evaluate the `if`) but controlled execution never takes that
  branch. Isolates `STATIC_RUNTIME_MISMATCH` with no other findings.
- The existing Batch 3 fixture `runtime_undeclared_network/` was reused
  (not duplicated) for the "undeclared behavior" scenario — it already
  declares only `task.read` while performing an undeclared network
  connection, which is exactly this case.

### Tests

- `tests/unit/test_skillshield_policy_loader.py` — `default_policy()`
  shape; `load_policy(None)`; a valid policy file; missing file; malformed
  JSON; missing `name`; wrong `permitted_capabilities` type; unsupported
  capability identifier.
- `tests/integration/test_skillshield_p4_conformance_validation.py` — one
  test per required P4 scenario, each running the real pipeline
  module-by-module (ingest → analyze → execute → `build_findings` →
  `recommend`) and asserting the *exact* expected `Finding` type(s)/
  severities and `Recommendation`, not just "at least one finding."

### Documentation

- `docs/conformance-rules.md` — new §10 (policy loading: default policy
  table + rationale, policy-file format, fatal-vs-non-fatal error-handling
  asymmetry) and §11 (the P4 end-to-end validation table, mapping each
  required scenario to its fixture and exact result).
- `DECISIONS.md` — new `## P4 (Batch 4)` section: the default-policy
  capability choice, the policy-file-is-fatal/declaration-is-not asymmetry,
  reusing the shared capability-vocabulary registry for policy validation,
  and a correction to a pre-existing documentation error (see below).

### Incidental fix: a documentation inaccuracy from Batch 2

While designing `clean_pipeline/`, empirically verified (a 6-line throwaway
script run through `run_all_detectors`) that `docs/conformance-rules.md`
§8.1/§8.3's claim — that `Path(...).read_text()`/`.write_text()` is
detected "when chained directly on the constructor call" — is **false**:
neither the directly-chained nor the variable-assigned form is ever
detected, because the detector's call-target resolution requires the call
base to resolve to an `ast.Name` via import-alias tracking, and a
`Path(...)` constructor call is not an `ast.Name`. Corrected the prose in
§8.1/§8.3 to state this plainly. **No code was changed** — `detectors.py`'s
`_CALL_PATTERNS` dict still carries the now-confirmed-unreachable
`"pathlib.Path.read_text"`-style entries; cleaning those up is Batch 2's
file and out of this batch's scope, so it was left as-is and just noted
here. This is also why `clean_pipeline`/`mismatch_pipeline` use plain
`open(...)` rather than `pathlib.Path` for file I/O.

## Validation results

```text
.venv/Scripts/python.exe -m ruff check .
All checks passed!

.venv/Scripts/python.exe -m pytest -q
........................................................................ [ 35%]
........................................................................ [ 71%]
.........................................................                [100%]
201 passed in 7.20s
```

201 passed = 189 pre-existing (Batches 1-3) + 12 new (7 policy-loader unit
tests + 5 P4 end-to-end integration tests — note the "undeclared behavior"
test asserts two findings, see below).

## Known limitations (intentional at this stage)

- No CLI or UI yet (P5/P6 — next batches).
- Policy remains a flat allow-list with no per-capability scope/conditions,
  consistent with the spec's explicit "do not create a universal policy
  language" constraint.
- The "undeclared behavior" end-to-end case
  (`runtime_undeclared_network/`) legitimately produces **two** findings
  under the default policy (`UNDECLARED_CAPABILITY` HIGH *and*
  `POLICY_VIOLATION` CRITICAL), not one — because the same observed,
  undeclared `network.egress` is also denied by the default policy. This
  is correct per the already-implemented severity rules (an also-undeclared
  policy violation is `CRITICAL`), not a test-writing mistake; the test
  asserts both explicitly rather than asserting "exactly one finding."
- `detectors.py`'s dead `pathlib.Path.*` call-pattern entries (see above)
  were left in place — a cheap cleanup for whoever next touches Batch 2's
  static-analysis code, not addressed here to keep this batch's diff
  scoped to P4.
