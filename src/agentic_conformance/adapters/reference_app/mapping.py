"""Native-to-canonical capability mapping for the reference application.

docs/spec.md §7.2 gives this normalization as its own example:

    HTTP request / requests.get() / fetch() / network tool invocation
        -> network.egress

This mapping is specific to the reference application's native naming and
must never be imported by core/.
"""

from __future__ import annotations

_CAPABILITY_MAP: dict[str, str] = {
    "http_request": "network.egress",
    "requests.get": "network.egress",
    "fetch": "network.egress",
    "network_tool": "network.egress",
    "read_task": "task.read",
    "write_file": "filesystem.write",
    "execute_process": "process.execute",
    "read_credential": "credential.read",
}


def normalize_capability_name(native_name: str) -> str:
    """Normalize a reference-application-native capability name to a canonical identifier."""
    try:
        return _CAPABILITY_MAP[native_name]
    except KeyError as exc:
        raise ValueError(f"Unmapped native capability: {native_name!r}") from exc
