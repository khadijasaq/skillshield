# SkillShield Security Limitations

This document states plainly what SkillShield's controlled-execution
mechanism does and does not guarantee, per `docs/product-spec.md` §21 and
the project's honesty requirements. It describes what was actually built
(`src/skillshield/execution/`), not an aspirational design. If anything
here changes in a later batch, this file is updated alongside it, not
rewritten from scratch.

## What this is

**A restricted subprocess with an audit-hook observer. Not a secure
sandbox.**

SkillShield runs a skill's declared entrypoint by spawning a plain CPython
subprocess (`skillshield.execution.harness`) with a stripped-down
environment, a copy of the skill's files in a scratch directory, and a
wall-clock timeout. It observes the subprocess's behavior using
`sys.addaudithook` (PEP 578) to detect filesystem, network, and
process-execution operations as they happen. There is no seccomp filter,
no Linux namespace, no container, no virtual machine, and no OS-level
permission restriction of any kind beyond what the executing OS user
account already has. If the account running SkillShield can read a file,
write a file, or reach a network endpoint, a skill executed by SkillShield
can too -- SkillShield only *observes and reports* that it did, after the
fact. It does not prevent it.

## Guarantee-by-guarantee

### Process isolation

**Not guaranteed.** The skill runs as an ordinary child process of the
SkillShield process, under the same OS user account, on the same machine,
sharing the same kernel. There is no container, VM, or namespace boundary.

### Filesystem access

**Not restricted. Only observed, and only through CPython's own
audit-hook-covered APIs.** The skill's own files are copied into a fresh
temporary directory before execution (so the *original* ingested artifact
can't be mutated by the skill), and the subprocess's working directory is
set there -- but the skill process still has the full filesystem
permissions of the OS user account. It can read or write any file that
account can access, anywhere on the filesystem, not just inside the
scratch directory. SkillShield's "filesystem.read"/"filesystem.write"
runtime evidence only covers operations that go through audited Python-
level APIs (`open`, `os.remove`, `os.mkdir`, `os.listdir`, etc.) -- a
skill using a compiled extension module, `ctypes`, or a direct syscall
wrapper that bypasses these APIs would not be observed at all. Import
machinery's own `.pyc` bytecode-cache reads/writes and the entrypoint
module's own source read are filtered out of the evidence as bootstrap
noise, not because they're blocked.

### Network access

**Not restricted. Only observed, and only for `socket.connect`.** A skill
can make real outbound network connections; nothing in SkillShield blocks
or proxies them. Observation is limited to the `socket.connect` audit
event, which (confirmed empirically) fires on the connection *attempt*
regardless of whether it succeeds -- so a blocked/refused/timed-out
connection still shows up as `network.egress` evidence. Any library that
performs networking through a path other than Python's `socket` module
(a compiled extension with its own network stack, for example) would not
be observed.

### Environment variables

**Partially stripped before the skill runs; reads are not observable at
all.** `sandbox.py` passes the subprocess a small allow-list of
environment variables (`PATH`, `SYSTEMROOT`, `SYSTEMDRIVE`, `TEMP`, `TMP`,
`PATHEXT`, `PYTHONIOENCODING`) instead of the operator's full environment,
which reduces (does not eliminate) incidental exposure of secrets that
might otherwise sit in the parent shell's environment. **Confirmed
empirically on this CPython version: `os.environ.get(...)` and
`os.getenv(...)` raise no audit event whatsoever.** SkillShield's runtime
observation is therefore structurally blind to a skill reading whatever
environment variables *are* present -- there is no way, with this
mechanism, to produce runtime evidence of an environment-variable read.
(Static analysis's `credential.read` detector can flag suspicious-looking
`os.getenv("...KEY...")`-style calls from source code, per
`docs/conformance-rules.md` §8.1 -- that is static evidence only, "may
read", not runtime proof that it did.)

### Credentials

**Not protected beyond the environment-variable stripping above.** A skill
can read any credential file the OS user account can read (SSH keys,
cloud CLI config, browser-stored secrets, etc.) exactly as the operator's
own account could. SkillShield neither detects nor prevents this at
runtime beyond the generic `filesystem.read` audit coverage described
above.

### Child processes

**Not restricted. Direct `subprocess.Popen` calls are observed; deeper
descendants are not specifically tracked.** `process.execute` evidence is
produced for `subprocess.Popen`/`subprocess.run`/`os.system`/`os.exec*`/
`os.spawn*` calls made directly by the skill's own Python code. A child
process the skill spawns is not itself monitored by an audit hook (audit
hooks are per-interpreter, not inherited across a process boundary the way
described here) -- if a skill's subprocess in turn does something
security-relevant, that specific action is not observed.

### Resource usage (CPU / memory)

**Not limited at all.** There is no CPU quota and no memory limit. A skill
that allocates unbounded memory or burns CPU will do so for up to the
configured timeout, consuming real system resources on the host running
SkillShield.

### Timeout

**Enforced, wall-clock only.** `sandbox.py` enforces a configurable
wall-clock timeout (default used in tests: a few seconds; callers choose
the value) via `subprocess.communicate(timeout=...)`. This is the only
resource-style limit in the current implementation.

### Termination

**Best-effort, not guaranteed.** On timeout, SkillShield attempts to kill
the entire process tree it spawned: `taskkill /F /T /PID <pid>` on
Windows, `os.killpg(getpgid(pid), SIGKILL)` on POSIX (the child is started
in its own process group specifically to make this possible). Both
mechanisms can fail to reach every descendant in pathological cases (a
process that detaches from its process group, a grandchild spawned after
the kill signal was already in flight, platform-specific scheduling
races). After a kill attempt, SkillShield reaps the process with a bounded
wait and reports `TIMEOUT` regardless of whether the tree was fully
cleaned up -- it does not re-verify system-wide that no descendant
survived.

### Runtime evidence collection

**Partial evidence is preserved even on a killed or crashed run.** The
harness opens its events file and installs the audit hook as the very
first things it does, and flushes after every event, so whatever happened
before a timeout/kill is still readable afterward. This is useful
evidence, not a safety guarantee -- a skill killed one instruction before
doing something undeclared would simply not have that instruction
observed.

## What SkillShield's `R` (runtime-observed capabilities) does and does not mean

- **Presence in `R` is real, specific evidence**: the audited event
  actually happened during this one controlled execution.
- **Absence from `R` is not proof of anything.** The exercised run may
  simply not have reached a given code path (different input, a
  conditional branch, a dependency that silently failed, etc.). Per
  `docs/product-spec.md` §15/§31, SkillShield's findings and explanations
  never claim runtime absence proves a capability can never occur.
- **`R` can miss real behavior that happens through unaudited APIs**
  (compiled extensions, direct syscalls, environment-variable reads, a
  spawned child process's own further actions).
- **`R` cannot be defeated by a skill simply declaring more capabilities
  than it uses** -- it only reports what was actually observed, regardless
  of what the manifest claims.

## Summary table

| Dimension | Prevented? | Observed? |
| --- | --- | --- |
| Process isolation | No | N/A |
| Filesystem access | No | Partially (audited Python APIs only) |
| Network access | No | Partially (`socket.connect` only) |
| Environment variables | Partially (allow-list on launch) | No (no audit event exists for reads) |
| Credentials | No | Only via generic filesystem read coverage |
| Child processes | No | Direct `Popen`/`exec`/`spawn` calls only |
| CPU / memory | No | No |
| Wall-clock timeout | Yes | N/A |
| Termination on timeout | Best-effort | N/A |
