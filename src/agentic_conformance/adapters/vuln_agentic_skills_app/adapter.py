"""Adapter for the real `vuln-agentic-skills-app` testbed (docs/downloaded-skill-assessment-plan.md Phase 1).

Testbed inspection (Batch 1, Phase 1) against
https://github.com/khadijasaq/vuln-agentic-skills-app (commit
249fe28d9d32a46a3d676540e9a47e1ac29680b6) found:

* Every skill is a directory holding exactly two files: `manifest.json`
  (the claim) and `skill.py` (the code) — confirmed across
  `backend/skills/catalogue/task_summary/` and every
  `vulnerabilities/ast0*/skill/<id>/` directory.
* `manifest.json` has the shape (see `app/skills/manifest.py`):
  `schema_version, id, name, version, author, category, description,
  invocation{when_to_use, parameters}, capabilities[{id, scope, reason}],
  dependencies[{name, version, source, integrity, publisher, reason}],
  entrypoint` (e.g. `"skill.py:run"`).
* There is no top-level integrity/checksum field on the manifest itself
  (only on individual `dependencies[]` entries, which this skill has
  none of) — so, exactly as `docs/downloaded-skill-assessment-spec.md`
  §4.2 anticipates, `integrity` is populated with an explicit placeholder
  rather than a fabricated value.
* The actual runtime entry point is a plain Python function:
  `skill.py` defines `run(ctx, params) -> SkillResult`, called by the
  real app's `SkillHost.invoke()` (`backend/app/skills/host.py`). `ctx` is
  a `SkillContext` exposing `ctx.tasks`, `ctx.files`, `ctx.net`, `ctx.env`
  brokers (`backend/app/skills/context.py`) — this is the actual
  entrypoint Phase 3's controlled execution invokes; nothing here invents
  a shell command or alternate entry point.

Adapter responsibility boundary: this module is the only place in the
codebase that knows any of the above. `core/` never sees a manifest dict,
a skill directory path, or a native capability id — only the canonical
`Skill`/`Capability`/`SecurityEvent` objects produced here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentic_conformance.adapters.vuln_agentic_skills_app.mapping import (
    normalize_capability_name,
)
from agentic_conformance.core.interfaces.adapter import ProductAdapter
from agentic_conformance.core.models import (
    Action,
    Actor,
    Capability,
    Declaration,
    SecurityEvent,
    Skill,
    Target,
)

#: Source identifier recorded on every canonical Skill this adapter produces.
SOURCE_ID = "vuln_agentic_skills_app"

#: Placeholder used when the real manifest provides no integrity/checksum
#: field, per docs/downloaded-skill-assessment-spec.md §4.2 ("an explicit
#: placeholder when none exists, not a fabricated value").
NO_INTEGRITY_PLACEHOLDER = "unknown"


def load_manifest(skill_dir: Path) -> dict[str, Any]:
    """Read and parse one skill's real `manifest.json`.

    In: the skill's directory (e.g. `.../skill/task_insights/`).
    Out: the parsed manifest as a plain dict — still a native, unvalidated
    representation; translation into canonical form happens in
    `VulnAgenticSkillsAppAdapter.translate_skill`.
    """
    manifest_path = Path(skill_dir) / "manifest.json"
    with manifest_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def resolve_entrypoint(skill_dir: Path, manifest: dict[str, Any]) -> tuple[Path, str]:
    """Resolve the real `entrypoint` field (e.g. `"skill.py:run"`) to a (file, attr) pair.

    This is the actual runtime entry point discovered during testbed
    inspection — used by Phase 3's controlled execution to load and call
    the real skill code, never an invented command.
    """
    entrypoint = manifest["entrypoint"]
    filename, _, attribute = entrypoint.partition(":")
    return Path(skill_dir) / filename, attribute


class VulnAgenticSkillsAppAdapter(ProductAdapter):
    """Adapter for real skills from `vuln-agentic-skills-app`.

    Architecturally identical in role to `adapters/reference_app`'s
    `ReferenceAppAdapter` (translation + integration only); used here as an
    architectural reference, not as a source of testbed-specific
    assumptions — this adapter's capability mapping and manifest shape are
    independently derived from inspecting the real application (see
    `mapping.py` and the module docstring above), not copied from the
    reference adapter.
    """

    def translate_skill(self, native_skill: Path) -> Skill:
        """Translate one real skill directory into a canonical `Skill`.

        `native_skill` is the skill's directory, e.g.
        `.../vulnerabilities/ast04-insecure-metadata/skill/task_insights`.
        """
        skill_dir = Path(native_skill)
        manifest = load_manifest(skill_dir)

        declared = tuple(
            self.normalize_capability(declaration["id"])
            for declaration in manifest.get("capabilities", [])
        )
        dependencies = tuple(
            dependency.get("name", "") for dependency in manifest.get("dependencies", [])
        )
        invocation = manifest.get("invocation", {})

        return Skill(
            skill_id=manifest["id"],
            name=manifest["name"],
            version=manifest["version"],
            description=manifest["description"],
            source=SOURCE_ID,
            integrity=NO_INTEGRITY_PLACEHOLDER,
            declaration=Declaration(declared_capabilities=declared),
            dependencies=dependencies,
            context={
                "category": manifest.get("category", ""),
                "author": manifest.get("author", ""),
                "when_to_use": invocation.get("when_to_use", ""),
                "entrypoint": manifest.get("entrypoint", ""),
            },
        )

    def normalize_capability(self, native_capability: Any) -> Capability:
        return Capability(identifier=normalize_capability_name(native_capability))

    def translate_event(self, native_event: dict[str, Any]) -> SecurityEvent:
        """Translate one raw runtime observation into a canonical `SecurityEvent`.

        `native_event` is a plain dict produced by this milestone's
        controlled-execution/runtime-monitoring layer (Phases 3–4), shaped
        after the real app's own `Observation` record
        (`backend/app/monitor/observations.py`): `capability`, `resource`,
        `detail`, `outcome`, `source`, `ts`, `seq`, `invocation_id` — plus
        `skill_id`, added by the runtime-monitoring layer (the real
        `Observation` model has no `skill_id` field; one notebook belongs
        to exactly one invocation, so the orchestrating layer that started
        that invocation is what knows which skill it was).
        """
        capability = self.normalize_capability(native_event["capability"])
        detail = native_event.get("detail", {})
        operation = detail.get("operation") or native_event["capability"]

        return SecurityEvent(
            event_id=f"obs-{native_event['invocation_id']}-{native_event['seq']}",
            timestamp=native_event["ts"],
            event_type=capability.identifier,
            context={
                "skill_id": native_event["skill_id"],
                "invocation_id": native_event["invocation_id"],
                "outcome": native_event.get("outcome", "ok"),
                "source": native_event.get("source", "broker"),
            },
            actor=Actor(type="skill", id=native_event["skill_id"]),
            action=Action(capability=capability, operation=str(operation)),
            target=Target(
                type="resource", identifier=str(native_event.get("resource", "unknown"))
            ),
        )
