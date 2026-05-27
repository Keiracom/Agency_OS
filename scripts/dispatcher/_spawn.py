"""Spawn / no-op-log wrapper around the composer.

Per PR #1140 §6 staging:
  Stage 1: dispatcher writes a no-op log entry (the composed prompt
           preview) instead of actually spawning. Proves file-claim
           race-safety + tmux-watcher coexistence without behaviour change.
  Stage 2: dispatcher actually spawns `claude` with the composed prompt.

Mode is selected via DISPATCHER_MODE env var; default = "noop" so a fresh
install can be safely enabled before the operator verifies behaviour.

Composer ABI: imports compose_initial_prompt from src.relay.spawn_composer
(Agency_OS-eh56). The composer is DI-friendly (takes db + repo_root + ...).
This module is the dispatcher's call-site that resolves the protocol to a
concrete subprocess + DB.

bd: Agency_OS-8416
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from src.relay.spawn_composer import compose_initial_prompt

log = logging.getLogger(__name__)

NOOP_LOG_PREVIEW_CHARS = 200

MODE_NOOP = "noop"
MODE_SPAWN = "spawn"


def handle_envelope(
    *,
    callsign: str,
    db: Any,
    repo_root: Path,
    inbox_root: Path,
    mode: str,
    claude_bin: str | None = None,
    resume_context: Mapping[str, Any] | None = None,
    popen: Any = subprocess.Popen,
    clock: Any = time,
) -> dict[str, Any]:
    """Compose the initial prompt + log (noop) or spawn `claude` (spawn).

    Returns a result dict with at least `{mode, prompt_chars}`. On the spawn
    path, includes `pid`. Tests inject `popen` to avoid launching real
    subprocesses.
    """
    prompt = compose_initial_prompt(
        callsign,
        db=db,
        repo_root=repo_root,
        inbox_root=inbox_root,
        now=int(clock.time()),
        resume_context=resume_context,
    )
    result: dict[str, Any] = {"mode": mode, "prompt_chars": len(prompt)}

    if mode == MODE_NOOP:
        log.info(
            "noop-spawn callsign=%s resume=%s prompt_preview=%r",
            callsign,
            resume_context is not None,
            prompt[:NOOP_LOG_PREVIEW_CHARS],
        )
        return result

    if mode != MODE_SPAWN:
        log.warning("unknown DISPATCHER_MODE=%r — falling through to noop", mode)
        result["mode"] = MODE_NOOP
        return result

    binary = claude_bin or shutil.which("claude")
    if not binary:
        log.error("spawn-mode requested but no `claude` binary found; falling back to noop")
        result["mode"] = MODE_NOOP
        return result

    proc = popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # Write the composed prompt to stdin + close. Caller (dispatcher_main)
    # decides whether to wait() or fire-and-forget.
    if proc.stdin is not None:
        proc.stdin.write(prompt)
        proc.stdin.close()
    result["pid"] = getattr(proc, "pid", None)
    log.info("spawned callsign=%s pid=%s", callsign, result["pid"])
    return result
