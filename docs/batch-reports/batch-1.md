# Batch 1 Report — P0 (Core Foundation) + P1 (Generic Skill Ingestion)

## Scope implemented

Per `docs/product-plan.md` §4-5 and `docs/product-spec.md` §9-§19 (P0) and
§10 (P1).

### P0 — Core Foundation

New package `src/skillshield/`:

- `core/models/capability.py` — reuses `agentic_conformance`'s open
  capability registry; registers `filesystem.read`.
- `core/models/artifact.py` — `SkillArtifact`, `ArtifactInputType`.
- `core/models/skill.py` — `Skill`, `Declaration`, `DeclaredCapability`,
  `DeclarationProblem`.
- `core/models/evidence.py` — `Evidence`, `EvidenceSource`.
- `core/models/finding.py` — `Finding`, `FindingType`, `Severity`,
  `PolicyInfo`, `severity_rank`.
- `core/models/policy.py` — `SecurityPolicy`.
- `core/models/assessment.py` — `Assessment`, `CapabilitySummary`,
  `Recommendation`.
- `core/models/__init__.py` — re-exports all of the above.
- `conformance/correlation.py` — the five D/S/R/P set relationships (S-D,
  R-D, S-R, R-S, R-P).
- `conformance/severity.py` — deterministic severity table.
- `conformance/engine.py` — `build_findings()`: correlation + evidence +
  severity → `Finding` tuple.
- `conformance/assessment.py` — `recommend()`: findings → `Recommendation`
  by max severity.
- `conformance/__init__.py` — re-exports `build_findings`, `recommend`.

### P1 — Generic Skill Ingestion

- `ingestion/errors.py` — `IngestionError` hierarchy (fatal:
  `PathTraversalError`, `MalformedArchiveError`, `UnsupportedArchiveError`,
  `InvalidSkillStructureError`; non-fatal, caught internally:
  `MissingDeclarationError`, `MalformedDeclarationError`).
- `ingestion/declaration.py` — `load_declaration()`: parses `manifest.json`,
  never raises out of the module.
- `ingestion/directory.py` — `ingest_directory()`: file inventory, content
  digest, source-file discovery, declaration resolution, canonical
  `Skill`/`SkillArtifact` construction.
- `ingestion/archive.py` — `ingest_archive()`: ZIP safety checks (traversal,
  symlinks, size/member caps, corruption) then delegates to
  `ingest_directory()` on a temp extraction dir.
- `ingestion/__init__.py` — `ingest()` dispatcher (directory vs. ZIP vs.
  unsupported/missing input).

### Packaging

- `pyproject.toml` — added `"src/skillshield"` to
  `[tool.hatch.build.targets.wheel].packages`. No new runtime dependency.
  Ran `uv sync`; confirmed `import skillshield` and the ingestion/conformance
  entry points work from the venv.

### Tests (all new; pre-existing `agentic_conformance` tests untouched)

- `tests/unit/test_skillshield_models.py`
- `tests/unit/test_skillshield_correlation.py`
- `tests/unit/test_skillshield_severity.py`
- `tests/unit/test_skillshield_engine.py`
- `tests/unit/test_skillshield_assessment.py`
- `tests/unit/test_skillshield_declaration.py`
- `tests/unit/test_skillshield_ingestion_directory.py`
- `tests/unit/test_skillshield_ingestion_archive.py`
- `tests/integration/test_skillshield_dir_zip_equivalence.py`
- `tests/integration/test_skillshield_ingestion_security.py`
- `tests/fixtures/skillshield/sample_skill/` (`manifest.json` + `skill.py`)
  — the first-party "clean skill" fixture; will be reused and extended by
  later batches.

### Docs

- `docs/conformance-rules.md` (new) — capability vocabulary, the five
  correlations, the severity table, the findings→recommendation mapping,
  the declaration format, and the archive safety limits.
- `DECISIONS.md` — appended implementation-time decisions under the
  existing `## P0/P1 (Batch 1)` section (archive size/member limits,
  declaration-error handling, unsupported-capability handling,
  `input_type` propagation).

## Validation results

```text
.venv/Scripts/python.exe -m ruff check .
All checks passed!

.venv/Scripts/python.exe -m pytest -q
........................................................................ [ 53%]
...............................................................          [100%]
135 passed in 0.58s
```

135 passed = 65 pre-existing `agentic_conformance` tests (untouched) + 70
new SkillShield tests.

```text
.venv/Scripts/python.exe -c "import skillshield; from skillshield.ingestion import ingest; print('ok')"
ok
```

## Known limitations (intentional at this stage)

- D/S/R/P are exercised only via synthetic/hand-built capability sets in
  this batch's conformance tests — there is no real static analyzer (P2),
  no controlled execution/runtime monitor (P3), and no policy *file*
  loading (a `SecurityPolicy` is constructed directly in tests; loading one
  from disk is P4 territory). This is intentional per the plan's batch
  sequencing ("P0 ... Done When: the core can represent and compare
  capability evidence without any application-specific dependency").
- `Skill.declaration.entrypoint` is parsed and stored but not yet resolved
  or invoked — that happens in P3.
- No CLI or UI yet (P5/P6).
- Archive ingestion does not scan for zip-bomb-style compression ratios
  beyond the flat uncompressed-size/member-count caps (e.g. a highly
  compressible single large member is still bounded by the 50 MB
  uncompressed cap, so this is covered, but no separate compression-ratio
  heuristic was added — considered unnecessary given the flat cap already
  bounds worst-case decompressed size).
