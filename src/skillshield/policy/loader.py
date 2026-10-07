"""Policy loading: a conservative built-in default, or an operator-supplied
policy file (docs/product-spec.md §16; docs/product-plan.md P4).

The project deliberately does not implement a universal policy language --
a policy is just a name plus a permitted-capability set
(``skillshield.core.models.policy.SecurityPolicy``). This module is the only
way to get one other than constructing it directly: a built-in default, or
a small JSON file.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentic_conformance.core.models.capability import supported_capabilities
from skillshield.core.models.policy import SecurityPolicy
from skillshield.policy.errors import PolicyLoadError

#: Deliberately conservative: a skill needs nothing more than reading its
#: own data to run with zero policy findings under the default policy.
#: filesystem.write, network.egress, process.execute, and credential.read
#: are all denied by omission. See docs/conformance-rules.md for the table
#: this mirrors.
_DEFAULT_PERMITTED = frozenset({"task.read", "filesystem.read"})


def default_policy() -> SecurityPolicy:
    """The built-in least-privilege default policy."""
    return SecurityPolicy(name="default", permitted_capabilities=_DEFAULT_PERMITTED)


def _policy_from_mapping(data: object, *, source: str) -> SecurityPolicy:
    if not isinstance(data, dict):
        raise PolicyLoadError(f"{source}: policy file must contain a JSON object")

    name = data.get("name")
    if not isinstance(name, str) or not name:
        raise PolicyLoadError(f"{source}: policy 'name' must be a non-empty string")

    raw_permitted = data.get("permitted_capabilities", [])
    if not isinstance(raw_permitted, list) or not all(isinstance(c, str) for c in raw_permitted):
        raise PolicyLoadError(
            f"{source}: 'permitted_capabilities' must be a list of capability-id strings"
        )

    known = supported_capabilities()
    unsupported = sorted(set(raw_permitted) - known)
    if unsupported:
        raise PolicyLoadError(
            f"{source}: policy permits unsupported capability identifier(s): "
            f"{', '.join(unsupported)}"
        )

    return SecurityPolicy(name=name, permitted_capabilities=frozenset(raw_permitted))


def load_policy(path: str | Path | None) -> SecurityPolicy:
    """Load a ``SecurityPolicy`` from a JSON file, or the built-in default
    when ``path`` is ``None``.

    The expected file shape::

        {"name": "my-policy", "permitted_capabilities": ["task.read", "filesystem.read"]}

    A malformed policy *file* (bad JSON, wrong shape, missing/empty
    ``name``, or a capability identifier SkillShield does not recognize)
    raises ``PolicyLoadError`` immediately -- this is operator configuration,
    not something to silently fall back from or turn into a skill finding.
    """
    if path is None:
        return default_policy()

    policy_path = Path(path)
    source = str(policy_path)
    try:
        raw_text = policy_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyLoadError(f"{source}: could not read policy file ({exc})") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise PolicyLoadError(f"{source}: not valid JSON ({exc})") from exc

    return _policy_from_mapping(data, source=source)
