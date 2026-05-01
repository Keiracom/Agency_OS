"""Opus CLI subprocess wrapper for Max COO bot.

Replaces the OpenAI AsyncOpenAI client with Claude Opus via the `claude`
CLI (Max plan, $0/call). Each call spawns a short-lived subprocess:
    claude -p "<prompt>" --model claude-opus-4-6

The subprocess uses Dave's existing ~/.claude/credentials.json OAuth
(Max plan authentication). No API key required.

Public API:
    result = await opus_call(system_prompt, user_message, timeout=30)
    # result: str (response text) or "" on failure

Design:
- Async (asyncio.create_subprocess_exec) — non-blocking
- Timeout protection (default 30s, configurable)
- Never raises — returns "" on any failure (Max must never crash)
- Logs failures for debugging
"""
from __future__ import annotations

import asyncio
import logging
import shutil

logger = logging.getLogger(__name__)

_CLAUDE_BIN = shutil.which("claude") or "/home/elliotbot/.local/bin/claude"
_DEFAULT_MODEL = "claude-opus-4-6"
_DEFAULT_TIMEOUT = 30


async def opus_call(
    system_prompt: str,
    user_message: str,
    *,
    model: str = _DEFAULT_MODEL,
    timeout: float = _DEFAULT_TIMEOUT,
) -> str:
    """Call Claude Opus via CLI subprocess. Returns response text or "" on failure.

    Non-blocking (asyncio subprocess). Never raises.
    """
    prompt = f"{system_prompt}\n\n{user_message}"
    try:
        proc = await asyncio.create_subprocess_exec(
            _CLAUDE_BIN, "-p", prompt, "--model", model,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        if proc.returncode != 0:
            logger.warning(
                "opus_call failed (rc=%s): %s",
                proc.returncode, stderr.decode()[:200],
            )
            return ""
        return stdout.decode().strip()
    except asyncio.TimeoutError:
        logger.warning("opus_call timed out after %ss", timeout)
        if proc:
            proc.kill()
        return ""
    except FileNotFoundError:
        logger.error("claude binary not found at %s", _CLAUDE_BIN)
        return ""
    except Exception as exc:
        logger.error("opus_call unexpected error: %s", exc)
        return ""
