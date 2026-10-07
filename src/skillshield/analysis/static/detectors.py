"""AST-based static capability detectors (docs/product-spec.md §14).

Each detector inspects a single parsed source file (an ``ast.Module``) and
yields ``Hit`` tuples for syntactic patterns that indicate a capability may
be used. This is pure source inspection: nothing here imports, executes, or
``exec``'s any part of the analyzed code.

Static evidence means "the source code indicates this capability may be
used" -- never that it definitely occurs. These detectors resolve simple
``import``/``from ... import`` aliasing (so ``import subprocess as sp`` is
still recognized when the code calls ``sp.run(...)``) but do not perform
data-flow analysis: a capability reached only through indirection the
detector doesn't recognize (``getattr(os, "system")(...)``, a module
reference stored in a variable, dynamic ``importlib.import_module``, string
`eval`/`exec`, etc.) is a documented coverage gap, not a bug -- see
docs/conformance-rules.md §8.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

#: Resolved dotted call name -> (capability, detector_name, operation).
_CALL_PATTERNS: dict[str, tuple[str, str, str]] = {
    # filesystem.read
    "os.listdir": ("filesystem.read", "stdlib-call", "os.listdir"),
    "os.scandir": ("filesystem.read", "stdlib-call", "os.scandir"),
    # pathlib.Path.{read,write}_{text,bytes} are handled separately in
    # detect_known_calls via _PATH_CONSTRUCTOR_METHOD_PATTERNS, since they
    # are method calls on a Call result (Path(...).read_text()), not a
    # plain dotted name _dotted_name()/_resolve() can produce.
    # filesystem.write
    "os.remove": ("filesystem.write", "stdlib-call", "os.remove"),
    "os.mkdir": ("filesystem.write", "stdlib-call", "os.mkdir"),
    "os.makedirs": ("filesystem.write", "stdlib-call", "os.makedirs"),
    # network.egress
    "requests.get": ("network.egress", "http-call", "requests.get"),
    "requests.post": ("network.egress", "http-call", "requests.post"),
    "requests.put": ("network.egress", "http-call", "requests.put"),
    "requests.delete": ("network.egress", "http-call", "requests.delete"),
    "httpx.get": ("network.egress", "http-call", "httpx.get"),
    "httpx.post": ("network.egress", "http-call", "httpx.post"),
    "urllib.request.urlopen": ("network.egress", "http-call", "urllib.request.urlopen"),
    "socket.socket": ("network.egress", "socket-call", "socket.socket"),
    # process.execute
    "subprocess.run": ("process.execute", "subprocess-call", "subprocess.run"),
    "subprocess.Popen": ("process.execute", "subprocess-call", "subprocess.Popen"),
    "subprocess.call": ("process.execute", "subprocess-call", "subprocess.call"),
    "subprocess.check_output": ("process.execute", "subprocess-call", "subprocess.check_output"),
    "subprocess.check_call": ("process.execute", "subprocess-call", "subprocess.check_call"),
    "os.system": ("process.execute", "stdlib-call", "os.system"),
    "os.popen": ("process.execute", "stdlib-call", "os.popen"),
}

#: Module name (as written in import/from) -> capability implied merely by importing it.
_IMPORT_PATTERNS: dict[str, tuple[str, str, str]] = {
    "socket": ("network.egress", "import", "import socket"),
    "requests": ("network.egress", "import", "import requests"),
    "httpx": ("network.egress", "import", "import httpx"),
    "urllib.request": ("network.egress", "import", "import urllib.request"),
    "http.client": ("network.egress", "import", "import http.client"),
    "subprocess": ("process.execute", "import", "import subprocess"),
}

_READ_MODES = {None, "r", "rb", "rt"}
_WRITE_MODES = {"w", "wb", "a", "ab", "x"}

_CREDENTIAL_ENV_PATTERNS = ("key", "token", "secret", "password", "credential")
_CREDENTIAL_PATH_PATTERNS = (".env", "credentials.json", "id_rsa")


@dataclass(frozen=True)
class Hit:
    """One detected occurrence of a capability-indicating source pattern."""

    capability: str
    detector: str
    operation: str
    lineno: int


def _build_alias_map(tree: ast.Module) -> dict[str, str]:
    """Map locally-bound names introduced by ``import``/``from ... import``
    to the fully-dotted name they refer to.

    Plain ``import module`` (no ``as``) needs no entry: the bound name
    already equals the attribute-chain root used at call sites.
    """
    alias_map: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    alias_map[alias.asname] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module is None or node.level:
                continue  # relative import -- not resolvable without package context
            for alias in node.names:
                bound = alias.asname or alias.name
                alias_map[bound] = f"{node.module}.{alias.name}"
    return alias_map


def _dotted_name(node: ast.expr) -> str | None:
    """Return the dotted attribute-chain string for a Name/Attribute
    expression, or None if it isn't a plain chain (e.g. a call result)."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        parts.reverse()
        return ".".join(parts)
    return None


def _resolve(dotted: str, alias_map: dict[str, str]) -> str:
    root, _, rest = dotted.partition(".")
    mapped = alias_map.get(root, root)
    return f"{mapped}.{rest}" if rest else mapped


def _import_module_names(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if node.module is None or node.level:
        return []
    return [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]


def detect_imports(tree: ast.Module) -> list[Hit]:
    """Detect capabilities implied merely by importing a module."""
    hits: list[Hit] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for name in _import_module_names(node):
                pattern = _IMPORT_PATTERNS.get(name)
                if pattern is not None:
                    capability, detector, operation = pattern
                    hits.append(Hit(capability, detector, operation, node.lineno))
    return hits


_PATH_CONSTRUCTOR_METHOD_PATTERNS: dict[str, tuple[str, str, str]] = {
    "read_text": ("filesystem.read", "stdlib-call", "Path.read_text"),
    "read_bytes": ("filesystem.read", "stdlib-call", "Path.read_bytes"),
    "write_text": ("filesystem.write", "stdlib-call", "Path.write_text"),
    "write_bytes": ("filesystem.write", "stdlib-call", "Path.write_bytes"),
}


def _is_path_constructor_call(node: ast.expr, alias_map: dict[str, str]) -> bool:
    """True if ``node`` is a call to ``pathlib.Path(...)`` (however imported)."""
    if not isinstance(node, ast.Call):
        return False
    dotted = _dotted_name(node.func)
    if dotted is None:
        return False
    return _resolve(dotted, alias_map) == "pathlib.Path"


def detect_known_calls(tree: ast.Module, alias_map: dict[str, str]) -> list[Hit]:
    """Detect calls matching a known capability-indicating dotted name, an
    os.exec*/os.spawn* family call (too many variants to list by hand), or a
    read/write method called directly on a ``pathlib.Path(...)`` constructor
    result (e.g. ``Path("f").read_text()``) -- the common one-liner form;
    a ``Path`` held in an intermediate variable is a documented coverage gap
    (no data-flow tracking), per docs/conformance-rules.md §8.3."""
    hits: list[Hit] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in _PATH_CONSTRUCTOR_METHOD_PATTERNS
            and _is_path_constructor_call(node.func.value, alias_map)
        ):
            capability, detector, operation = _PATH_CONSTRUCTOR_METHOD_PATTERNS[node.func.attr]
            hits.append(Hit(capability, detector, operation, node.lineno))
            continue
        dotted = _dotted_name(node.func)
        if dotted is None:
            continue
        resolved = _resolve(dotted, alias_map)
        pattern = _CALL_PATTERNS.get(resolved)
        if pattern is not None:
            capability, detector, operation = pattern
            hits.append(Hit(capability, detector, operation, node.lineno))
            continue
        root = resolved.split(".")[0]
        tail = resolved.split(".")[-1]
        if root == "os" and tail.startswith(("exec", "spawn")):
            hits.append(Hit("process.execute", "stdlib-call", resolved, node.lineno))
    return hits


def _string_constant(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _open_mode(node: ast.Call) -> str | None:
    """Best-effort extraction of the literal mode string passed to open().

    Returns None (meaning: could not determine statically) when the mode
    argument is anything other than a string literal, or absent -- callers
    distinguish "no mode argument" (default read) from "unresolvable mode"
    by checking argument presence separately.
    """
    if len(node.args) >= 2:
        return _string_constant(node.args[1])
    for kw in node.keywords:
        if kw.arg == "mode":
            return _string_constant(kw.value)
    return None


def _has_mode_argument(node: ast.Call) -> bool:
    if len(node.args) >= 2:
        return True
    return any(kw.arg == "mode" for kw in node.keywords)


def detect_open_calls(tree: ast.Module) -> list[Hit]:
    """Detect filesystem.read / filesystem.write / credential.read from
    builtin open() calls, classified by the (statically-known) mode."""
    hits: list[Hit] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"):
            continue
        if _has_mode_argument(node):
            mode = _open_mode(node)
            if mode is None:
                continue  # dynamic mode -- documented coverage gap
            mode = mode.lower()
            if mode.startswith(("w", "a", "x")):
                hits.append(Hit("filesystem.write", "builtin-call", f"open(mode={mode!r})", node.lineno))
            elif mode.startswith("r"):
                hits.append(Hit("filesystem.read", "builtin-call", f"open(mode={mode!r})", node.lineno))
        else:
            hits.append(Hit("filesystem.read", "builtin-call", "open()", node.lineno))

        path_literal = _string_constant(node.args[0]) if node.args else None
        if path_literal is not None:
            lowered = path_literal.lower()
            if any(pattern in lowered for pattern in _CREDENTIAL_PATH_PATTERNS):
                hits.append(
                    Hit("credential.read", "path-literal", f"open({path_literal!r})", node.lineno)
                )
    return hits


def detect_credential_env_access(tree: ast.Module, alias_map: dict[str, str]) -> list[Hit]:
    """Detect os.environ.get(...)/os.getenv(...)/os.environ[...] reads whose
    literal key looks like a credential name."""
    hits: list[Hit] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            dotted = _dotted_name(node.func)
            if dotted is None:
                continue
            resolved = _resolve(dotted, alias_map)
            if resolved in ("os.getenv", "os.environ.get"):
                key = _string_constant(node.args[0]) if node.args else None
                if key and any(p in key.lower() for p in _CREDENTIAL_ENV_PATTERNS):
                    hits.append(Hit("credential.read", "env-call", f"{resolved}({key!r})", node.lineno))
        elif isinstance(node, ast.Subscript):
            dotted = _dotted_name(node.value)
            if dotted is None:
                continue
            resolved = _resolve(dotted, alias_map)
            if resolved == "os.environ":
                key = _string_constant(node.slice)
                if key and any(p in key.lower() for p in _CREDENTIAL_ENV_PATTERNS):
                    hits.append(
                        Hit("credential.read", "env-subscript", f"os.environ[{key!r}]", node.lineno)
                    )
    return hits


def run_all_detectors(tree: ast.Module) -> list[Hit]:
    """Run every detector over one parsed file and return all hits."""
    alias_map = _build_alias_map(tree)
    hits: list[Hit] = []
    hits.extend(detect_imports(tree))
    hits.extend(detect_known_calls(tree, alias_map))
    hits.extend(detect_open_calls(tree))
    hits.extend(detect_credential_env_access(tree, alias_map))
    return hits
