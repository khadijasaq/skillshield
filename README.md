# SkillShield

**SkillShield is a product-independent security assessment layer for
downloaded Agentic Skills.** You download a skill (a ZIP, or a local
directory) from wherever you found it — GitHub, a marketplace, a personal
repository — and before you trust it, SkillShield tells you what it
**declares**, what its source code **indicates** it can do, what it
**actually did** under one controlled execution, and what your **security
policy** permits, then gives you one plain recommendation:

```text
NO ISSUES FOUND   |   REVIEW BEFORE USE   |   DO NOT USE
```

SkillShield never labels a skill "malicious" — it reports evidence-based
findings and lets you decide. See `SECURITY_LIMITATIONS.md` for exactly what
"controlled execution" does and does not guarantee, and
`docs/product-spec.md` for the full product definition.

This repository also contains an earlier, separate milestone —
`src/agentic_conformance/`, the "Agentic Skill Security & Conformance
Layer" (see `docs/spec.md`/`docs/plan.md`) — which SkillShield reuses one
piece of (the open capability-vocabulary registry) but is otherwise
independent of. The rest of this README is about SkillShield.

## Install

Requires Python 3.10+. This project uses [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

This installs both packages in the repo (`agentic-skill-conformance`,
which SkillShield lives inside as `src/skillshield/`) in editable mode,
plus `pytest`/`ruff` for development. No other runtime dependencies exist
for either package.

Without `uv`, an editable `pip install -e .` from the repo root works too.

## Launch

### Command line

```bash
skillshield scan ./my-downloaded-skill        # a local directory
skillshield scan ./my-downloaded-skill.zip     # a ZIP archive — same result
```

Options:

| Flag | Meaning |
| --- | --- |
| `--policy PATH` | Use a custom security policy JSON file instead of the built-in conservative default (see `docs/conformance-rules.md` §10 for the format). |
| `--timeout SECONDS` | Controlled-execution wall-clock timeout (default `10.0`). |
| `--json` | Print the full assessment as JSON instead of the human-readable report. |

Exit code: `0` for any completed assessment (including a `DO NOT USE`
recommendation — that's a successful analysis outcome, not a tool
failure), `2` if the skill couldn't even be ingested (malformed/unsafe
archive, invalid structure, bad path), `3` if `--policy` names a malformed
policy file.

### Web UI

```bash
skillshield ui
```

Then open the printed URL (default `http://127.0.0.1:8765/`) in a browser.
Upload a skill ZIP, or (in a Chromium-based browser) select a local skill
folder directly, click **Assess**, and view the recommendation, the D/S/R/P
capability summary, the findings (each with an expandable **View Evidence**
section), and any limitations. `--host`/`--port` override the bind address.

The UI is a thin client: it calls the exact same assessment pipeline as the
CLI and contains no security logic of its own (see
`docs/product-spec.md` §22 and `DECISIONS.md`'s "P5/P6" entries). It is a
local, single-user development tool — no authentication, not meant to be
exposed beyond `127.0.0.1`.

## What a scan actually does

```text
Ingest (directory or ZIP, with path-traversal/archive-safety checks)
  -> Extract the declaration (manifest.json)
  -> Static analysis (AST-based detectors over the skill's .py files)
  -> Controlled execution (a restricted subprocess, observed via an audit hook)
  -> Correlate Declared / Static / Runtime / Policy capability sets
  -> Generate findings (with severity)
  -> Map findings to one recommendation
```

Full details, including the exact severity rules and the
findings-to-recommendation mapping: `docs/conformance-rules.md`. The exact
guarantees (and, more importantly, non-guarantees) of "controlled
execution": `SECURITY_LIMITATIONS.md`. Implementation-time judgment calls
and their rationale: `DECISIONS.md`. Per-milestone implementation reports:
`docs/batch-reports/`.

## Development

```bash
uv run pytest       # full test suite
uv run ruff check .  # lint
```

Test fixtures for every required scenario (clean skill, undeclared
capability, policy violation, static/runtime mismatch, timeout, execution
failure, malformed declaration, malicious/traversal archive) live under
`tests/fixtures/skillshield/` — all first-party, built for this project;
none depend on any external dataset or application.

## Scope

SkillShield's first prototype (milestones P0-P6; see `docs/product-plan.md`)
covers everything above. It deliberately does **not** include: downloading
skills from GitHub/SkillsMP/any marketplace, host-platform integrations
(OpenClaw/Dify/n8n), an LLM-based analyzer, a universal policy language, or
large-scale research evaluation — see `docs/product-spec.md` §30 for the
full non-goals list. `FINAL_REPORT.md` has the complete acceptance-criteria
and definition-of-done verification for the current prototype.
