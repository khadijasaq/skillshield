# Batch 3 Report — P3 (Controlled Execution + Runtime Monitoring)

## Scope implemented

Per `docs/product-plan.md` §7 and `docs/product-spec.md` §15, §21.

### `src/skillshield/execution/`

- `result.py` — `ExecutionStatus` (`OK`/`TIMEOUT`/`CRASHED`/`NO_ENTRYPOINT`),
  `ExecutionResult`.
- `monitor.py` — `translate_event()` (audit event → capability + detail),
  `is_bytecode_cache_event()` (import-machinery noise filter).
- `harness.py` — the child-process entry point
  (`python -m skillshield.execution.harness <skill_dir> <entry_file>
  <entry_attr> <events_file>`): opens the events file before installing
  the audit hook, filters bytecode-cache and self-import noise, imports
  and calls the entrypoint, reports `ok`/`crashed`.
- `sandbox.py` — `execute(skill, artifact, timeout_seconds=10.0)`:
  resolves and statically validates the entrypoint, copies the artifact
  into a scratch directory, builds a minimal environment, spawns the
  harness with `-B` and platform-appropriate process-group creation,
  enforces the timeout, kills the whole process tree on timeout
  (`taskkill /F /T` on Windows, `killpg(SIGKILL)` on POSIX), reads back
  partial/complete JSONL evidence regardless of outcome, cleans up.

### Conformance engine (additive)

`conformance/engine.py`'s `build_findings()` gained `runtime_evidence:
tuple[Evidence, ...] = ()` and `execution_failures: tuple[str, ...] = ()`,
mirroring Batch 2's `static_evidence`/`analysis_failures` pattern exactly.
Both bare-`Evidence` runtime fallback sites (`R-D` and `R-S`) now attach
real audit-event detail when available. Re-verified the full pre-existing
suite (189 total afterward) passes unchanged.

### Fixtures (`tests/fixtures/skillshield/`)

`runtime_clean/`, `runtime_undeclared_network/`, `runtime_process_execute/`,
`runtime_timeout/`, `runtime_crash/`, `runtime_no_entrypoint/` — each a
plain, self-contained `.py` skill with a `manifest.json`, no host-framework
dependency, covering every P3 validation scenario from the plan.

### Tests

- `tests/unit/test_skillshield_runtime_monitor.py` — `translate_event`/
  `is_bytecode_cache_event` against the real empirically-confirmed event
  shapes.
- `tests/unit/test_skillshield_execution_result.py` — `ExecutionResult`
  construction/validation.
- `tests/integration/test_skillshield_controlled_execution.py` — all six
  plan scenarios end-to-end through `ingest()` → `execute()`, including an
  explicit "no orphaned Python process after timeout" check.
- `tests/integration/test_skillshield_runtime_to_findings.py` — real
  `execute()` output fed into `build_findings()`, confirming real-evidence
  `UNDECLARED_CAPABILITY` (`HIGH`, runtime-confirmed) and
  `EXECUTION_FAILURE` findings.

### Docs

- `docs/conformance-rules.md` §9 — audit-event mapping table, the
  import-noise-filtering design (the batch's most consequential fix — see
  below), timeout/termination behavior.
- `SECURITY_LIMITATIONS.md` (new, repo root) — guarantee-by-guarantee
  honesty statement: process isolation, filesystem, network, environment
  variables, credentials, child processes, resource usage, timeout,
  termination. States plainly this is "a restricted subprocess with an
  audit-hook observer, not a secure sandbox."
- `DECISIONS.md` — appended 5 implementation-level judgment calls under
  the existing `## P3 (Batch 3)` section.

## The most important finding of this batch

Before any noise filtering, **every** executed skill showed
`filesystem.read`/`filesystem.write` as runtime-observed purely from
Python's own import machinery (reading the entrypoint's source, reading
and writing `.pyc` bytecode caches for it and every stdlib module it
imports) — confirmed by direct observation during manual verification
before the automated test suite was written. Left unfixed, this would
have produced a false `UNDECLARED_CAPABILITY` finding on almost every
real-world skill regardless of what its own code does, undermining the
entire premise of runtime observation. Fixed in two layers (`-B` plus
`is_bytecode_cache_event` plus entry-file self-read exclusion by absolute
path) — see `docs/conformance-rules.md` §9.3 and `DECISIONS.md`.

## Validation results

```text
.venv/Scripts/python.exe -m ruff check .
All checks passed!

.venv/Scripts/python.exe -m pytest -q
........................................................................ [ 38%]
........................................................................ [ 76%]
.............................................                            [100%]
189 passed in 5.63s
```

189 passed = 163 pre-existing (65 `agentic_conformance` + 98 SkillShield
Batch 1/2) + 26 new Batch 3 tests.

Manually confirmed via `tasklist` (Windows) that the Python process count
after a timeout-exercising run returns to its pre-run baseline — no
orphaned harness process survives — in addition to the automated
regression test that performs the same check inline.

## Known limitations (intentional / honest, not oversights)

- No CPU/memory limiting — wall-clock timeout only (`SECURITY_LIMITATIONS.md`).
- `os.environ.get`/`os.getenv` reads produce no runtime evidence at all —
  confirmed empirically, not a bug in `monitor.py`.
- The audit hook can be bypassed by a sufficiently adversarial skill using
  a compiled extension module or direct syscalls that don't go through an
  audited CPython API.
- Process-tree termination on timeout is best-effort (`taskkill /F /T` /
  `killpg(SIGKILL)`); a descendant that detaches from the process group
  could in principle survive.
- Real policy loading/application (P4) does not exist yet — `process_relevant`
  fixture only demonstrates that `process.execute` is observable; it is not
  run against a deny policy in this batch.
- No CLI or UI yet (P5/P6).
