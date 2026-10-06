# Implementation Plan: Downloaded Skill Assessment (SkillShield)

This document defines **HOW** the second milestone described in
`docs/downloaded-skill-assessment-spec.md` is implemented.

`docs/downloaded-skill-assessment-spec.md` remains the source of truth for
**WHAT** is required, exactly as `docs/spec.md` remains the source of truth
for the first milestone. `docs/spec.md` and `docs/plan.md` remain in force
unchanged; nothing in this plan supersedes them. If this plan and either
specification conflict, the specification wins and this plan must be
corrected — not the other way around. If implementation ever reveals a
genuine contradiction in either specification, implementation must STOP and
report it; specifications are not silently rewritten to make implementation
easier.

All implementation must remain within the scope of
`docs/downloaded-skill-assessment-spec.md`. No phase may introduce behavior
outside its finalized requirements.

Target branch (not created by Claude): `feat/downloaded-skill-assessment`.

---

## 1. Plan Overview

The second milestone extends the first milestone's architecture to assess a
Downloaded Skill before a user trusts it:

```text
Downloaded Skill
      ↓
Adapter
      ↓
Canonical Models
      ↓
Evidence / Runtime Events
      ↓
Conformance Core
      ↓
Policy Evaluation
      ↓
Findings / Assessment
      ↓
Report / User Decision
```

The implementation follows this sequence:

1. Downloaded skill adapter (one real skill, one real testbed app)
2. Static analysis foundation (one deterministic detector)
3. Controlled execution integration contract
4. Runtime monitoring (sandbox observations → canonical `SecurityEvent`)
5. Declaration/static/runtime (`D`/`S`/`R`) correlation
6. Policy and severity
7. `Finding` / `Assessment` models and a minimal report
8. End-to-end evaluation against the testbed

The architectural boundary from the first milestone is unchanged and
governs every phase below:

```text
Adapter              = translation + integration
Static Analyzer      = inspection → evidence, outside core/
Controlled Execution = isolation + lifecycle, outside core/
Runtime Monitor       = observation → canonical SecurityEvent, outside core/
Core                  = canonical representation + conformance evaluation
                        + deterministic correlation/policy/severity logic
```

`core/` never contains logic specific to
`vuln-agentic-skills-app`, to a sandbox technology, or to a static-analysis
engine. Those always sit in adapters or in new, equally product-independent
modules alongside `core/` and `adapters/` (never conditionally branched
*inside* `core/`).

---

## 2. Current Starting Point

Already in place (first milestone, complete, frozen except where a phase
below explicitly extends it additively):

```text
src/agentic_conformance/core/models/            (Skill, Capability, SecurityEvent, Evidence, Decision)
src/agentic_conformance/core/interfaces/         (ConformanceAPI, ProductAdapter)
src/agentic_conformance/core/conformance/         (structural.py, rules.py, engine.py)
src/agentic_conformance/adapters/reference_app/   (adapter.py, mapping.py)
schemas/                                          (skill, security_event, evidence, decision)
tests/unit/, tests/integration/                    (65 tests, all passing)
examples/reference_app_walkthrough.py
docs/spec.md, docs/plan.md                          (first milestone, frozen)
docs/downloaded-skill-assessment-spec.md             (second milestone spec, frozen)
CLAUDE.md                                            (frozen)
```

Verified before writing this plan: `uv run pytest --collect-only -q` reports
**65 tests collected**; no file or directory referencing
`vuln-agentic-skills-app` exists anywhere in this repository yet.

Not yet implemented (this plan's subject):

```text
Any adapter for vuln-agentic-skills-app
Static analyzer
Controlled execution / sandbox integration
Runtime monitor
S/R/D correlation functions beyond the existing R⊆D, R⊆P, R⊆D∩P rules
PolicyRule / effect extension
Finding model + schema
Assessment model + schema
Severity classification
End-to-end testbed demonstration for the six required cases
```

---

## 3. Directory-Placement Decisions (made once, here, for the whole milestone)

Per `docs/downloaded-skill-assessment-spec.md` §16, anticipated additions
are an implementation-plan decision. The following decisions are made now,
so every phase below reuses them instead of re-deciding ad hoc:

| New component | Location | Reason |
|---|---|---|
| Adapter for `vuln-agentic-skills-app` | `src/agentic_conformance/adapters/vuln_agentic_skills_app/` | Mirrors the existing `adapters/reference_app/` convention exactly: one directory per adapted product, named for what it adapts. No new top-level directory needed — `adapters/` already exists for exactly this purpose. |
| Static analyzer | `src/agentic_conformance/analysis/static/` | Not an adapter (it does not translate a specific product's native format — it inspects source text generically) and not core conformance logic (it does not evaluate rules, it produces evidence). A new second-level package under `src/agentic_conformance/`, sibling to `core/` and `adapters/`, is justified because this component is genuinely a third kind of thing the first milestone never needed: a product-independent *evidence producer* that is not an adapter. One module (`static/`) is created now; a sibling `analysis/runtime/` is reserved by this same package in Phase 4 rather than inventing a fourth top-level name later. |
| Controlled execution / sandbox | `src/agentic_conformance/execution/` | Sibling to `core/`, `adapters/`, `analysis/`. Isolation/process-lifecycle concerns are categorically different from both "translate a product's data" (adapter) and "inspect source without running it" (analysis), so folding it into either would blur a boundary the specification explicitly keeps separate (§6, §12 of the spec). This is the **only** new top-level-under-`src/` package besides `analysis/` that this milestone introduces — not `sandbox/` at the repository root, which would needlessly compete with `src/` for top-level visibility. |
| Runtime monitor | `src/agentic_conformance/analysis/runtime/` | Grouped with the static analyzer under `analysis/` because both are "observation → canonical Evidence/SecurityEvent" producers; only the observation channel differs (source text vs. sandbox output). This avoids a fourth sibling package (`monitoring/`) for a component that is conceptually the same *kind* of thing as the static analyzer. |
| `Finding`, `Assessment` models | `src/agentic_conformance/core/models/finding.py`, `.../assessment.py` | These are canonical models exactly like `Skill`/`Decision`/`Evidence` — they belong where those already live, per `docs/spec.md` §19's mapping of `core/models/` to "canonical ... models." No new directory. |
| `PolicyRule` / severity logic | `src/agentic_conformance/core/conformance/policy.py`, `.../severity.py` | Deterministic, product-independent evaluation logic, exactly like `rules.py` and `structural.py` already in `core/conformance/`. No new directory — a `policies/` top-level package would duplicate what `core/conformance/` already is. |
| New schemas | `schemas/finding.schema.json`, `schemas/assessment.schema.json` | Same flat `schemas/` directory as the first milestone; no reorganization. |
| Minimal report rendering | `examples/skillshield_assessment_walkthrough.py` (function used by it lives in `core/` as plain data formatting, not a new package) | Mirrors `examples/reference_app_walkthrough.py`. No `reports/` package: per the spec (§10.6), report *rendering* is explicitly deferred/unfrozen, so only a minimal, test-covered formatting function is needed, not infrastructure. |

Directories explicitly **not** created by this milestone, per
`docs/downloaded-skill-assessment-spec.md` §16 and the instructions governing
this plan: `frontend/`, `api/`, `services/`, `sandbox/` (top-level),
`analyzers/` (top-level), `monitoring/` (top-level), `policies/` (top-level),
`reports/`, `benchmark/`.

---

## 4. Phase 1 — Downloaded Skill Integration

### Objective

Register one real skill from `github.com/khadijasaq/vuln-agentic-skills-app`
as a canonical `Skill`, through a dedicated adapter, using the existing
`register_skill` operation unchanged.

### Why this phase comes here

Every later phase (static analysis, execution, monitoring, correlation,
assessment) operates on a registered `Skill`. Nothing can be demonstrated
end-to-end until one real skill exists in canonical form. This phase has no
dependency on any other new component — it only depends on first-milestone
code that is already complete (`Skill`, `Declaration`, `Capability`,
`ConformanceAPI.register_skill`, `ProductAdapter`).

### Scope

1. **Inspect the actual application** (read-only; the first concrete step
   of this phase, performed before any code is written): clone or fetch
   `vuln-agentic-skills-app`, and determine its real manifest/declaration
   format, source-file layout, runtime entry point, and whatever event or
   log format (if any) it already produces for its own actions. This plan
   deliberately does not assume a manifest filename, directory layout, or
   event format — those are discovered during this step, not guessed here.
2. **Identify the skill declaration format** actually used (e.g. a JSON/
   YAML manifest, a Python decorator, a config block — whatever is found).
3. **Identify source files** belonging to a single chosen skill within the
   app, to also serve as the fixed Phase 2/3/4/8 target skill throughout
   this milestone (one skill, reused across phases, per
   `docs/downloaded-skill-assessment-spec.md` §11 step 1).
4. **Identify the runtime entry point** for that skill (how it is actually
   invoked/run).
5. **Identify any existing runtime activity/event source** the app already
   emits (logs, hooks, callbacks) that Phase 4's monitor may eventually be
   able to reuse — recorded as a finding for Phase 4, not acted on yet.
6. **Design the adapter mapping**: native declaration fields → canonical
   `Skill`/`Declaration`/`Capability`, following the existing
   `ReferenceAppAdapter`/`mapping.py` pattern exactly (a small
   `dict`-based native-name → canonical-identifier table; extend the
   capability vocabulary via `register_capability` only for genuinely new
   capability kinds the app's declarations use that
   `task.read`/`network.egress`/`process.execute`/`filesystem.write`/
   `credential.read` do not already cover).
7. **Produce a canonical `Skill`** for the chosen skill via
   `translate_skill` + `register_skill`.
8. **Register it through the existing API** — no change to
   `ConformanceAPI` or `ProductAdapter` is needed or permitted in this
   phase.
9. **Test with one real skill**: a unit test for the translation logic and
   an integration test that registration + a trivial `evaluate()` call
   succeeds end-to-end for that one skill, mirroring
   `tests/unit/test_reference_adapter.py` and
   `tests/integration/test_conformance_engine.py`.

### Files to create

```text
src/agentic_conformance/adapters/vuln_agentic_skills_app/__init__.py
src/agentic_conformance/adapters/vuln_agentic_skills_app/adapter.py
src/agentic_conformance/adapters/vuln_agentic_skills_app/mapping.py
tests/unit/test_vuln_app_adapter.py
tests/integration/test_vuln_app_registration.py
```

Exact adapter/mapping file split and internal function names mirror
`adapters/reference_app/` precisely; if the real application's structure
makes a single `adapter.py` sufficient (e.g. no non-trivial capability
mapping table is needed), `mapping.py` may be reduced to a few constants
inside `adapter.py` instead of a separate file — a final call made during
this phase's own inspection step (point 1 above), not before.

### Files to modify

None in `core/`. `src/agentic_conformance/core/models/capability.py` is
touched only at **runtime** via its existing public
`register_capability` function (called from the new adapter module) — its
source code is not edited.

### Files that must NOT be modified

```text
docs/spec.md
docs/plan.md
docs/downloaded-skill-assessment-spec.md
CLAUDE.md
src/agentic_conformance/core/models/*.py        (used, not edited)
src/agentic_conformance/core/interfaces/*.py
src/agentic_conformance/core/conformance/*.py
src/agentic_conformance/adapters/reference_app/*
tests/ (existing files)
schemas/
.github/workflows/ci.yml
.gitignore
pyproject.toml
```

### Inputs

The real on-disk contents of one skill from `vuln-agentic-skills-app`
(manifest/declaration + source files), obtained by cloning/inspecting the
application as part of this phase's own first step.

### Outputs

One canonical `Skill` instance, successfully passed to `register_skill`.

### Interfaces

No new interface. Reuses exactly:

```text
ConformanceAPI.register_skill(skill_profile: Skill) -> None
ProductAdapter.translate_skill(native_skill) -> Skill
ProductAdapter.normalize_capability(native_capability) -> Capability
ProductAdapter.register(native_skill) -> None
```

### Data flow

```text
vuln-agentic-skills-app skill (manifest + source)
        ↓
VulnAgenticSkillsAppAdapter.translate_skill()
        ↓
canonical Skill (+ Declaration + Capability)
        ↓
ConformanceEngine.register_skill()   (existing, unmodified)
```

### Tests

- Unit: `translate_skill` on a captured/fixture copy of the real
  manifest → expected canonical `Skill`; `normalize_capability` on each
  native capability name actually found.
- Integration: `adapter.register(real_native_skill)` then
  `adapter.evaluate(skill_id)` returns a `Decision` without raising
  (even if the decision is a structural `DENY` because no events exist
  yet — the point of this phase is registration, not evaluation
  correctness).

### Acceptance criteria

1. The real application's manifest format for the chosen skill has been
   inspected and documented in code comments/docstrings (not assumed).
2. `register_skill` succeeds for that skill without modification to any
   first-milestone file.
3. Every native capability the chosen skill declares normalizes to a
   canonical `Capability` (extending the vocabulary where genuinely new).
4. New tests pass; all 65 existing tests continue to pass unmodified.
5. `core/` contains zero lines referencing `vuln-agentic-skills-app`.

### Non-goals

Static analysis, controlled execution, runtime monitoring, correlation,
policy, findings, assessment — none of these are implemented in this
phase. Only registration.

### Validation commands

```text
uv run ruff check .
uv run pytest
uv run pytest tests/unit/test_vuln_app_adapter.py tests/integration/test_vuln_app_registration.py -v
```

### Review checkpoint

Stop after Phase 1. Do not begin Phase 2 until reviewed and approved.

---

## 5. Phase 2 — Static Analysis Foundation

### Objective

Implement one minimal, deterministic static analyzer that inspects the
Phase 1 skill's source files and produces at least one real `Evidence`
instance with `source = STATIC`, populating `S` for the first time.

### Why this phase comes here

Depends on Phase 1 only for *which source files* to point the analyzer at
(the chosen skill's files). It does not depend on Phase 3/4 (execution,
monitoring) at all — static analysis never runs the skill. It is sequenced
before execution/monitoring because the spec's Stage 5 correlation (`S-R`,
`R-S`, etc. — Phase 5 of this plan) needs `S` to exist before it is useful,
and because static analysis is lower-risk to build first (it never
executes untrusted code).

### Scope

1. **Static analyzer input**: a list of source file paths belonging to the
   Phase 1 skill (obtained from the adapter, not re-discovered).
2. **Source traversal**: read each file's text; no execution, no dynamic
   import, no `eval`.
3. **Capability detection**: a small, fixed set of deterministic pattern
   detectors — e.g. recognizable import statements (`socket`, `requests`,
   `urllib`, `subprocess`, `os.system`) and literal patterns (`http://`,
   `https://` URL literals; `os.environ`/`getenv` calls). Each detector is
   a pure function: `text -> list[RawMatch]`.
4. **Evidence generation**: each detector match becomes exactly one
   `StaticFinding` (per
   `docs/downloaded-skill-assessment-spec.md` §5.1), then exactly one
   canonical `Evidence` (per §5.3): `source=STATIC`, `skill_id=<the Phase 1
   skill>`, `data={"capability":..., "file":..., "location":...,
   "detector":..., "description":...}`.
5. **Source-location attribution**: `file` is the path relative to the
   skill's source root; `location` is the 1-based line number the match
   was found on.
6. **Normalization into canonical capabilities**: each detector owns a
   fixed native-pattern → canonical-capability-identifier mapping (e.g.
   `subprocess` import → `process.execute`), using `register_capability`
   only if a genuinely new capability is needed (unlikely in this phase —
   the existing vocabulary already covers network/filesystem/process/
   credential).
7. **Integration with the existing Evidence model**: no changes to
   `core/models/evidence.py`; the analyzer only constructs instances of it.
8. **Handling unknown/unrecognized behavior**: code that matches no
   detector produces no `Evidence` and no error — absence of a static
   finding is not itself a finding (consistent with
   `docs/downloaded-skill-assessment-spec.md` §5.1's "at least one concrete
   detector... does not require a complete static-analysis framework").

Explicitly, this phase separates **capability inference**
("this import/pattern implies capability X was likely intended") from
**maliciousness determination** (not attempted anywhere in this phase or
milestone): a detector's output is always phrased as "capability X was
statically inferred," never as "this is dangerous" or "this is malicious."

### Files to create

```text
src/agentic_conformance/analysis/__init__.py
src/agentic_conformance/analysis/static/__init__.py
src/agentic_conformance/analysis/static/detectors.py
src/agentic_conformance/analysis/static/analyzer.py
src/agentic_conformance/analysis/static/evidence.py
tests/unit/test_static_detectors.py
tests/unit/test_static_analyzer.py
tests/integration/test_static_analysis_evidence.py
```

`detectors.py` holds the pure pattern-matching functions;
`analyzer.py` holds the traversal/orchestration (`analyze(source_root) ->
list[StaticFinding]`, per spec §5.1); `evidence.py` holds the
`StaticFinding -> Evidence` conversion (spec §5.3). This three-way split
keeps each module single-purpose per `CLAUDE.md`'s "prefer small, focused
modules" rule.

### Files to modify

None. `register_capability` is called at runtime from `analyzer.py` if
needed; no source files in `core/` are edited.

### Files that must NOT be modified

Same protected list as Phase 1, plus:
`src/agentic_conformance/adapters/vuln_agentic_skills_app/*` (Phase 1's
adapter is consumed, e.g. for file paths, not modified by this phase).

### Inputs

The Phase 1 skill's source file paths (and their text content).

### Outputs

A `list[StaticFinding]` and, derived from it, a `list[Evidence]` with
`source=STATIC`, covering the Phase 1 skill.

### Interfaces

```text
analyze(source_root: Path) -> list[StaticFinding]          # analyzer.py
static_findings_to_evidence(
    skill_id: str, findings: list[StaticFinding]
) -> list[Evidence]                                          # evidence.py
```

`StaticFinding` is a small frozen dataclass per spec §5.1
(`capability`, `file`, `location`, `detector`, `description`), defined in
`analyzer.py` or a shared `types.py` in the same package — not in
`core/models/`, since it is an analyzer-internal intermediate type, not a
canonical model (only the `Evidence` it converts into is canonical).

### Data flow

```text
Skill source files
        ↓
detectors.py  (pure pattern functions)
        ↓
analyzer.py   (traversal + orchestration)
        ↓
list[StaticFinding]
        ↓
evidence.py   (StaticFinding -> Evidence)
        ↓
list[Evidence]  (source=STATIC)   →  fed to Phase 5 correlation
```

### Tests

- Unit: each detector against known-positive and known-negative text
  fixtures (string literals, not real files, for the pure-function tests).
- Unit: `analyze()` against a small fixture directory tree.
- Integration: `analyze()` run against the **real** Phase 1 skill's actual
  source files, asserting at least one `Evidence` with `source=STATIC` is
  produced — this is the "at least one real detector" requirement from the
  spec, exercised against real data, not only fixtures.

### Acceptance criteria

1. At least one concrete detector exists and is unit-tested.
2. Running `analyze()` against the Phase 1 skill's real source produces at
   least one `StaticFinding` and at least one converted `Evidence`
   (`source=STATIC`), i.e. `S` is nonempty for that skill.
3. Every `Evidence.data["capability"]` value is a valid canonical
   capability identifier.
4. No detector executes or imports the analyzed skill's code.
5. All new and existing tests pass.

### Non-goals

A complete/universal static-analysis framework, obfuscation/encoded-content
detection, dependency-graph scanning, taint analysis, any maliciousness
verdict, any LLM-based inference.

### Validation commands

```text
uv run ruff check .
uv run pytest
uv run pytest tests/unit/test_static_detectors.py tests/unit/test_static_analyzer.py tests/integration/test_static_analysis_evidence.py -v
```

### Review checkpoint

Stop after Phase 2. Do not begin Phase 3 until reviewed and approved.

---

## 6. Phase 3 — Controlled Execution / Sandbox Integration Contract

### Objective

Define and implement the minimal `execute(skill, runtime_config) ->
ExecutionHandle` integration contract from
`docs/downloaded-skill-assessment-spec.md` §6.1, with an explicitly
documented, non-production isolation mechanism sufficient to run the Phase
1 skill under observation for Phase 4 to use.

### Why this phase comes here

Depends on Phase 1 (needs a registered skill + its runtime entry point) but
not on Phase 2 (static analysis and execution are independent evidence
sources, per spec §8.1 — nothing about execution depends on static
findings existing first). It must precede Phase 4 because the monitor
observes *this* phase's execution; it must precede Phase 5 because `R`
cannot exist without a completed execution to observe.

### Scope — interface first

```text
execute(skill: Skill, runtime_config: dict) -> ExecutionHandle
```

`ExecutionHandle` exposes exactly what Phase 4 needs: a way to know the
execution has finished, and a way to retrieve whatever raw observation
stream the sandbox collected (format owned by this phase, consumed only by
Phase 4's monitor — never by `core/`).

Per spec §6.2/§12 and this plan's explicit governing instruction, running
an untrusted skill locally with no isolation is **not** acceptable as the
"first implementation." A concrete, justified choice is made for the first
prototype:

> **Sandbox technology selected for this milestone: a dedicated OS-level
> restricted subprocess** (`subprocess.run` with a dedicated unprivileged
> account/working directory, no inherited credentials beyond placeholders
> per spec §6.4, a wall-clock timeout, and — where the host OS supports it
> — process/resource limits such as `resource.setrlimit` on Linux or a
> Windows Job Object). This is **not** a container or VM.
>
> **Why selected:** it requires zero new runtime dependencies (consistent
> with the first milestone's "no new runtime dependencies" discipline) and
> is implementable with the Python standard library alone, while still
> providing a real process boundary (separate OS process, restricted
> filesystem working directory, a hard timeout) — sufficient to exercise
> the full pipeline end-to-end on the one fixed testbed skill (spec §11)
> without requiring a container runtime or VM hypervisor as a new
> environment dependency for this plan's own CI/test execution.
>
> **What it guarantees:** the skill runs as a separate OS process; it
> cannot directly share Python memory/state with the assessment host
> process; it is killed on timeout; its working directory is a disposable
> temporary directory.
>
> **What it does NOT guarantee:** it does **not** prevent filesystem access
> outside the working directory, does **not** prevent network egress,
> does **not** prevent privilege escalation, and does **not** provide the
> isolation guarantees of a container or VM. This must be stated verbatim
> in the module's docstring and in the Phase 3 completion report, per spec
> §12's requirement that an interim/stub implementation's non-isolating
> nature be clearly documented. Per spec §12, this interim sandbox is run
> **only** against the fixed reference testbed skill (§4.4 of the spec),
> never against arbitrary untrusted input, for exactly this reason.
>
> **Why the abstraction remains technology-independent:** `execute()` and
> `ExecutionHandle` do not expose any subprocess-specific detail to Phase 4
> or to `core/` — Phase 4's monitor consumes only the raw-observation
> stream `ExecutionHandle` defines, not subprocess internals, so a future
> milestone can replace the subprocess implementation with a container or
> VM-based one by changing only this module, with zero changes to Phase 4,
> Phase 5, or `core/`.

### Files to create

```text
src/agentic_conformance/execution/__init__.py
src/agentic_conformance/execution/handle.py
src/agentic_conformance/execution/subprocess_sandbox.py
tests/unit/test_execution_handle.py
tests/integration/test_subprocess_sandbox.py
```

### Files to modify

None in `core/`, `adapters/`, or `analysis/`.

### Files that must NOT be modified

Same protected list as Phase 1/2, plus Phase 1 and Phase 2's own new files
(consumed, not edited).

### Inputs

The Phase 1 `Skill` (for its runtime entry point) and a `runtime_config`
dict (environment variables/placeholder credentials per spec §6.4).

### Outputs

An `ExecutionHandle` that, once the process completes, exposes: exit
status, wall-clock duration, and the raw observation stream (initially:
captured stdout/stderr plus a best-effort list of files created/modified
under the working directory, detected by a before/after directory scan —
see Phase 4 for how this becomes `SecurityEvent`s).

### Interfaces

```text
# execution/handle.py
@dataclass(frozen=True)
class ExecutionHandle:
    skill_id: str
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    working_directory: Path
    created_or_modified_files: tuple[Path, ...]

# execution/subprocess_sandbox.py
def execute(skill: Skill, runtime_config: dict, *, timeout_seconds: float = 30.0) -> ExecutionHandle: ...
```

### Data flow

```text
Skill (+ runtime_config)
        ↓
subprocess_sandbox.execute()
        ↓  (restricted subprocess, dedicated temp working dir, timeout)
ExecutionHandle (exit_code, stdout/stderr, file diffs)
        ↓
        → consumed by Phase 4's monitor only
```

### Tests

- Unit: `ExecutionHandle` construction/validation.
- Integration: `execute()` against a small, deliberately harmless fixture
  script (not the real testbed skill yet) verifying timeout enforcement,
  working-directory isolation (files written only inside the temp dir are
  captured), and correct `exit_code` propagation.
- Integration: `execute()` against the real Phase 1 skill, asserting it
  runs to completion (or a documented, expected failure) within the
  timeout.

### Acceptance criteria

1. `execute()` runs the Phase 1 skill in a separate OS process with a
   disposable working directory and enforced timeout.
2. A skill that exceeds the timeout is terminated and reported as such
   (not hung, not silently ignored).
3. The non-isolation caveats above are stated verbatim in
   `subprocess_sandbox.py`'s module docstring.
4. No change to `core/`, `adapters/reference_app/`, or
   `adapters/vuln_agentic_skills_app/` is required or made.
5. All new and existing tests pass.

### Non-goals

Container- or VM-based isolation, resource-limit tuning beyond a basic
timeout, network-egress blocking, multi-tenant/concurrent execution,
credential provisioning beyond placeholders.

### Validation commands

```text
uv run ruff check .
uv run pytest
uv run pytest tests/unit/test_execution_handle.py tests/integration/test_subprocess_sandbox.py -v
```

### Review checkpoint

Stop after Phase 3. Do not begin Phase 4 until reviewed and approved.

---

## 7. Phase 4 — Runtime Monitoring

### Objective

Convert the Phase 3 `ExecutionHandle`'s raw observations into canonical
`SecurityEvent` instances (reusing the existing model exactly), populating
`R` for the Phase 1 skill for the first time.

### Why this phase comes here

Strictly depends on Phase 3 (there is nothing to monitor without a
completed execution) and on Phase 1 (`skill_id`/`context`). Independent of
Phase 2 (static analysis never feeds the monitor).

### Scope

Coverage is explicitly limited to what the Phase 3 subprocess sandbox can
actually observe in this milestone (per spec §6.3's "represent observations
in each category... not that every category has a working detector on day
one"):

1. **Filesystem**: `created_or_modified_files` from `ExecutionHandle` →
   one `filesystem.write` event per file. (`filesystem.read` is registered
   as a new canonical capability via `register_capability`, per spec §7.1,
   but is **not** populated in this phase — the subprocess sandbox has no
   read-tracking mechanism without additional OS-level tracing, which is
   out of scope here.)
2. **Network**: not observed in this phase (the subprocess sandbox
   provides no network interception) — explicitly deferred; the monitor's
   interface supports it (see Interfaces below) so a future sandbox
   upgrade can populate it without an interface change.
3. **Process execution**: if the skill's own stdout/stderr or file-diff
   evidence indicates it spawned a subprocess of its own (best-effort,
   deterministic string/pattern check on captured output — not a
   guarantee), one `process.execute` event.
4. **Credential/environment access**: not directly observable from
   `ExecutionHandle` alone in this phase; deferred alongside network (same
   reasoning).
5. **Tool invocation / agent actions**: only if the testbed skill's own
   output format makes this legible deterministically (discovered during
   Phase 1's inspection step) — otherwise explicitly out of scope for this
   phase, consistent with spec §6.3 not requiring full category coverage
   on day one.

This phase is intentionally honest about partial coverage: it implements
real events for filesystem writes (and process execution when visible),
and documents network/credential/tool-call monitoring as **not yet
implemented**, rather than fabricating events to appear complete.

### Files to create

```text
src/agentic_conformance/analysis/runtime/__init__.py
src/agentic_conformance/analysis/runtime/monitor.py
tests/unit/test_runtime_monitor.py
tests/integration/test_runtime_monitor_events.py
```

### Files to modify

None in `core/`. `register_capability` is invoked at runtime from
`monitor.py` for `filesystem.read` (reserved for future use, per spec
§7.1), not edited into `core/models/capability.py`.

### Files that must NOT be modified

Same protected list as prior phases, plus Phase 3's `execution/*` (consumed
via `ExecutionHandle`, not modified).

### Inputs

One completed `ExecutionHandle` (from Phase 3) for the Phase 1 skill.

### Outputs

A `list[SecurityEvent]`, each with `context={"skill_id": ...}` consistent
with the existing reference adapter's convention (spec §7.2), fed through
the existing, unmodified `emit_event` operation.

### Interfaces

```text
def observations_to_events(handle: ExecutionHandle) -> list[SecurityEvent]: ...
```

No new canonical model. Reuses `SecurityEvent`, `Actor`, `Action`, `Target`
exactly as defined in `core/models/security_event.py`.

### Data flow

```text
ExecutionHandle (Phase 3)
        ↓
monitor.observations_to_events()
        ↓
list[SecurityEvent]
        ↓
ConformanceEngine.emit_event()   (existing, unmodified, called once per event)
```

### Tests

- Unit: `observations_to_events()` against a hand-constructed
  `ExecutionHandle` fixture (known file diffs, known stdout) → expected
  `SecurityEvent`s.
- Integration: run Phase 3's `execute()` on the real Phase 1 skill, then
  `observations_to_events()` on the result, then `emit_event()` for each,
  asserting the engine's internal event list for that skill is nonempty
  (`R` is nonempty) — the first real population of `R` in this milestone.

### Acceptance criteria

1. At least one real `SecurityEvent` is produced and successfully emitted
   for the Phase 1 skill via the unmodified `emit_event` operation.
2. Every produced event validates against the existing
   `validate_security_event` structural check with no changes to that
   function.
3. Coverage gaps (network, credential, tool-call) are explicitly documented
   in `monitor.py`'s module docstring as deferred, not silently absent.
4. All new and existing tests pass.

### Non-goals

A second event model, full category coverage (§6.3), real-time/streaming
monitoring, any sandbox technology beyond what Phase 3 selected.

### Validation commands

```text
uv run ruff check .
uv run pytest
uv run pytest tests/unit/test_runtime_monitor.py tests/integration/test_runtime_monitor_events.py -v
```

### Review checkpoint

Stop after Phase 4. Do not begin Phase 5 until reviewed and approved.

---

## 8. Phase 5 — Declaration / Static / Runtime Correlation

### Objective

Implement and explicitly test **every** comparison relationship required by
`docs/downloaded-skill-assessment-spec.md` §8.3 — reusing existing
`core/conformance/rules.py` helpers and ordinary set operations wherever a
comparison is already directly supported, and adding new pure functions
only where genuinely necessary — and wire `UNDECLARED_CAPABILITY` /
`STATIC_RUNTIME_MISMATCH` to **real, mandatory** evidence from `D` (Phase
1), `S` (Phase 2), and `R` (Phase 4) for a real skill from
`vuln-agentic-skills-app`.

### Why this phase comes here

Strictly depends on Phase 1 (`D`), Phase 2 (`S`), and Phase 4 (`R`) all
existing for the same skill. This is the first phase where all three
evidence sources are combined — it cannot start earlier.

### Scope

1. **Explicit coverage of every required comparison.** Spec §8.3 refers to
   these collectively as the six comparison relationships/categories
   (`S-D`, `R-D`, `R-S`, `S-R`, `R∩D`, `R∩P`), with `S ⊆ D` given alongside
   them in the same section's rule set. This plan preserves that
   terminology rather than inventing a new taxonomy, and requires that
   **all seven of the following be implemented or represented, and
   explicitly tested** — not only the newly introduced helper functions:

```text
1. S ⊆ D   static_within_declared(declared, static) -> bool         [NEW]
2. S - D   statically_undeclared_capabilities(declared, static)      [NEW]
3. R - D   existing rules.undeclared_capabilities(declared, observed) [REUSED]
4. R - S   runtime_not_statically_identified(static, observed)        [NEW]
5. S - R   statically_identified_not_observed(static, observed)        [NEW]
6. R ∩ D   ordinary set intersection: observed & declared                [REUSED]
7. R ∩ P   ordinary set intersection: observed & policy                  [REUSED]
```

   > No redundant helper is required for a comparison already directly
   > supported by existing conformance rules or ordinary set operations,
   > but the comparison itself must still be explicitly tested.

   Only four new pure functions are added to `core/conformance/` (a new
   module, not editing `rules.py`'s existing functions): `S ⊆ D`, `S - D`,
   `R - S`, `S - R`. `R - D` is not reimplemented — the existing
   `rules.undeclared_capabilities` is reused directly by `correlate()`
   (see Interfaces below). `R ∩ D` and `R ∩ P` are not given named
   functions — they are ordinary Python set intersections, computed
   inline where needed (in `correlate()` and in its tests) and never
   duplicated as wrapper functions merely to have a name for them.
2. Add the `Finding`-generation logic that maps each nonempty comparison to
   a `ReasonCode` per spec §9.1's table — implemented here as a pure
   function returning `Finding` *data* (dataclass instances), with the
   `Finding` canonical model itself introduced in Phase 7 (kept together
   with `Assessment` since they are always constructed together — see
   Phase 7's rationale). For this phase, findings are represented as plain
   tuples/dicts internally and converted to the canonical `Finding` model
   only once Phase 7 defines it — **or**, to avoid a throwaway
   intermediate type, `Finding` is pulled forward into this phase instead
   of Phase 7 (see decision below).

   **Decision:** `Finding` is implemented in **this** phase
   (`core/models/finding.py`), not deferred to Phase 7, because Phase 5's
   own acceptance criteria (spec §15 item 6: "a `STATIC_RUNTIME_MISMATCH`
   Finding can be produced and correctly attributed to its originating
   Evidence") explicitly require the `Finding` model to exist here. Phase
   7 then only adds `Assessment`, which aggregates `Finding`s Phase 5
   already produces. This is a refinement of the phase numbering in
   §21/§5 of the planning brief, made because Phase 5's own acceptance
   criteria cannot be met without it — not a scope merge.
3. Every `Finding` carries `evidence_refs` (per spec §10.4) pointing to the
   specific `Evidence`/`SecurityEvent` instances behind it, so Finding →
   Evidence → file+location (static) or event+timestamp (runtime) is
   always traceable (spec §9.2).

### Files to create

```text
src/agentic_conformance/core/models/finding.py
src/agentic_conformance/core/conformance/correlation.py
schemas/finding.schema.json
tests/unit/test_models_finding.py
tests/unit/test_conformance_correlation.py
tests/integration/test_correlation_real_skill.py
```

### Files to modify

None — `rules.py`, `structural.py`, `engine.py` are not edited in this
phase (the engine is extended in Phase 6, once policy/severity also need
wiring in; doing it once in Phase 6 avoids touching `engine.py` twice).
`core/models/__init__.py` is modified only to export `Finding` (an additive
`__all__` entry, consistent with how `Decision`/`Evidence` are already
exported).

### Files that must NOT be modified

Same protected list as prior phases, plus
`core/conformance/rules.py`, `core/conformance/structural.py` (used, not
edited — Phase 5 adds a sibling module instead of changing these).

### Inputs

`D` (from the Phase 1 `Skill.declaration`), `S` (from Phase 2's
`Evidence` with `source=STATIC`), `R` (from Phase 4's emitted
`SecurityEvent`s) — all for the same Phase 1 skill.

### Outputs

A `list[Finding]` for that skill, each with a `reason_code`,
`capabilities`, `evidence_refs`, and `description`.

### Interfaces

```text
# core/conformance/correlation.py  (new functions — only where genuinely necessary)
def static_within_declared(declared: set[str], static: set[str]) -> bool: ...          # S ⊆ D
def statically_undeclared_capabilities(declared: set[str], static: set[str]) -> set[str]: ...  # S - D
def runtime_not_statically_identified(static: set[str], observed: set[str]) -> set[str]: ...    # R - S
def statically_identified_not_observed(static: set[str], observed: set[str]) -> set[str]: ...     # S - R

def correlate(
    skill: Skill, static_evidence: list[Evidence], events: list[SecurityEvent]
) -> list[Finding]:
    """Computes all seven comparisons internally — R-D via the existing
    rules.undeclared_capabilities(), R∩D/R∩P via plain set intersection,
    the remaining four via the new functions above — and returns the
    resulting Findings (R∩D/R∩P do not themselves produce Findings; they
    are exercised directly in tests, per the note in Scope above)."""
```

### Data flow

```text
D (Skill.declaration)   S (Evidence, STATIC)   R (SecurityEvent list)
        └───────────────────┼───────────────────┘
                            ▼
                  correlation.correlate()
                            ▼
                      list[Finding]
                            ▼
              → consumed by Phase 6 (policy) and Phase 7 (Assessment)
```

### Tests

This milestone distinguishes two kinds of test, consistently with the
evaluation philosophy established across both the specification and this
plan — they are not substitutes for one another:

**Deterministic synthetic/unit tests** (allowed and required for edge
cases, isolation, and repeatability):

- Unit: each of the four new pure set functions (`S ⊆ D`, `S - D`,
  `R - S`, `S - R`) against hand-constructed sets covering
  empty/overlapping/disjoint cases.
- Unit: the reused `R - D` path (existing `rules.undeclared_capabilities`)
  and the `R ∩ D` / `R ∩ P` plain-set-intersection expressions, each
  exercised with a dedicated assertion in `test_conformance_correlation.py`
  against hand-constructed sets — so all seven comparisons in Scope item 1
  have explicit test coverage, not only the four newly written functions.
- Unit: `correlate()` against hand-constructed `D`/`S`/`R` fixtures,
  asserting the exact expected `Finding`s (reason codes + capabilities),
  including at least one fixture that produces `UNDECLARED_CAPABILITY` and
  one that produces `STATIC_RUNTIME_MISMATCH`.

**Real testbed evidence** (mandatory — must demonstrate actual evidence
flowing through the real Phase 1 → Phase 2 → Phase 4 pipeline; must not be
satisfiable merely because a chosen skill happens to produce no mismatch):

- Integration: `correlate()` against a real skill's actual `D` (Phase 1),
  `S` (Phase 2), and `R` (Phase 4) must assert a **non-empty** result for
  at least one of the seven comparisons, and must assert that at least one
  `UNDECLARED_CAPABILITY` Finding and at least one
  `STATIC_RUNTIME_MISMATCH` Finding are produced with correct
  `evidence_refs` pointing back to the real `Evidence`/`SecurityEvent`
  instances that produced them. If the Phase 1 skill does not naturally
  produce one or both of these findings, Phase 5 must select another real
  skill from `vuln-agentic-skills-app` (or a second legitimate scenario
  already supported by that application) that does — it must not weaken
  this assertion to an "empty findings list is also acceptable" branch,
  and must not fabricate or manufacture a fake result to satisfy it.

### Acceptance criteria

1. All seven comparisons listed in Scope item 1 are implemented or
   represented, and each has explicit test coverage (spec §15 item 5) —
   the four new functions via dedicated unit tests, and the three reused
   relationships (`R-D`, `R∩D`, `R∩P`) via dedicated assertions against the
   existing helper or plain set operations. Testing only the four newly
   added functions does not satisfy this criterion.
2. `correlate()` produces correctly attributed `UNDECLARED_CAPABILITY` and
   `STATIC_RUNTIME_MISMATCH` findings against fixture data, **and** against
   real data from an actual skill in `vuln-agentic-skills-app` flowing
   through the real Phase 1 → Phase 2 → Phase 4 pipeline (spec §15 item 6).
   This is mandatory, not best-effort: if the originally selected real
   skill does not produce one of these findings, a different real skill or
   real scenario from the same testbed must be used instead.
3. No `Finding` ever claims maliciousness — only the standardized reason
   code + capability + evidence reference (spec §9.3).
4. `schemas/finding.schema.json` is field-aligned with `Finding`, verified
   by an alignment test following the existing per-model pattern.
5. All new and existing tests pass.

### Non-goals

Probabilistic confidence, ML, LLM-based correlation, collapsing findings
into a single score, modifying the existing `R⊆D`/`R⊆P`/`R⊆D∩P` functions.

### Validation commands

```text
uv run ruff check .
uv run pytest
uv run pytest tests/unit/test_models_finding.py tests/unit/test_conformance_correlation.py tests/integration/test_correlation_real_skill.py -v
```

### Review checkpoint

Stop after Phase 5. Do not begin Phase 6 until reviewed and approved.

---

## 9. Phase 6 — Policy and Risk Evaluation

### Objective

Extend the existing policy mechanism with the minimal `PolicyRule`/`effect`
representation from spec §10.1, and implement the closed, deterministic
severity classification from spec §10.5 — without breaking any existing
`set_policy(skill_id, frozenset)` caller or test.

### Why this phase comes here

Depends on Phase 5 (`Finding`s and `R` must exist for policy/severity to
have something to classify) but not on Phase 7 (`Assessment` only
aggregates what this phase produces; it does not need to exist first).

### Scope

1. **`PolicyRule`**: a frozen dataclass (`capability: str`, `effect:
   DecisionValue`) — reusing the existing `DecisionValue` enum
   (`ALLOW`/`FLAG`/`DENY`) for `effect` rather than inventing a parallel
   enum, since the spec's effect vocabulary is identical to the existing
   one.
2. **Policy extension in `engine.py`**: add `set_policy_rules(skill_id,
   rules: tuple[PolicyRule, ...])` as a new method, additive to the
   existing `set_policy(skill_id, frozenset)`. Internally, `set_policy`
   continues to work exactly as today (stored separately or normalized
   into the all-`ALLOW`-vs-default-`DENY` special case described in spec
   §10.1) — **no existing method signature changes**, and
   `tests/integration/test_end_to_end.py` Cases A/B/C must pass completely
   unmodified.
3. **Policy evaluation**: for each observed capability, the most specific
   matching `PolicyRule`'s `effect` applies; no matching rule → existing
   default behavior (absent from permitted set → violation), per spec
   §10.1 exactly.
4. **Severity classification** (`core/conformance/severity.py`): a pure
   function `classify_severity(decision: Decision, findings: list[Finding])
   -> Severity` where `Severity` is a new closed enum (`LOW`, `MEDIUM`,
   `HIGH`) in `core/models/` (alongside `DecisionValue`/`ReasonCode`, same
   file or a new `severity.py` — decided as a new small file to keep
   `decision.py` unchanged and avoid re-touching a frozen-pattern file).
   Fixed deterministic mapping, exactly as spec §10.5 describes: any
   `POLICY_VIOLATION`/`INTEGRITY_FAILURE` finding → `HIGH`; any
   `UNDECLARED_CAPABILITY`/`STATIC_RUNTIME_MISMATCH` finding with no
   policy violation → `MEDIUM`; no findings and `ALLOW` → `LOW`.

This phase explicitly keeps five concepts distinct, per spec §10.2 and the
planning brief's own requirement:

```text
Conformance  — existing ALLOW/FLAG/DENY Decision (unchanged)
Policy        — which PolicyRule matched, with what effect
Finding        — the specific issue (from Phase 5)
Decision        — the standardized outcome (unchanged model, same engine)
Severity         — the closed LOW/MEDIUM/HIGH classification (new, this phase)
```

No numeric or probabilistic score is introduced anywhere in this phase.

### Files to create

```text
src/agentic_conformance/core/models/severity.py
src/agentic_conformance/core/conformance/policy.py
src/agentic_conformance/core/conformance/severity.py
tests/unit/test_models_severity.py
tests/unit/test_conformance_policy.py
tests/unit/test_conformance_severity.py
```

### Files to modify

```text
src/agentic_conformance/core/conformance/engine.py   (add set_policy_rules;
    existing set_policy and evaluate() signatures/behavior unchanged)
src/agentic_conformance/core/models/__init__.py       (export Severity, additive)
```

### Files that must NOT be modified

```text
tests/integration/test_end_to_end.py                  (must keep passing
    unmodified — this is the explicit regression gate for this phase)
core/conformance/rules.py, structural.py, correlation.py
core/models/decision.py, evidence.py, skill.py, security_event.py, capability.py
```
plus the standing protected list (specs, `CLAUDE.md`, CI, `.gitignore`,
`pyproject.toml`).

### Inputs

`R` (Phase 4) for a skill, and either a legacy `frozenset` policy or a new
`tuple[PolicyRule, ...]` policy registered for it; `Finding`s and `Decision`
from Phase 5/existing engine.

### Outputs

Per-capability policy results (`capability`, matched rule or `None`,
resulting `effect`), and one `Severity` value per evaluation.

### Interfaces

```text
# core/conformance/policy.py
def evaluate_policy(
    rules: tuple[PolicyRule, ...], observed: set[str]
) -> dict[str, DecisionValue]: ...

# core/conformance/severity.py
def classify_severity(decision: Decision, findings: list[Finding]) -> Severity: ...

# engine.py addition
def set_policy_rules(self, skill_id: str, rules: tuple[PolicyRule, ...]) -> None: ...
```

### Data flow

```text
R (observed capabilities) + PolicyRule(s)
        ↓
policy.evaluate_policy()
        ↓
per-capability effect map
        ↓ (together with Decision + Finding list from Phase 5)
severity.classify_severity()
        ↓
Severity (LOW | MEDIUM | HIGH)
        ↓
        → consumed by Phase 7's Assessment
```

### Tests

- Unit: `evaluate_policy()` against rule sets covering ALLOW/FLAG/DENY
  effects, no-match fallback, and most-specific-rule precedence.
- Unit: `classify_severity()` against each branch of the fixed mapping.
- Regression: full existing `tests/integration/test_end_to_end.py` run,
  unmodified, confirming Cases A/B/C and the invalid-declaration case all
  still produce their original exact decisions/reason codes.
- New integration test demonstrating a policy-rule-based case that
  distinguishes a `FLAG`-effect capability from a `DENY`-effect capability
  for the same skill (spec §15 item 7), using `set_policy_rules`.

### Acceptance criteria

1. `set_policy(skill_id, frozenset)` behavior is byte-for-byte unchanged;
   `tests/integration/test_end_to_end.py` passes without modification.
2. A new policy-rule-based test shows `ALLOW` vs. `FLAG` vs. `DENY` effects
   distinguished for different capabilities of one skill.
3. `classify_severity()` is a pure function with no probabilistic/numeric
   output — only `LOW`/`MEDIUM`/`HIGH`.
4. All new and existing tests pass.

### Non-goals

A general-purpose policy language (wildcards, conditions, composition),
numeric/weighted risk scores, per-capability confidence values.

### Validation commands

```text
uv run ruff check .
uv run pytest
uv run pytest tests/integration/test_end_to_end.py -v
uv run pytest tests/unit/test_conformance_policy.py tests/unit/test_conformance_severity.py tests/unit/test_models_severity.py -v
```

### Review checkpoint

Stop after Phase 6. Do not begin Phase 7 until reviewed and approved.

---

## 10. Phase 7 — Security Assessment and Report

### Objective

Implement the canonical `Assessment` model (spec §10.3) aggregating the
Phase 1 `Skill`, Phase 2/4 evidence-derived `D`/`S`/`R`, Phase 5 `Finding`s,
the existing `Decision`, Phase 6 policy results and `Severity`, plus a
mechanically derived `recommendation` string — and a minimal textual
rendering, analogous to `examples/reference_app_walkthrough.py`.

### Why this phase comes here

Strictly an aggregation step: it depends on every prior phase's output
existing for the same skill, and produces nothing new that any other phase
consumes. It is last before the broadening work of Phase 8.

### Scope

1. **`Assessment` model** (`core/models/assessment.py`): exactly the fields
   listed in spec §10.3 — `schema_version`, `skill_id`, `skill_name`,
   `skill_version`, `source`, `declared_capabilities`, `static_capabilities`,
   `runtime_capabilities`, `findings` (`tuple[Finding, ...]`),
   `policy_results`, `decision`, `severity`, `recommendation`.
2. **`recommendation` derivation**: a small, fixed, deterministic mapping
   from `(decision.value, severity)` to a short fixed string (e.g.
   `DENY`+`HIGH` → `"DO NOT USE"`, `FLAG`+`MEDIUM` → `"REVIEW BEFORE USE"`,
   `ALLOW`+`LOW` → `"NO ISSUES FOUND"`) — never freeform/generated text,
   per spec §10.3's explicit requirement.
3. **Aggregation function**: `build_assessment(skill, static_evidence,
   events, findings, decision, policy_results, severity) -> Assessment`,
   pure, consuming only canonical objects already produced by Phases 1–6 —
   never re-deriving `D`/`S`/`R` itself and never reaching into adapter-,
   analyzer-, or execution-specific internals (spec §20 item 7: "report
   generation consumes canonical findings/assessment").
4. **Schema**: `schemas/assessment.schema.json`, field-aligned with
   `Assessment`, following the exact pattern of the four existing schemas.
5. **Minimal textual rendering**: a `format_assessment(assessment) -> str`
   function (plain text, no templating engine, no HTML) used by a new
   example walkthrough script — not a `reports/` package (per §3's
   directory decision), since the spec defers report *format* entirely
   (§10.6) and only a minimal, test-covered rendering is in scope.

### Files to create

```text
src/agentic_conformance/core/models/assessment.py
src/agentic_conformance/core/conformance/assessment.py   (build_assessment)
schemas/assessment.schema.json
examples/skillshield_assessment_walkthrough.py
tests/unit/test_models_assessment.py
tests/unit/test_conformance_assessment.py
tests/integration/test_assessment_real_skill.py
```

### Files to modify

```text
src/agentic_conformance/core/models/__init__.py   (export Assessment, additive)
```

### Files that must NOT be modified

Everything in the standing protected list, plus all files created in
Phases 1–6 (consumed as inputs, not altered).

### Inputs

The Phase 1 `Skill`; Phase 2 static `Evidence`; Phase 4 `SecurityEvent`s;
Phase 5 `Finding`s; the existing engine's `Decision`; Phase 6 policy
results and `Severity` — all for the same skill.

### Outputs

One `Assessment` instance per evaluated skill, plus its textual rendering.

### Interfaces

```text
# core/conformance/assessment.py
def build_assessment(
    skill: Skill,
    static_evidence: list[Evidence],
    events: list[SecurityEvent],
    findings: list[Finding],
    decision: Decision,
    policy_results: dict[str, DecisionValue],
    severity: Severity,
) -> Assessment: ...

def format_assessment(assessment: Assessment) -> str: ...
```

### Data flow

```text
Skill   static Evidence   SecurityEvents   Finding(s)   Decision   policy results   Severity
   └─────────┴──────────────────┴───────────────┴────────────┴───────────┴──────────┘
                                    ▼
                          build_assessment()
                                    ▼
                               Assessment
                                    ▼
                          format_assessment()
                                    ▼
                          printed/returned text
```

### Tests

- Unit: `build_assessment()` against hand-constructed fixtures for every
  field, including each branch of the `recommendation` mapping.
- Unit: `format_assessment()` produces a non-empty, deterministic string
  containing the skill name, decision value, and severity.
- Schema/model alignment test for `Assessment`, following the existing
  per-model pattern exactly.
- Integration: end-to-end `build_assessment()` using the real Phase 1
  skill's actual outputs from Phases 1–6, asserting every `Assessment`
  field is populated (non-`None`/non-empty where the spec requires it).

### Acceptance criteria

1. `Assessment` exists with every field from spec §10.3 populated for the
   real Phase 1 skill (spec §15 item 8).
2. `schemas/assessment.schema.json` is field-aligned with `Assessment`.
3. `recommendation` is always one of a small fixed set of strings, never
   freeform/generated text.
4. The new walkthrough script runs successfully and prints a complete
   assessment for the Phase 1 skill.
5. All new and existing tests pass.

### Non-goals

A frontend/dashboard, HTML/PDF/JSON-API rendering, any report format
decision beyond the minimal text rendering needed to demonstrate the
pipeline.

### Validation commands

```text
uv run ruff check .
uv run pytest
uv run python examples/skillshield_assessment_walkthrough.py
```

### Review checkpoint

Stop after Phase 7. Do not begin Phase 8 until reviewed and approved.

---

## 11. Phase 8 — Evaluation Against the Vulnerable Skills Testbed

### Objective

Demonstrate, end-to-end, all six required cases from
`docs/downloaded-skill-assessment-spec.md` §11 step 1 using one or more
**real** skills from `vuln-agentic-skills-app` (never a constructed or
synthetic substitute), then expand coverage to additional real skills
within the same testbed application (§11 step 2).

### Why this phase comes here

This is pure demonstration/breadth — it introduces no new core component,
only exercises Phases 1–7 against more real data. It must come last because
it depends on every other phase being complete and correct.

### Scope

1. **Six required cases, demonstrated using real skills from
   `vuln-agentic-skills-app` only** — never a deliberately constructed or
   artificial variant of a skill, and never a second synthetic test
   application:

```text
1. benign declared behavior              → ALLOW                 (Phases 1,4,5)
2. runtime undeclared behavior            → R-D nonempty, FLAG      (Phases 1,4,5)
3. static finding                          → S nonempty              (Phase 2)
4. runtime finding                          → R nonempty              (Phase 4)
5. declaration/runtime mismatch            → UNDECLARED_CAPABILITY or
                                             STATIC_RUNTIME_MISMATCH   (Phase 5)
6. policy violation                         → DENY, POLICY_VIOLATION   (Phase 6)
```

   If the Phase 1 skill cannot naturally demonstrate one of cases 1–5, a
   **different real skill from the same testbed** must be selected for
   that case instead — the skill's own source/behavior is never modified
   or fabricated to manufacture a finding that is not genuinely present.
   Case 6 (policy violation) is the one case legitimately produced by
   *configuration* rather than by selecting a different skill: applying a
   real `PolicyRule`/`set_policy_rules` policy (Phase 6) against a real
   skill's real, already-observed `R` is not fabricating behavior — it is
   the same technique the first milestone's Case C already used with
   `set_policy`, applying a policy decision on top of genuine observed
   capabilities. This differs categorically from altering what the skill
   itself does or inventing observations that did not occur.
2. **Expand to additional skills**: repeat Phase 1's adapter-mapping step
   (no new adapter architecture needed — the same
   `VulnAgenticSkillsAppAdapter` handles any skill in the same native
   format) for at least one more real skill from the testbed, and run the
   full pipeline (Phases 2–7) against it, to prove the pipeline
   generalizes within the testbed rather than being hand-fitted to one
   skill.
3. **External benchmarks are not touched** in this phase or milestone
   (Trail of Bits Overtly Malicious Skills, MalSkillBench,
   MaliciousSkillBench, SkillTrustBench) — named in the spec only as a
   future direction (spec §11 step 3, §14).

### Files to create

```text
tests/integration/test_skillshield_end_to_end.py
```

(One consolidated end-to-end test module covering all six cases plus the
second skill, analogous in spirit to
`tests/integration/test_end_to_end.py` from the first milestone, but for
the full Phase 1–7 pipeline rather than the hand-constructed native dicts
the first milestone used — this phase uses real adapter/analyzer/execution/
monitor output, from real skills in `vuln-agentic-skills-app`, not
synthetic native payloads and not a constructed/fake skill, since the
entire point of Phase 8 is proving the real pipeline over real testbed
data. Case 6 (policy violation) may apply a real Phase 6 policy
configuration on top of a real skill's real observed capabilities, per
Scope item 1 above — this is the one case produced by configuration rather
than by skill selection, and remains real-data-based throughout.)

### Files to modify

None — Phase 8 adds tests only; if an additional skill's native format
reveals a genuine adapter/analyzer gap, that gap is reported back to the
relevant earlier phase for a small additive fix (new detector, new mapping
entry) rather than resolved by non-additive changes.

### Files that must NOT be modified

The full standing protected list, plus every file from Phases 1–7 (only
additive extensions — e.g. a new mapping-table entry or detector — are
permitted if a genuine gap is found, and must be reported before being
made, per §18 of the governing instructions).

### Inputs

Two or more real skills from `vuln-agentic-skills-app` (the Phase 1 skill
plus at least one more).

### Outputs

Six demonstrated cases plus at least one additional fully-assessed skill;
no new canonical objects beyond what Phases 1–7 already define.

### Interfaces

None new — this phase is pure integration/testing over existing
interfaces.

### Data flow

```text
Skill #1 (Phase 1)  →  full Phase 1-7 pipeline  →  Assessment  →  6 cases verified
Skill #2 (new)         →  full Phase 1-7 pipeline  →  Assessment  →  pipeline generalizes
```

### Tests

End-to-end only, per the Test Strategy (§12 below): one test per required
case (six total) plus one full-pipeline test for the second skill.

### Acceptance criteria

1. All six cases from spec §11 step 1 are each demonstrated by a passing
   test, using real skills from `vuln-agentic-skills-app` — selecting a
   different real skill (or, for case 6 only, a real policy configuration
   applied to real observed behavior) when the originally selected skill
   does not naturally exercise a given case. No case may be satisfied by a
   constructed/fake skill or a second synthetic test application.
2. At least one additional real skill from the testbed is fully assessed
   end-to-end (Phases 1–7) with a passing test.
3. No external benchmark dependency is introduced.
4. All new and existing tests pass (65 original + every test added in
   Phases 1–8).

### Non-goals

External benchmark integration, performance evaluation, broad coverage
beyond two real skills.

### Validation commands

```text
uv run ruff check .
uv run pytest
uv run pytest tests/integration/test_skillshield_end_to_end.py -v
uv run python examples/skillshield_assessment_walkthrough.py
```

### Review checkpoint

Stop after Phase 8. This is the last implementation phase; final validation
is Batch 7 (§13 below), not a ninth phase.

---

## 12. Test Strategy

This milestone's tests fall into two categories that are not
interchangeable:

- **Deterministic synthetic/unit tests** — hand-constructed fixtures used
  for individual set operations, edge cases, invalid inputs, policy
  behavior, and model validation. These are necessary and sufficient for
  isolating logic, but they do not by themselves satisfy any acceptance
  criterion that requires real evidence (notably spec §15 items 5 and 6,
  and the Phase 8 six-case demonstration).
- **Real testbed evaluation** — tests that exercise the actual
  Phase 1 → Phase 2 → Phase 4 pipeline against real skills from
  `github.com/khadijasaq/vuln-agentic-skills-app`, asserting genuine,
  non-fabricated evidence and findings. Phase 5's and Phase 8's acceptance
  criteria are mandatory on this category specifically — a synthetic test
  passing is not a substitute for it.

### Unit tests (one file per concern, mirroring the first milestone's layout)

```text
test_vuln_app_adapter.py          — adapter mapping (Phase 1)
test_static_detectors.py           — pattern detectors (Phase 2)
test_static_analyzer.py             — traversal/orchestration (Phase 2)
test_execution_handle.py             — ExecutionHandle construction (Phase 3)
test_runtime_monitor.py               — observation → SecurityEvent mapping (Phase 4)
test_models_finding.py                 — Finding construction/validation (Phase 5)
test_conformance_correlation.py         — D/S/R set functions (Phase 5)
test_models_severity.py                   — Severity enum (Phase 6)
test_conformance_policy.py                 — PolicyRule evaluation (Phase 6)
test_conformance_severity.py                — classify_severity (Phase 6)
test_models_assessment.py                     — Assessment construction (Phase 7)
test_conformance_assessment.py                  — build_assessment/format_assessment (Phase 7)
```

### Integration tests

```text
test_vuln_app_registration.py            — adapter → canonical Skill (Phase 1)
test_static_analysis_evidence.py          — analyzer → Evidence, real skill (Phase 2)
test_subprocess_sandbox.py                 — execution lifecycle, real + fixture skill (Phase 3)
test_runtime_monitor_events.py              — monitor → SecurityEvent, real skill (Phase 4)
test_correlation_real_skill.py               — engine → findings, real D/S/R (Phase 5)
test_assessment_real_skill.py                 — assessment aggregation, real skill (Phase 7)
```

### End-to-end tests

```text
test_skillshield_end_to_end.py   — full Downloaded Skill → Adapter → Static Analysis →
                                    Controlled Execution → Runtime Monitoring → Evidence →
                                    Conformance → Policy → Assessment, for the six required
                                    cases plus a second real skill (Phase 8)
```

### Protection of existing tests

All 65 first-milestone tests
(`tests/unit/test_models.py`, `test_interfaces.py`,
`test_conformance_structural.py`, `test_conformance_rules.py`,
`test_reference_adapter.py`, `test_package_importable.py`;
`tests/integration/test_conformance_engine.py`,
`test_end_to_end.py`) are run, unmodified, as part of every phase's
validation step (`uv run pytest` runs the whole suite, not just new files).
No phase may edit an existing test file to make new functionality pass; a
failing existing test after a change means the change is wrong, not the
test.

---

## 13. Batching / Implementation Control

Batches correspond 1:1 to phases except where two phases are tightly
coupled (Phase 3+4) or where final cleanup needs its own batch, matching
the brief's recommended structure.

### Batch 1 — Phase 1 (Downloaded Skill Integration)

- **Allowed files:** exactly the "Files to create" list in §4, plus
  read-only inspection of the external `vuln-agentic-skills-app` repository
  (not committed into this repository — only informs the adapter's design).
- **Prohibited files:** everything under "Files that must NOT be modified"
  in §4; all of `core/`; all of `adapters/reference_app/`; `schemas/`;
  existing tests; `docs/`, `CLAUDE.md`, CI, `.gitignore`, `pyproject.toml`.
- **Validation:** `uv run ruff check .`; `uv run pytest`.
- **Stop point:** after Phase 1's acceptance criteria are met and reported.
- **Review required** before Batch 2.

### Batch 2 — Phase 2 (Static Analysis Foundation)

- **Allowed files:** §5's "Files to create" list.
- **Prohibited files:** everything Batch 1 prohibited, plus Batch 1's own
  new files (consumed, not edited) unless a genuine Phase 1 gap is found
  and reported first.
- **Validation:** `uv run ruff check .`; `uv run pytest`.
- **Stop point:** after Phase 2's acceptance criteria are met and reported.
- **Review required** before Batch 3.

### Batch 3 — Phase 3 + Phase 4 (Controlled Execution + Runtime Monitoring)

Combined into one batch because Phase 4 has no independent value without
Phase 3 (there is nothing to monitor without an execution to observe), and
splitting them would force an artificial review checkpoint between two
phases that are only meaningfully testable together (Phase 3's own
integration test already requires running the real skill, which Phase 4
immediately consumes).

- **Allowed files:** §6 and §7's "Files to create" lists.
- **Prohibited files:** everything prior batches prohibited, plus Batches
  1–2's files (consumed, not edited).
- **Validation:** `uv run ruff check .`; `uv run pytest`.
- **Stop point:** after both Phase 3 and Phase 4 acceptance criteria are
  met and reported together.
- **Review required** before Batch 4.

### Batch 4 — Phase 5 (D/S/R Correlation)

- **Allowed files:** §8's "Files to create" list (including `Finding`,
  pulled forward into this phase per §8's documented decision).
- **Prohibited files:** everything prior batches prohibited, plus
  `core/conformance/rules.py`, `structural.py`, `engine.py` (used, not
  edited in this batch).
- **Validation:** `uv run ruff check .`; `uv run pytest`. The real-data
  integration test (`test_correlation_real_skill.py`) must assert a
  non-empty `UNDECLARED_CAPABILITY` and a non-empty
  `STATIC_RUNTIME_MISMATCH` finding from an actual real skill in
  `vuln-agentic-skills-app` — an empty-findings result is not an
  acceptable substitute; if the originally selected skill does not
  produce these, a different real skill from the same testbed must be
  used before this batch is reported complete.
- **Stop point:** after Phase 5's acceptance criteria are met and reported.
- **Review required** before Batch 5.

### Batch 5 — Phase 6 + Phase 7 (Policy, Severity, Finding aggregation, Assessment, Report)

Combined because Phase 7's `Assessment` has no meaningful content without
Phase 6's `Severity` and policy results (every `Assessment` field in spec
§10.3 that isn't already covered by Phases 1–5 comes from Phase 6) — and
because splitting them would mean Phase 6's own "review checkpoint" has no
end-to-end artifact to show (severity/policy results with nothing
aggregating them), while Phase 7 has nothing to aggregate without Phase 6.
This mirrors the brief's own suggested batching (§16 of the instructions)
exactly.

- **Allowed files:** §9 and §10's "Files to create"/"Files to modify"
  lists.
- **Prohibited files:** everything prior batches prohibited, plus
  `tests/integration/test_end_to_end.py` (regression-protected, not
  edited — see §9's explicit non-modification rule), and `core/models/
  decision.py`, `evidence.py`, `skill.py`, `security_event.py`,
  `capability.py` (used, not edited).
- **Validation:** `uv run ruff check .`; `uv run pytest`;
  `uv run pytest tests/integration/test_end_to_end.py -v` (explicit
  regression check); `uv run python
  examples/skillshield_assessment_walkthrough.py`.
- **Stop point:** after both Phase 6 and Phase 7 acceptance criteria are
  met and reported together.
- **Review required** before Batch 6.

### Batch 6 — Phase 8 (Testbed Evaluation)

- **Allowed files:** §11's "Files to create" list (tests only).
- **Prohibited files:** everything prior batches prohibited; any
  non-additive change to Phases 1–7 files (an additive fix — e.g. one new
  mapping-table entry — is permitted only if a genuine gap is found and
  reported before being made, per the frozen-files rule in §18 of the
  governing instructions). No constructed/fake skill and no second
  synthetic test application may be introduced in this batch — all six
  cases use real skills from `vuln-agentic-skills-app`, per §11's Scope.
- **Validation:** `uv run ruff check .`; `uv run pytest`;
  `uv run pytest tests/integration/test_skillshield_end_to_end.py -v`.
- **Stop point:** after all six required cases and the second-skill
  demonstration are reported.
- **Review required** before Batch 7.

### Batch 7 — Final validation / documentation cleanup

- **Allowed files:** no new functionality; only cleanup of implementation
  issues found during final validation (mirroring the first milestone's
  Phase 6/Batch 3 discipline exactly: "Do NOT make cosmetic or speculative
  changes merely for cleanup. If no changes are actually necessary, do not
  modify files just to make a change.").
- **Prohibited files:** `docs/spec.md`, `docs/plan.md`,
  `docs/downloaded-skill-assessment-spec.md`, `CLAUDE.md`,
  `docs/downloaded-skill-assessment-plan.md` itself, and any file not
  already created/modified by Batches 1–6, unless a genuine defect is
  found and reported.
- **Validation:** `uv run ruff check .`; `uv run pytest` (full suite,
  expected count: 65 existing + all new tests from Batches 1–6);
  `uv run python examples/skillshield_assessment_walkthrough.py`;
  re-verification that every schema in `schemas/` remains field-aligned
  with its model (including the two new ones).
- **Stop point:** final milestone report, structured like the first
  milestone's Batch 3 report (status, files changed, cleanup/fixes,
  validation results, specification compliance checked against every
  acceptance criterion in §19 below, final architecture, out-of-scope
  confirmation, git status).
- **No further batch follows.**

---

## 14. Architectural Boundary Checks

Verified at the end of every batch above, and re-verified in Batch 7 as a
final gate:

1. **`core/` remains product-independent.** No file under `core/` imports
   from `adapters/vuln_agentic_skills_app/`, `analysis/`, or `execution/`.
   `core/` only exposes new pure functions/models that any adapter or
   analyzer may call into — never the reverse.
2. **The vulnerable skills app exists only behind an adapter.** All
   knowledge of its manifest format, file layout, and entry point lives in
   `adapters/vuln_agentic_skills_app/`.
3. **Static analysis is not embedded into core conformance logic.**
   `analysis/static/` produces `Evidence`; it does not call into
   `core/conformance/engine.py` or implement any `R⊆D`-style rule itself.
4. **Runtime monitoring is not embedded into core conformance logic.**
   `analysis/runtime/` produces `SecurityEvent`s; it does not implement
   conformance rules.
5. **Sandbox technology is not assumed by canonical models.**
   `core/models/*.py` has zero references to `subprocess`,
   `execution/`, or any sandbox-specific type; `ExecutionHandle` is
   consumed only by `analysis/runtime/monitor.py`, never by `core/`.
6. **Policy evaluation remains conceptually separate.** `PolicyRule`
   evaluation (`core/conformance/policy.py`) and `Decision` production
   (`engine.py`) are distinct functions; a `Decision` is never constructed
   directly from a policy result without going through the existing
   engine logic.
7. **Report generation consumes canonical findings/assessment.**
   `format_assessment()` takes only an `Assessment` instance — it has no
   access to adapters, analyzers, or the sandbox.
8. **Existing first-milestone APIs remain compatible.**
   `ConformanceAPI`, `ProductAdapter`, `register_skill`, `emit_event`,
   `evaluate`, and `set_policy(skill_id, frozenset)` all keep their
   original signatures and behavior.
9. **Existing tests continue to pass.** The original 65 tests are run,
   unmodified, after every batch.
10. **No unnecessary repository reorganization occurs.** Only the
    directories decided in §3 are created; no existing file moves.

---

## 15. Final Implementation Order

```text
Phase 1  (Downloaded Skill Integration)
   ↓
Phase 2  (Static Analysis Foundation)
   ↓
Phase 3  (Controlled Execution Contract)
   ↓
Phase 4  (Runtime Monitoring)
   ↓
Phase 5  (D/S/R Correlation + Finding)
   ↓
Phase 6  (Policy + Severity)
   ↓
Phase 7  (Assessment + Report)
   ↓
Phase 8  (Testbed Evaluation)
```

**No phase may run in parallel with another.** Although Phase 2 (static
analysis) does not technically depend on Phase 3/4 (execution/monitoring)
at the data level — both are independent evidence producers reading from
Phase 1's output — this plan still sequences them strictly, for two
concrete reasons specific to this repository's working practice, not mere
convenience:

1. **Single-reviewer batch discipline.** Every phase in both milestones so
   far has ended with "stop for repository-owner review" before the next
   begins (`docs/plan.md` §"Phase Discipline"). Parallel phases would
   produce two simultaneous, unreviewed diffs, breaking that discipline.
2. **Phase 5 needs both `S` and `R` to exist together to be testable.**
   Even if Phase 2 and Phase 3/4 were implemented in parallel, Phase 5
   cannot be validated against real data until both land — so parallelizing
   them would not shorten the critical path to a working Phase 5, only add
   coordination risk for no schedule benefit in a single-implementer,
   single-reviewer workflow.

---

## 16. Acceptance-Criteria Mapping

Every numbered acceptance criterion from
`docs/downloaded-skill-assessment-spec.md` §15, mapped to implementation
phase, files/components, tests, and validation evidence.

| # | Spec Acceptance Criterion (§15) | Phase | Files/Components | Tests | Validation Evidence |
|---|---|---|---|---|---|
| 1 | Downloaded skill registered as canonical `Skill` via dedicated adapter | Phase 1 | `adapters/vuln_agentic_skills_app/adapter.py`, `mapping.py` | `test_vuln_app_adapter.py`, `test_vuln_app_registration.py` | `uv run pytest tests/unit/test_vuln_app_adapter.py tests/integration/test_vuln_app_registration.py` |
| 2 | Static analyzer produces ≥1 real `Evidence` (`source=STATIC`), populating `S` | Phase 2 | `analysis/static/detectors.py`, `analyzer.py`, `evidence.py` | `test_static_detectors.py`, `test_static_analyzer.py`, `test_static_analysis_evidence.py` | `uv run pytest tests/integration/test_static_analysis_evidence.py` |
| 3 | Controlled execution runs the skill under observation, isolation limits documented | Phase 3 | `execution/handle.py`, `subprocess_sandbox.py` | `test_execution_handle.py`, `test_subprocess_sandbox.py` | module docstring review + `uv run pytest tests/integration/test_subprocess_sandbox.py` |
| 4 | Runtime observations become canonical `SecurityEvent`s, populating `R` via `emit_event` | Phase 4 | `analysis/runtime/monitor.py` | `test_runtime_monitor.py`, `test_runtime_monitor_events.py` | `uv run pytest tests/integration/test_runtime_monitor_events.py` |
| 5 | All seven §8.3 comparisons (`S⊆D`, `S-D`, `R-D`, `R-S`, `S-R`, `R∩D`, `R∩P`) implemented/represented and explicitly tested — the three reused via existing helpers/plain set ops, not just the four new functions; ≥1 mandatory nonempty result against real testbed data | Phase 5 | `core/conformance/correlation.py` (new functions), existing `rules.undeclared_capabilities` (reused) | `test_conformance_correlation.py` (all seven, including reused relationships), `test_correlation_real_skill.py` (mandatory real-data assertion) | `uv run pytest tests/unit/test_conformance_correlation.py tests/integration/test_correlation_real_skill.py` |
| 6 | ≥1 `UNDECLARED_CAPABILITY` and ≥1 `STATIC_RUNTIME_MISMATCH` Finding, correctly attributed to originating Evidence/SecurityEvent, demonstrated against a **real** skill from `vuln-agentic-skills-app` flowing through the real Phase 1→2→4 pipeline (not merely fixture data) | Phase 5 | `core/models/finding.py`, `core/conformance/correlation.py` | `test_models_finding.py`, `test_conformance_correlation.py`, `test_correlation_real_skill.py` | `uv run pytest tests/unit/test_models_finding.py tests/integration/test_correlation_real_skill.py` |
| 7 | Policy evaluation distinguishes `ALLOW` vs. `DENY` effect for same skill, no regression | Phase 6 | `core/conformance/policy.py`, `core/models/severity.py`, `engine.py` (additive) | `test_conformance_policy.py`, regression run of `test_end_to_end.py` | `uv run pytest tests/integration/test_end_to_end.py tests/unit/test_conformance_policy.py` |
| 8 | `Assessment` produced with every §10.3 field populated, schema-aligned | Phase 7 | `core/models/assessment.py`, `conformance/assessment.py`, `schemas/assessment.schema.json` | `test_models_assessment.py`, `test_conformance_assessment.py`, `test_assessment_real_skill.py` | `uv run pytest tests/integration/test_assessment_real_skill.py`; schema alignment check |
| 9 | Six demonstration cases (§11 step 1) shown using **real skills** from `vuln-agentic-skills-app` — selecting a different real skill per case where needed, plus a real policy configuration for case 6 only; no constructed/fake skill and no second synthetic test application; ≥1 additional real skill fully assessed end-to-end | Phase 8 | `tests/integration/test_skillshield_end_to_end.py` | same file (6 cases, ≥2 real skills) | `uv run pytest tests/integration/test_skillshield_end_to_end.py -v` |
| 10 | `core/` has zero branches/assumptions specific to the testbed app, sandbox, or static analyzer | All phases | N/A (boundary check) | Architectural boundary check §14 items 1–5 | manual grep/review during each batch's stop point |
| 11 | New canonical models (`Finding`, `Assessment`) have schema-aligned schemas | Phase 5, Phase 7 | `schemas/finding.schema.json`, `schemas/assessment.schema.json` | `test_models_finding.py` (alignment), `test_models_assessment.py` (alignment) | schema/model field-alignment test pattern, as used for the first milestone's four schemas |
| 12 | All existing first-milestone tests continue to pass unmodified | All phases | N/A | full suite | `uv run pytest` after every batch; final count check in Batch 7 |

---

## 17. Implementation Practices (carried over from `docs/plan.md`, unchanged)

- **Source of Truth:** `docs/downloaded-skill-assessment-spec.md` defines
  WHAT; this document defines HOW. If they conflict, the specification
  wins, and the conflict is reported rather than silently resolved.
- **Minimalism:** small focused modules, standard-library-only
  dependencies, explicit data structures, no premature abstraction — e.g.
  the Phase 3 sandbox choice uses only `subprocess`/`resource`/stdlib,
  introducing no new runtime dependency for this milestone, matching the
  first milestone's own "no runtime dependencies" discipline.
- **Repository Stability:** only the directories listed in §3 are
  introduced; no existing file is reorganized.
- **Version Control:** no commits, branches, tags, pushes, merges, resets,
  rebases, or stashes are performed by Claude during implementation of this
  plan. The target branch `feat/downloaded-skill-assessment` is created by
  the repository owner, not by Claude.
- **Phase Discipline:** each phase/batch runs its validation commands,
  reports results, and stops for repository-owner review before the next
  begins — exactly as `docs/plan.md`'s own "Phase Discipline" section
  already establishes for the first milestone.
