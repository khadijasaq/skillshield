"""Native-to-canonical capability mapping for `vuln-agentic-skills-app`.

Testbed inspection (Batch 1, Phase 1): the real application's shared
capability vocabulary is defined at
`backend/policy/capability_vocabulary.json` in
https://github.com/khadijasaq/vuln-agentic-skills-app (commit
249fe28d9d32a46a3d676540e9a47e1ac29680b6). It declares exactly seven native
capability identifiers:

    task.read     task.write     fs.read     fs.write
    net.outbound  env.read       proc.spawn

Four of these already have a direct, semantically equivalent canonical
counterpart from the first milestone's initial vocabulary
(`docs/spec.md` §7.2: task.read, network.egress, process.execute,
filesystem.write, credential.read) and are reused as-is:

    task.read    -> task.read          (identical concept)
    fs.write     -> filesystem.write    (identical concept)
    net.outbound -> network.egress      (identical concept)
    proc.spawn   -> process.execute      (identical concept)

Three genuinely have no existing canonical equivalent and are registered as
new canonical capabilities via `register_capability`, per docs/plan.md's
"keep the vocabulary open to future extension" rule and this batch's
instruction to introduce a new capability only when the real testbed
requires it:

    task.write -> task.write    (creating/changing/deleting tasks is a
                                 distinct ability from reading them; the
                                 existing vocabulary has no write-capable
                                 task capability)
    fs.read    -> filesystem.read (the existing vocabulary only has
                                 filesystem.write; reading is a distinct,
                                 narrower ability)
    env.read   -> env.read       (reading a configuration setting is not
                                 the same claim as `credential.read` in the
                                 existing vocabulary — the testbed's own
                                 vocabulary explicitly describes env.read as
                                 "read a configuration setting", and
                                 deliberately blocks real secrets such as
                                 GROQ_API_KEY from ever being reachable
                                 through it; forcing it onto
                                 `credential.read` would overclaim secrecy
                                 semantics that are not actually present)

`proc.spawn` is notable: the testbed's own vocabulary marks it
`"brokered": false` — there is no official channel for it, so observing it
at all means a skill went around the official channel entirely. That
asymmetry (declared-but-never-brokered) belongs to the adapter's knowledge
of the native vocabulary, not to `core/`.
"""

from __future__ import annotations

from agentic_conformance.core.models.capability import register_capability

_CAPABILITY_MAP: dict[str, str] = {
    "task.read": "task.read",
    "task.write": "task.write",
    "fs.read": "filesystem.read",
    "fs.write": "filesystem.write",
    "net.outbound": "network.egress",
    "env.read": "env.read",
    "proc.spawn": "process.execute",
}

#: Canonical identifiers introduced by this adapter because the real
#: testbed vocabulary requires them and no existing identifier matches.
NEW_CANONICAL_CAPABILITIES: tuple[str, ...] = ("task.write", "filesystem.read", "env.read")

for _identifier in NEW_CANONICAL_CAPABILITIES:
    register_capability(_identifier)


def normalize_capability_name(native_name: str) -> str:
    """Normalize a `vuln-agentic-skills-app`-native capability id to a canonical one."""
    try:
        return _CAPABILITY_MAP[native_name]
    except KeyError as exc:
        raise ValueError(
            f"Unmapped native capability from vuln-agentic-skills-app: {native_name!r}"
        ) from exc


def is_mapped_native_capability(native_name: str) -> bool:
    """Whether a native capability id has a known canonical mapping."""
    return native_name in _CAPABILITY_MAP
