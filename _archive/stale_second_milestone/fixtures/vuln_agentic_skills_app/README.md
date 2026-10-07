# Fixture provenance — `vuln-agentic-skills-app`

The files under `task_insights/` (`manifest.json`, `skill.py`) are **verbatim,
byte-for-byte copies** of a real skill from the actual testbed application:

```text
Repository: https://github.com/khadijasaq/vuln-agentic-skills-app
Commit:     249fe28d9d32a46a3d676540e9a47e1ac29680b6 (main, 2026-09-13)
Original path: vulnerabilities/ast04-insecure-metadata/skill/task_insights/
```

This is the "insecure metadata" (AST04) demonstration skill, nicknamed "the
lying skill" in the testbed's own documentation: its manifest declares only
`task.read`, but its (real, unmodified) code also performs a file read
(`fs.read`) and a network call (`net.outbound`) — neither declared. This is
not a contrived or fabricated scenario; it is the testbed's own intentional
design, used here to provide genuine, non-fabricated real-data evidence for
Batch 1 (Phases 1–4) and for later phases' declaration/runtime comparison.

These files are vendored (rather than fetched live from GitHub during test
runs) purely so `uv run pytest` is deterministic and does not depend on
network access or on an external clone's filesystem path. Nothing in their
content has been altered. A live clone of the same repository was also used
during Batch 1 implementation to inspect the testbed's actual structure
before writing any adapter code (see Batch 1 report).

## Batch 2 additions

Two more real skills were vendored for Phase 8's six required demonstration
cases, from the same repository and commit:

```text
task_summary/   <- backend/skills/catalogue/task_summary/
                   "the honest skill" — declares only task.read and does
                   exactly and only that; used as the benign/ALLOW case.

focus_picker/   <- vulnerabilities/ast03-over-privileged/skill/focus_picker/
                   declares four capabilities (task.read, fs.read, task.write,
                   net.outbound) but only ever calls task.read and fs.read;
                   used to demonstrate a real policy-violation case by
                   applying a deny-effect policy rule to its real observed
                   behavior (not by altering what the skill does).
```

All six real skills in the upstream testbed
(`task_summary`, `standup_sync`, `time_budget`, `focus_picker`,
`task_insights`, `team_rules`) were inspected (not vendored unless listed
above) during Phase 5 while searching for a real `R - S` (static/runtime
mismatch) case — see the Batch 2 report for that investigation's result.
