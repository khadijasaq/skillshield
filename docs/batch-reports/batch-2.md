# Batch 2 Report — P2 (Static Analysis)

## Scope implemented

Per `docs/product-plan.md` §6 and `docs/product-spec.md` §14.

### New: `src/skillshield/analysis/`

- `analysis/__init__.py` — package docstring only.
- `analysis/static/detectors.py` — AST-based detectors: `detect_imports`,
  `detect_known_calls`, `detect_open_calls`, `detect_credential_env_access`,
  combined by `run_all_detectors`. Resolves simple `import X as Y` /
  `from X import Y [as Z]` aliasing. Yields `Hit(capability, detector,
  operation, lineno)`.
- `analysis/static/analyzer.py` — `analyze(skill, artifact) ->
  StaticAnalysisResult(capabilities, evidence, analysis_failures)`. Reads
  and `ast.parse`s each file in `skill.source_files`; a read/parse failure
  is captured per-file and does not abort analysis of the rest.
- `analysis/static/__init__.py` — re-exports `analyze`, `StaticAnalysisResult`,
  `Hit`, `run_all_detectors`.

### Changed: `src/skillshield/conformance/engine.py`

`build_findings()` gained two **optional, additive** parameters so every
Batch 1 call site and test keeps working unchanged:

- `static_evidence: tuple[Evidence, ...] = ()` — real file/line/detector
  evidence is attached to `UNDECLARED_CAPABILITY` (static-only) and
  `STATIC_RUNTIME_MISMATCH` (S-R direction) findings when a matching entry
  exists; otherwise the Batch 1 bare-`Evidence` fallback is used (so
  synthetic-set callers are unaffected).
- `analysis_failures: tuple[str, ...] = ()` — each entry becomes one
  `ANALYSIS_FAILURE` finding.

### Fixtures (new, under `tests/fixtures/skillshield/`)

- `static_undeclared/` — declares only `task.read`; code also calls
  `requests.get(...)` (single undeclared capability: `network.egress`).
- `static_multi_undeclared/` — declares only `task.read`; code also runs
  `subprocess.run`, writes a file, and makes a network call (three
  undeclared capabilities).
- `static_dynamic_gap/` — declares only `task.read`; runs `os.system` via
  `getattr()` indirection, which the detectors (by design) cannot see —
  demonstrates the documented coverage gap.
- `static_syntax_error/` — one valid file (`skill.py`, one undeclared
  capability) plus one file with a deliberate `SyntaxError`
  (`broken_helper.py`), to prove a bad file doesn't abort the rest.
- The existing `sample_skill/` (Batch 1) is reused as the "no detectable
  capability" clean case — its code performs no capability-indicating
  pattern, so `S` is empty.

### Tests

- `tests/unit/test_skillshield_static_detectors.py` — true-positive and
  true-negative coverage for every detector, plus alias-resolution and two
  explicit coverage-gap assertions (dynamic `open()` mode, `getattr()`
  indirection).
- `tests/unit/test_skillshield_static_analyzer.py` — every P2 validation
  scenario from the plan: declared-only (empty S), single undeclared,
  multiple undeclared, no detectable capability, unsupported source
  construct (documented gap), analysis failure with a surviving sibling
  file, and evidence detail (file/line/detector/operation) assertions.
- `tests/integration/test_skillshield_static_analysis_to_findings.py` —
  ingest → `analyze()` → `build_findings()` end-to-end: confirms findings
  carry real evidence (not the Batch-1 bare fallback) and that a parse
  failure surfaces as one `ANALYSIS_FAILURE` finding while the valid
  sibling file's undeclared-capability finding is still produced.

### Docs

- `docs/conformance-rules.md` — new §8 "Static analysis (P2)": the
  detector → capability mapping table, the `ANALYSIS_FAILURE` behavior, and
  an explicit, example-backed statement of the coverage gap (static
  evidence means "may use," not proof).
- `DECISIONS.md` — five new judgment-call entries appended to the existing
  `## P2 (Batch 2)` section (alias-resolution scope, evidence dedup key,
  `open()` mode-matching simplification, multi-capability-per-call
  behavior).

## Validation results

```text
.venv/Scripts/python.exe -m ruff check .
All checks passed!

.venv/Scripts/python.exe -m pytest -q
........................................................................ [ 44%]
........................................................................ [ 88%]
...................                                                      [100%]
163 passed in 0.31s
```

163 passed = 135 from Batch 1 (untouched) + 28 new (19 detector unit tests,
7 analyzer unit tests, 2 integration tests).

## Known limitations (intentional at this stage)

- Static analysis is pure source inspection — it never imports, executes,
  or `exec`'s skill code. It therefore cannot see dynamically-constructed
  capability access (`getattr` indirection, variables holding
  modules/callables, non-literal `open()` arguments, `eval`/`exec`,
  `importlib.import_module`). This is documented, not hidden, per
  `docs/conformance-rules.md` §8.3 — and is exactly the gap controlled
  execution (P3) exists to help close via real runtime observation.
- `S` is still only correlated against a `runtime` parameter that Batch 2's
  own tests pass as an empty set — there is no real runtime evidence yet.
  `STATIC_RUNTIME_MISMATCH` (S-R / R-S) and `POLICY_VIOLATION` (R-P) are
  exercised with synthetic runtime sets in Batch 1's tests only; P3 (runtime)
  and P4 (policy loading) are not yet implemented.
- `credential.read` detection is a literal-string heuristic (key/path
  substring match) — a credential read through any other pattern (e.g. a
  config object attribute, a non-standard secrets manager call) is not
  detected. This is consistent with the plan's "small, extensible
  vocabulary" principle, not a completeness claim.
