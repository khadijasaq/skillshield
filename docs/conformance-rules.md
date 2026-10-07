# SkillShield Conformance Rules

Executable reference for the deterministic rules implemented in
`src/skillshield/conformance/`. This document is extended (not replaced) by
each later batch as static analysis (P2), controlled execution (P3), and
policy loading (P4) make D/S/R/P real instead of synthetic.

## 1. Capability vocabulary

SkillShield reuses the open capability registry from
`agentic_conformance.core.models.capability` and adds one identifier:

| Capability          | Source milestone |
| -------------------- | ----------------- |
| `task.read`          | pre-existing       |
| `network.egress`      | pre-existing       |
| `process.execute`     | pre-existing       |
| `filesystem.write`    | pre-existing       |
| `credential.read`     | pre-existing       |
| `filesystem.read`     | added in P0/P1 (Batch 1) |

The vocabulary is an open registry (`register_capability`), not a closed
enum, so later batches may add more identifiers without touching `core/`.

## 2. D/S/R/P correlation (`conformance/correlation.py`)

Five relationships, each a plain set difference over capability-identifier
strings:

| Relationship | Function                 | Meaning                                                              |
| ------------ | ------------------------- | ---------------------------------------------------------------------|
| `S - D`      | `undeclared_static`        | Indicated by source code but not declared.                           |
| `R - D`      | `undeclared_runtime`       | Observed during execution but not declared.                          |
| `S - R`      | `static_only`               | Statically indicated but not observed at runtime.                    |
| `R - S`      | `runtime_only`              | Observed at runtime but not indicated by static analysis.            |
| `R - P`      | `policy_violations`         | Observed capability not permitted by policy.                         |

These functions take plain sets and have no dependency on ingestion, static
analysis, or execution -- they are exercised in Batch 1 with synthetic sets,
and will be fed real S (Batch 2) and real R (Batch 3) sets unchanged.

## 3. Finding generation (`conformance/engine.py`)

`build_findings(declared, static, runtime, policy=None, declaration_problem=None)`
turns the five correlations into `Finding` objects:

- Each capability in `R - D` produces one `UNDECLARED_CAPABILITY` finding
  (runtime-confirmed).
- Each capability in `S - D` that is **not already** in `R - D` produces one
  `UNDECLARED_CAPABILITY` finding (static-only) -- a capability is never
  reported twice for the same underlying gap; the stronger (runtime-
  confirmed) finding wins.
- Each capability in `R - S` and each capability in `S - R` produces one
  `STATIC_RUNTIME_MISMATCH` finding (two directions, two different
  explanations, same finding type and severity).
- When a `policy` is supplied, each capability in `R - P` produces one
  `POLICY_VIOLATION` finding.
- A non-`None` `declaration_problem` (missing or malformed manifest.json)
  produces exactly one `INVALID_DECLARATION` finding.

A finding's wording never claims static evidence proves runtime behavior,
and never claims runtime absence proves a capability cannot occur
(docs/product-spec.md §14, §15, §31).

## 4. Severity table (`conformance/severity.py`)

| Finding type              | Severity                                         |
| -------------------------- | ------------------------------------------------- |
| `POLICY_VIOLATION`          | `CRITICAL` if the same capability is also undeclared, else `HIGH` |
| `UNDECLARED_CAPABILITY`      | `HIGH` if runtime-confirmed, else `MEDIUM` (static-only) |
| `STATIC_RUNTIME_MISMATCH`    | `LOW`                                             |
| `INVALID_DECLARATION`        | `MEDIUM`                                          |
| `ANALYSIS_FAILURE`            | `LOW`                                             |
| `EXECUTION_FAILURE`           | `LOW`                                             |

Rationale: a policy violation that the skill also tried to hide (by not
declaring it) is the single worst-evidenced case SkillShield can produce
(deliberate undeclared behavior that is also explicitly denied), hence
`CRITICAL`. A policy violation on an openly declared capability is still
`HIGH` because policy is the operator's explicit security boundary. An
undeclared capability actually seen at runtime is stronger evidence than one
only indicated by source code, hence `HIGH` vs. `MEDIUM`. Static/runtime
mismatches without a declaration or policy problem are the weakest signal
(they may simply reflect an execution scenario that didn't exercise a code
path) and analysis/execution failures are tooling limitations, not skill
behavior -- both `LOW`.

## 5. Findings -> Recommendation mapping (`conformance/assessment.py`)

```text
No findings                -> NO ISSUES FOUND
Max finding severity LOW/MEDIUM   -> REVIEW BEFORE USE
Max finding severity HIGH/CRITICAL -> DO NOT USE
```

`recommend()` takes the maximum severity across all findings for one skill
and maps it through this table. SkillShield never produces any
recommendation string outside these three, and never uses the word
"malicious".

## 6. Declaration format (P1)

A skill's declaration is `manifest.json` at the skill root:

```json
{
  "id": "sample-skill",
  "name": "Sample Skill",
  "version": "1.0.0",
  "description": "...",
  "capabilities": [
    { "id": "task.read", "scope": ["*"], "reason": "..." }
  ],
  "entrypoint": "skill.py:run"
}
```

`id`, `name`, `version` are required; `capabilities` entries may be plain
capability-id strings or `{id, scope?, reason?}` objects; `entrypoint` is
optional in P1 (used by P3's controlled execution). A missing manifest, a
manifest that is not valid JSON, one missing a required field, or one with
the wrong JSON types for `capabilities`/`entrypoint` is **not fatal** --
`skillshield.ingestion.declaration.load_declaration` never raises; it
returns a `DeclarationProblem` (`kind="missing"` or `kind="malformed"`)
that the conformance engine turns into one `INVALID_DECLARATION` finding.
A declaration naming a capability identifier outside the supported
vocabulary is also captured as a (non-fatal) `malformed` problem, even
though the declaration itself remains usable.

## 7. Archive safety limits (P1)

| Limit                     | Value         |
| -------------------------- | -------------- |
| Max uncompressed size       | 50 MB          |
| Max member count            | 10,000         |

Both are enforced in `skillshield/ingestion/archive.py` before extraction
begins (member sizes/count are read from the ZIP's central directory without
extracting anything). Any archive member whose path resolves outside the
extraction root (`..` traversal, absolute paths, Windows drive-letter/UNC
paths) or that is a symlink is rejected with `PathTraversalError` before any
file is written.

## 8. Static analysis (P2)

`skillshield/analysis/static/` generates real S (statically inferred
capabilities) plus Evidence, by inspecting each skill source file's AST
(`ast.parse`) -- it never imports, executes, or `exec`'s the skill's code.
`analyze(skill, artifact)` runs every detector over each `.py` file in
`skill.source_files` and returns a `StaticAnalysisResult(capabilities,
evidence, analysis_failures)`.

### 8.1 Detector -> capability mapping

| Capability | Source pattern | Example |
| --- | --- | --- |
| `filesystem.read` | `open(...)` with no mode, or `"r"`/`"rb"`/`"rt"`; `os.listdir`/`os.scandir` | `open("tasks.json")` |
| `filesystem.write` | `open(...)` with `"w"`/`"wb"`/`"a"`/`"ab"`/`"x"`; `os.remove`/`os.mkdir`/`os.makedirs` | `open("out.txt", "w")` |
| `network.egress` | `import socket`/`requests`/`httpx`/`urllib.request`/`http.client` (the import alone is evidence); `requests.get/post/put/delete`, `httpx.get/post`, `urllib.request.urlopen`, `socket.socket(...)` | `requests.get(url)` |
| `process.execute` | `import subprocess`; `subprocess.run/Popen/call/check_output/check_call`; `os.system`/`os.popen`; any `os.exec*`/`os.spawn*` | `subprocess.run([...])` |
| `credential.read` | `os.getenv(...)`/`os.environ.get(...)`/`os.environ[...]` whose literal key contains `key`/`token`/`secret`/`password`/`credential` (case-insensitive); `open(...)` on a literal path containing `.env`, `credentials.json`, or `id_rsa` | `os.getenv("API_SECRET_KEY")` |

A capability can legitimately be detected by more than one rule for the
same call (e.g. `open("credentials.json")` is both `filesystem.read` *and*
`credential.read`) -- this is intentional, not double-counting a bug.

Simple `import X as Y` / `from X import Y [as Z]` aliasing is resolved
against the call target before matching (so `import subprocess as sp;
sp.run(...)` is still recognized); plain `import X` needs no resolution
since the bound name already matches the attribute-chain root used at call
sites.

### 8.2 `ANALYSIS_FAILURE`

A file that cannot be read (`OSError`/`UnicodeDecodeError`) or parsed
(`SyntaxError`/`ValueError`) produces one entry in `analysis_failures`
(`"<file>: <reason>"`) and is simply skipped -- analysis of the skill's
other files always continues. `conformance.engine.build_findings` turns
each entry into one `ANALYSIS_FAILURE` finding (`LOW` severity, per §4);
this is a tooling-coverage gap, not evidence about the skill's behavior.

### 8.3 Documented coverage gap -- static possibility, not proof

Per product-spec §14/§31, static evidence means "the source code indicates
this capability *may* be used," never "this is proven to happen." The
detectors do no data-flow analysis, so they do **not** see:

- capability access reached through `getattr(module, "name")(...)` or any
  other dynamic-dispatch indirection;
- a module/callable captured into a variable and invoked later (e.g.
  `p = Path(...)` then `p.write_text(...)` on a later line) -- the detector
  only resolves call targets through `import`/`from...import` aliasing and
  the directly-chained constructor form, not through inferred variable
  *types*, so there is no way for it to know that some arbitrary name is "a
  `Path` instance" versus anything else with a `.read_text()` method.
  The directly-chained form (`Path("x").read_text()`,
  `pathlib.Path("x").write_text(...)`, and the `_bytes` variants, however
  written -- `Path` imported plain, `from pathlib import Path`, or aliased)
  **is** recognized, as `filesystem.read`/`filesystem.write` respectively
  (see `_PATH_CONSTRUCTOR_METHOD_PATTERNS` in `detectors.py`). (An earlier
  version of this document claimed this form was *not* recognized, based on
  a real gap found during Batch 4 review; it was fixed immediately after by
  adding an explicit check for a read/write method called directly on a
  `Path(...)` constructor call, and this section was corrected to match.)
- a mode/path argument that isn't a literal string constant (e.g.
  `open(path, mode)` where `mode` is a variable);
- any capability reached via `eval`/`exec`, `importlib.import_module`, or
  equivalent string-driven dynamism.

These gaps are demonstrated directly in
`tests/fixtures/skillshield/static_dynamic_gap/` and asserted (not hidden)
in `tests/unit/test_skillshield_static_analyzer.py::test_unsupported_source_construct_is_a_documented_gap`.
A real runtime execution of the same code (P3) can still observe the
capability even when static analysis misses it -- which is exactly what
the `R - S` correlation (§2) is for.

## 9. Controlled execution and runtime monitoring (P3)

`skillshield/execution/` runs a skill's declared entrypoint in a restricted
subprocess and observes its behavior via CPython's `sys.addaudithook`
(PEP 578). This is **not a secure sandbox** -- see `SECURITY_LIMITATIONS.md`
for exactly what is and is not guaranteed. `execute(skill, artifact,
timeout_seconds=...)` returns an `ExecutionResult(status,
runtime_capabilities, events, duration_seconds, exit_code, failure_reason,
...)`.

### 9.1 Entrypoint resolution

`skill.declaration.entrypoint` (`"file.py:callable"`) must name a file in
`skill.source_files` and a function/class/module-level name that a static
check (`ast.parse`, no execution) confirms exists in that file. If the
declaration is missing, the entrypoint field is absent, the file isn't
among the skill's sources, or the named target doesn't statically exist,
`execute()` returns `status=NO_ENTRYPOINT` without spawning anything.

### 9.2 Audit-event -> capability mapping (`execution/monitor.py`)

Event names and argument shapes below were confirmed empirically on this
project's CPython 3.12 venv with a throwaway probe script (not assumed from
documentation) before being wired in:

| Audit event | Capability | Notes |
| --- | --- | --- |
| `open` (args: `path, mode, flags`) | `filesystem.write` if `mode` starts with `w`/`a`/`x`; `filesystem.read` otherwise | `mode` is the real resolved mode string CPython passes, not re-derived from flags |
| `os.remove`, `os.rmdir`, `os.rename`, `os.mkdir` | `filesystem.write` | |
| `os.listdir`, `os.scandir` | `filesystem.read` | |
| `socket.connect` (args: `socket_obj, address`) | `network.egress` | **Fires even when the connection attempt itself fails** (confirmed with a connect to a closed local port raising `TimeoutError`) -- the attempt, not the success, is the capability signal |
| `subprocess.Popen` | `process.execute` | |
| `os.system` | `process.execute` | |
| `os.exec*`, `os.spawn*`, `os.posix_spawn` | `process.execute` | matched by event-name prefix, since there are too many `os.exec*` variants to list individually |

**Confirmed empirically: `os.environ.get(...)` and `os.getenv(...)` raise
*no* audit event at all** on this CPython version -- runtime observation is
blind to plain environment-variable reads (only `os.putenv`/`os.unsetenv`
writes are audited). This is a real limitation, documented in
`SECURITY_LIMITATIONS.md`, not an oversight in `monitor.py`.

### 9.3 Import-machinery noise filtering

Running a skill at all means importing its entrypoint module, which makes
CPython read the module's own source and probe/write `.pyc` bytecode
caches for it *and* for every stdlib module it imports (confirmed
empirically: a `socket`-only skill produced `open` events for
`socket.cpython-312.pyc`/`selectors.cpython-312.pyc` under the venv's own
`Lib/__pycache__`). Left unfiltered, this would report `filesystem.read`/
`filesystem.write` as runtime-observed for *every* skill regardless of what
its own code does -- a serious false-positive source, not a cosmetic one.
Two mitigations, both required (neither alone is sufficient):

1. `sandbox.py` launches the harness with `-B` (`sys.dont_write_bytecode`),
   so no *new* `.pyc` is written for this run.
2. `monitor.is_bytecode_cache_event()` filters out any event touching a
   path containing `__pycache__` or ending in `.pyc` regardless of event
   type -- needed because *reading* a pre-existing stdlib cache from the
   shared venv still happens even with `-B`.
3. `harness.py` separately excludes the single `open` event for the entry
   file's own source being read by the import machinery (compared by
   resolved absolute path), since that `.py` read is Python bootstrapping
   itself, not the skill accessing a file.

### 9.4 Partial evidence on kill/crash

The harness opens the events file and installs the audit hook before doing
anything else, and flushes after every single event, so a process killed
mid-run (timeout) still leaves on disk whatever it managed to do before
being killed -- `sandbox.py` reads and parses this file regardless of how
the process ended, tolerating a truncated/partial final JSON line.

### 9.5 Timeout and termination

Only a wall-clock timeout is enforced -- there is **no** CPU or memory
limit. On timeout, the whole process tree is targeted for termination:
`taskkill /F /T /PID` on Windows, `os.killpg(..., SIGKILL)` on POSIX (the
child is launched in its own process group specifically so this is
possible). This is best-effort, not a guarantee -- see
`SECURITY_LIMITATIONS.md`.

### 9.6 `EXECUTION_FAILURE` / `CRASHED` / `TIMEOUT`

`conformance.engine.build_findings(..., execution_failures=(...))` turns
each entry into one `EXECUTION_FAILURE` finding (`LOW` severity, per §4) --
a failed/timed-out/no-entrypoint execution is a tooling-coverage gap for
*that* run, not evidence the skill is unsafe; whatever runtime evidence was
collected before the failure (if any) is still correlated normally via
`runtime_evidence`/`runtime`.

## 10. Policy loading (P4)

`skillshield/policy/loader.py` is the only way to get a
`SecurityPolicy` other than constructing one directly: a conservative
built-in default, or a small JSON file. There is deliberately no universal
policy language -- a policy remains exactly what it was in P0 (§ above): a
name plus a flat permitted-capability set (`core/models/policy.py`).

### 10.1 Default policy

```text
name: "default"
permitted_capabilities: {task.read, filesystem.read}
```

Everything else (`filesystem.write`, `network.egress`, `process.execute`,
`credential.read`) is denied by omission. Rationale: least-privilege -- a
skill that only reads its own data needs nothing more; this is also the
policy every P4 end-to-end validation fixture below is designed against.

### 10.2 Policy file format

```json
{ "name": "my-policy", "permitted_capabilities": ["task.read", "filesystem.read"] }
```

`load_policy(None)` returns the default policy above. `load_policy(path)`
reads and parses that path. A malformed policy *file* -- invalid JSON, not
a JSON object, missing/empty `name`, a non-list/non-string-list
`permitted_capabilities`, or any capability identifier not in
`agentic_conformance.core.models.capability.supported_capabilities()` --
raises `PolicyLoadError` immediately. This is intentionally **not** the
same non-fatal handling as a skill's own declaration (§6): a policy file is
operator configuration, not attacker/author-controlled content being
assessed, so a mistake in it should fail loudly rather than silently
degrade or become a finding about an unrelated skill. See `DECISIONS.md`
("P4 (Batch 4)") for the full rationale.

## 11. P4 end-to-end validation

Four fixtures under `tests/fixtures/skillshield/`, each run through the
*real* pipeline (`ingest` → `analyze` → `execute` → `build_findings` →
`recommend`, not synthetic D/S/R/P sets) by
`tests/integration/test_skillshield_p4_conformance_validation.py`, prove
the exact outcomes `docs/product-plan.md` §8 requires:

| Scenario | Fixture | Result |
| --- | --- | --- |
| Clean skill | `clean_pipeline/` | zero findings → `NO ISSUES FOUND` |
| Undeclared behavior | `runtime_undeclared_network/` (reused from Batch 3 — already exactly this case) | `UNDECLARED_CAPABILITY` (`HIGH`) finding (plus, correctly, a simultaneous `POLICY_VIOLATION` under the default policy, since the same undeclared capability is also denied) → `DO NOT USE` |
| Policy violation | `policy_violation_pipeline/` (declares the capability, so this is isolated from the undeclared case) | `POLICY_VIOLATION` (`HIGH`) finding → `DO NOT USE` |
| Static/runtime mismatch | `mismatch_pipeline/` (a genuinely conditional write path gated on an env var the controlled-execution environment allow-list never sets) | `STATIC_RUNTIME_MISMATCH` (`LOW`) finding → `REVIEW BEFORE USE` |
