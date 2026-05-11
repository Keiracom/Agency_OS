"""claude_invoke.py — subprocess wrapper around the `claude` CLI.

Spawns a fresh `claude --no-hooks --print --session-id <uuid>` process for
each invocation (Option B per Drevon PR-B dispatch). Per-call isolation: no
shared state between invocations, no daemon, no tmux infra.

`--no-hooks` is MANDATORY. Without it, PostToolUse/Stop hooks fire inside
the spawned process and recurse into session_store.record_tool_call(),
which would cascade nested turn_logs writes / infinite loops.

Stdin: compressed prompt (str).
Stdout: claude's response (str).
Stderr: captured for error diagnostics.

Exit codes:
    0   success
    !=0 → CalledProcessError raised; caller decides whether to retry / abort.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from uuid import uuid4


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


def invoke(
    prompt: str,
    *,
    timeout_seconds: int = 600,
    claude_bin: str | None = None,
    extra_args: list[str] | None = None,
    runner=subprocess.run,
) -> ClaudeResult:
    """Run `claude --no-hooks --print --session-id <new>` with `prompt` on stdin.

    `runner` is injectable for tests (default: subprocess.run). Tests pass a
    stub that returns CompletedProcess-shaped data without touching the OS.
    """
    binary = _resolve_claude(claude_bin)
    session_id = str(uuid4())
    cmd = [binary, "--no-hooks", "--print", "--session-id", session_id]
    if extra_args:
        cmd.extend(extra_args)
    completed = runner(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return ClaudeResult(
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        returncode=completed.returncode,
        session_id=session_id,
    )
