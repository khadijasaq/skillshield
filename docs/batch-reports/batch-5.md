# Batch 5 Report — P5 (End-to-End Application Interface)

## Scope implemented

Per `docs/product-plan.md` §9 and `docs/product-spec.md` §23.

### Application interface

- `src/skillshield/pipeline.py` — `assess(input_path, *, policy_path=None,
  timeout_seconds=10.0) -> Assessment`. Runs the complete pipeline: `ingest()`
  → `analyze()` → `execute()` → `load_policy()` → `build_findings()` →
  `recommend()`, and assembles the final `Assessment` (capability summary,
  findings, limitations, reproducibility metadata). Pure glue — no
  conformance/analysis/execution logic duplicated here. A fatal
  `IngestionError` or `PolicyLoadError` propagates unchanged; see
  `DECISIONS.md` ("P5 (Batch 5) implementation notes") for why.

### CLI

- `src/skillshield/cli.py` — `skillshield scan <path>` (argparse,
  `scan` subcommand only, matching the plan's literal command shape).
  Options: `--policy PATH`, `--timeout SECONDS`, `--json`. Human-readable
  report shows: recommendation, D/S/R/P capability summary (counts and
  names), each finding (severity/type/capability/explanation/policy
  info/evidence with real detail), and limitations. `--json` renders the
  same `Assessment` as dependency-free JSON (`_assessment_to_jsonable`).
  Exit codes: `0` completed assessment (any recommendation), `2` ingestion
  failure, `3` policy-load failure.

### Packaging

- `pyproject.toml` — added `[project.scripts]` → `skillshield =
  "skillshield.cli:main"`. Ran `uv sync`; confirmed `.venv/Scripts/skillshield.exe`
  exists and runs correctly (see example output below).

### Tests (all new; nothing pre-existing touched)

- `tests/unit/test_skillshield_pipeline.py` (10 tests) — glue-level:
  clean/policy-violation/mismatch fixtures produce the right `Assessment`;
  nonexistent path and malformed ZIP raise `IngestionError`; bad policy
  file raises `PolicyLoadError`; timeout/crash fixtures produce the
  expected limitation/finding; capability fields are frozensets; the
  `Assessment` round-trips through the CLI's JSON helper.
- `tests/integration/test_skillshield_cli.py` (6 tests) — real subprocess
  invocations of `python -m skillshield.cli scan ...`: clean skill (exit 0,
  "NO ISSUES FOUND"), policy violation (exit 0, "DO NOT USE" + capability
  name in stdout), `--json` output parses and has the right fields,
  nonexistent path (nonzero exit, clear stderr, empty stdout), a ZIP built
  on the fly from an existing fixture produces an identical recommendation
  and findings to the directory form, and the installed `skillshield`
  console script itself (not just `python -m`) works.

### Docs

- `DECISIONS.md` — new `### P5 (Batch 5) implementation notes` subsection
  under the pre-existing `## P5/P6 (Batches 5-6)` heading: plain function
  instead of a `SkillShieldPipeline` class (and why that's a deliberate,
  documented deviation from the originally-sketched name), exception
  propagation choice, CLI exit-code convention, `--json` serialization
  approach.

## Validation results

```text
.venv/Scripts/python.exe -m ruff check .
All checks passed!

.venv/Scripts/python.exe -m pytest -q
........................................................................ [ 32%]
........................................................................ [ 65%]
........................................................................ [ 98%]
....                                                                     [100%]
220 passed in 14.34s
```

220 passed = 204 pre-existing + 16 new (10 pipeline unit + 6 CLI integration).

### Real CLI output (clean fixture)

```text
$ .venv/Scripts/skillshield.exe scan tests/fixtures/skillshield/clean_pipeline
============================================================
SKILLSHIELD SECURITY ASSESSMENT
============================================================
Skill: Clean Pipeline Skill (v1.0.0, id=clean-pipeline)

RECOMMENDATION: NO ISSUES FOUND

Capability summary (D/S/R/P):
  Declared (1): filesystem.read
  Static (1): filesystem.read
  Runtime (1): filesystem.read
  Policy-permitted (2): filesystem.read, task.read

Findings: none

Limitations:
  - Static evidence indicates possible behavior, not proof it occurs. Runtime
    evidence reflects only this one controlled execution; its absence does
    not prove a capability can never occur.

(policy=default, artifact_digest=25c1426c..., generated_at=2026-10-07T12:28:05Z)
```

### Real CLI output (policy-violation fixture, with real evidence detail)

```text
$ .venv/Scripts/skillshield.exe scan tests/fixtures/skillshield/runtime_undeclared_network
RECOMMENDATION: DO NOT USE

Findings (2):

  [HIGH] UNDECLARED_CAPABILITY
    Capability: network.egress
    Capability 'network.egress' was not declared. Declared: no. Static: yes. Runtime: yes.
    Evidence:
        - runtime: network.egress [event=socket.connect, resource=('127.0.0.1', 18423)]

  [CRITICAL] POLICY_VIOLATION
    Capability: network.egress
    Capability 'network.egress' was observed at runtime but is denied by policy 'default'.
    Policy: default (denied)
    Evidence:
        - policy: network.egress
```

## Known limitations (intentional at this stage)

- No UI yet — that is Batch 6 / P6.
- `--json`'s shape is whatever `Assessment`'s current fields are; it is not
  a versioned/frozen schema document.
- The CLI has exactly one subcommand (`scan`), per the plan's literal
  command shape — nothing speculative (no `list`, `config`, etc.) was added.
- `skillshield scan` always runs the full pipeline synchronously; a very
  large skill or a long `--timeout` will block the terminal for that long,
  which is the accepted trade-off documented in `DECISIONS.md` for the
  synchronous application-interface design.
