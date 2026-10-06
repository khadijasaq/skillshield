"""Runtime monitoring: ExecutionHandle observations -> canonical SecurityEvent
(second milestone, Phase 4).

```text
ExecutionHandle.observations   (raw, native-shaped — Phase 3)
        v
observations_to_native_events()   (adds skill_id/invocation_id)
        v
ProductAdapter.translate_event()   (existing, unmodified — testbed-specific
                                     mapping lives in the adapter, not here)
        v
ProductAdapter.observe()            (existing, unmodified — emits through
                                     the existing ConformanceAPI.emit_event)
        v
canonical SecurityEvent list  (R)
```

This module contains no testbed-specific parsing itself — that stays in
`adapters/vuln_agentic_skills_app/adapter.py`'s `translate_event`, per the
architectural boundary. This module only orchestrates: it knows how to get
from "one finished execution" to "events emitted through the existing
core", not what any particular native capability id means.

Coverage is honestly partial, matching what Phase 3's controlled-execution
mechanism can actually observe (see that module's docstring for the full
list of gaps): task read/write, filesystem read/write, and attempted
network calls are observed because `_runner.py`'s broker mediates all of
them. Process execution via a direct `subprocess`/`os.system` call bypassing
`ctx` entirely, and any activity after a timeout kills the process, are
**not** observed by this mechanism — there is no process-wide watcher
(unlike the real app's `audit_hook.py`), only the ctx-broker interception
itself. This gap is stated here rather than silently absent.
"""

from __future__ import annotations

from typing import Any

from agentic_conformance.core.interfaces.adapter import ProductAdapter
from agentic_conformance.core.models import SecurityEvent
from agentic_conformance.execution.handle import ExecutionHandle


def observations_to_native_events(handle: ExecutionHandle) -> list[dict[str, Any]]:
    """Enrich each raw observation with the `skill_id`/`invocation_id` the
    adapter's `translate_event` needs but the raw observation itself (an
    `_runner.py` log entry) does not carry on its own."""
    return [
        {**observation, "skill_id": handle.skill_id, "invocation_id": handle.invocation_id}
        for observation in handle.observations
    ]


def monitor_and_emit(adapter: ProductAdapter, handle: ExecutionHandle) -> list[SecurityEvent]:
    """Convert every observation from one execution into a canonical
    SecurityEvent and emit it through the existing, unmodified
    `ProductAdapter.observe` -> `ConformanceAPI.emit_event` path.

    Returns the canonical events for direct inspection (e.g. to compute
    `R`), re-translating them purely (no additional side effects) rather
    than reaching into the adapter's internal `ConformanceAPI` reference.
    """
    native_events = observations_to_native_events(handle)
    for native_event in native_events:
        adapter.observe(native_event)
    return [adapter.translate_event(native_event) for native_event in native_events]


def runtime_capability_set(events: list[SecurityEvent]) -> set[str]:
    """The distinct canonical capability identifiers across runtime events — `R`."""
    return {event.action.capability.identifier for event in events}


def invalid_observation_capabilities(handle: ExecutionHandle) -> set[str]:
    """Native capability ids observed that this adapter cannot normalize.

    Returned so a caller can report an "invalid event" condition honestly,
    rather than letting `ProductAdapter.observe` raise mid-loop and lose
    every event already processed. Empty for any execution whose
    observations are entirely within the mapped native vocabulary.
    """
    from agentic_conformance.adapters.vuln_agentic_skills_app.mapping import (
        is_mapped_native_capability,
    )

    return {
        observation["capability"]
        for observation in handle.observations
        if not is_mapped_native_capability(observation.get("capability", ""))
    }
