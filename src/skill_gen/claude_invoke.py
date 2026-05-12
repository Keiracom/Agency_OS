"""claude_invoke.py — subprocess wrapper around the `claude` CLI.

Spawns a fresh `claude --print --session-id <uuid>` process for each
invocation (Option B per Drevon PR-B dispatch). Per-call isolation: no
shared state between invocations, no daemon, no tmux infra.

Recursion guard via env marker: every spawned process gets
`CLAUDE_CODE_SKILL_GEN=1` in its environment. The session_store hooks
(`.claude/hooks/session_store_posttooluse.sh`, `session_store_stop.sh`)
inspect that variable and early-exit on match — preventing PostToolUse /
Stop hooks from cascading nested turn_logs writes / infinite loops inside
the spawned process.

The earlier design used `claude --no-hooks` but the installed CLI (v2.1.139)
doesn't recognise that flag — the CLI's own hook-skip flag (`--bare`) is
incompatible with OAuth (forces ANTHROPIC_API_KEY auth). The env-marker
guard preserves OAuth/Max-plan billing ($0 incremental) while still
preventing the recursion.

Stdin: compressed prompt (str).
Stdout: claude's response (str).
Stderr: captured for error diagnostics.

Exit codes:
    0   success
    !=0 → caller inspects ClaudeResult.returncode and decides retry/abort.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from uuid import uuid4

RECURSION_GUARD_ENV = "CLAUDE_CODE_SKILL_GEN"


@dataclass(frozen=True)
class ClaudeResult:
    stdout: str
    stderr: str
    returncode: int
    session_id: str


class ClaudeNotInstalled(RuntimeError):
    """Raised when the `claude` CLI isn't on PATH."""


def _resolve_claude(claude_bin: str | None) -> str:
    if claude_bin:
        return claude_bin
    found = shutil.which("claude")
    if not found:
        raise ClaudeNotInstalled("`claude` CLI not on PATH; install Claude Code or set CLAUDE_BIN")
    return found


def _build_env(parent_env: dict[str, str] | None = None) -> dict[str, str]:
    """Merge parent env (defaults to os.environ) with the recursion-guard marker."""
    env = dict(parent_env if parent_env is not None else os.environ)
    env[RECURSION_GUARD_ENV] = "1"
    return env


def invoke(
    prompt: str,
    *,
    timeout_seconds: int = 600,
    claude_bin: str | None = None,
    extra_args: list[str] | None = None,
    runner=subprocess.run,
    parent_env: dict[str, str] | None = None,
) -> ClaudeResult:
    """Run `claude --print --session-id <new>` with `prompt` on stdin.

    `runner` is injectable for tests (default: subprocess.run). Tests pass a
    stub that returns CompletedProcess-shaped data without touching the OS.

    `parent_env` is injectable for tests so they can assert env-merge behaviour
    without depending on the live os.environ. Production callers omit it.
    """
    binary = _resolve_claude(claude_bin)
    session_id = str(uuid4())
    cmd = [binary, "--print", "--session-id", session_id]
    if extra_args:
        cmd.extend(extra_args)
    env = _build_env(parent_env)
    completed = runner(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
        env=env,
    )
    return ClaudeResult(
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        returncode=completed.returncode,
        session_id=session_id,
    )
