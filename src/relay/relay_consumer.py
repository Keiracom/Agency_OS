"""
FILE: src/relay/relay_consumer.py
PURPOSE: Single async consumer replacing 7 inotifywait bash watchers
PHASE: Change 1b Phase 2 — Redis BRPOP consumer
DEPENDENCIES:
  - src/relay/redis_relay.py (pop)
  - src/security/inbox_hmac (sign/verify — file-path API; inline dict verify used here)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac as hmac_mod
import json
import logging
import os
import signal
import subprocess
import sys

logger = logging.getLogger(__name__)

# Queue → tmux target mapping
QUEUE_MAP: dict[str, dict] = {
    "relay:inbox:elliot":  {"tmux": "elliottbot:0.0", "type": "inbox"},
    "relay:inbox:aiden":   {"tmux": "aiden:0.0",      "type": "inbox"},
    "relay:inbox:scout":   {"tmux": "scout:0.0",       "type": "inbox"},
    "relay:inbox:max":     {"tmux": "maxbot:0.0",      "type": "inbox"},
    "relay:outbox:atlas":  {"tmux": "elliottbot:0.0",  "type": "clone_outbox", "clone": "ATLAS"},
    "relay:outbox:orion":  {"tmux": "aiden:0.0",       "type": "clone_outbox", "clone": "ORION"},
    "dispatch:atlas":      {"tmux": "atlas:0.0",        "type": "dispatch"},
    "dispatch:orion":      {"tmux": "orion:0.0",        "type": "dispatch"},
}


# ── HMAC (inline dict verify — inbox_hmac.verify() expects a file path) ────────

def _hmac_verify_dict(payload: dict, secret: str) -> tuple[bool, str]:
    """Re-implement the canonical HMAC check from inbox_hmac directly on a dict."""
    stored = payload.get("hmac")
    if not isinstance(stored, str):
        return False, "hmac field missing or not a string (unsigned payload)"
    filtered = {k: v for k, v in payload.items() if k != "hmac"}
    canonical = json.dumps(filtered, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = hmac_mod.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    if not hmac_mod.compare_digest(stored, expected):
        return False, "HMAC mismatch"
    return True, "ok"


# ── Tmux helpers ────────────────────────────────────────────────────────────────

async def _run_tmux(*args: str) -> tuple[int, str]:
    """Run a tmux command asynchronously (non-blocking)."""
    proc = await asyncio.create_subprocess_exec(
        "tmux", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
    return proc.returncode or 0, (stdout or b"").decode()


async def wait_for_prompt(tmux_target: str, max_attempts: int = 30) -> bool:
    """Poll tmux pane until Claude's ❯ prompt appears (up to max_attempts seconds)."""
    for _ in range(max_attempts):
        try:
            _, stdout = await _run_tmux("capture-pane", "-t", tmux_target, "-p")
            if "❯" in stdout:
                return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False


async def inject_into_tmux(tmux_target: str, text: str) -> bool:
    """Send text then C-m as separate keys (proven anti-paste-bracket pattern)."""
    try:
        text = text.replace("\n", " ")
        await _run_tmux("send-keys", "-t", tmux_target, text)
        await asyncio.sleep(0.5)
        await _run_tmux("send-keys", "-t", tmux_target, "C-m")
        return True
    except Exception as exc:
        logger.error("tmux inject failed target=%s: %s", tmux_target, exc)
        return False


# ── Message formatting ──────────────────────────────────────────────────────────

def format_message(payload: dict, queue_type: str, clone_name: str = "") -> str | None:
    msg_type = payload.get("type", "text")

    if queue_type == "inbox":
        sender = str(payload.get("sender", "unknown")).upper()
        if msg_type == "text":
            return f"[TG-{sender}] {payload.get('text', '')}"
        if msg_type == "photo":
            return (
                f"[TG-{sender}] Dave sent a screenshot: "
                f"{payload.get('file_path', '')} — {payload.get('caption', '')}"
            )
        if msg_type == "document":
            return (
                f"[TG-{sender}] Dave sent a file: "
                f"{payload.get('file_path', '')} ({payload.get('file_name', '')})"
            )

    elif queue_type == "dispatch":
        sender = payload.get("from", "unknown")
        return f"[DISPATCH FROM {sender}] {payload.get('brief', 'no brief')}"

    elif queue_type == "clone_outbox":
        return f"[{clone_name}] {payload.get('text', json.dumps(payload))}"

    return None


# ── Per-queue consumer ──────────────────────────────────────────────────────────

async def consume_queue(queue: str, config: dict) -> None:
    from src.relay.redis_relay import pop  # late import — allows module-level compile check

    tmux_target = config["tmux"]
    queue_type = config["type"]
    clone_name = config.get("clone", "")
    hmac_secret = os.environ.get("INBOX_HMAC_SECRET")

    logger.info("Consumer started: %s → %s", queue, tmux_target)

    while True:
        try:
            payload = await pop(queue, timeout=5)
            if payload is None:
                continue

            if queue_type == "dispatch" and hmac_secret:
                ok, reason = _hmac_verify_dict(payload, hmac_secret)
                if not ok:
                    logger.warning("HMAC reject on %s: %s", queue, reason)
                    continue

            text = format_message(payload, queue_type, clone_name)
            if not text:
                logger.warning("Could not format message from %s: %s", queue, payload)
                continue

            prompt_ready = await wait_for_prompt(tmux_target)
            if not prompt_ready:
                logger.warning("Prompt not ready on %s after 30s, injecting anyway", tmux_target)

            await inject_into_tmux(tmux_target, text)
            logger.info("Injected into %s from %s: %.80s", tmux_target, queue, text)

        except Exception as exc:
            logger.error("Consumer error on %s: %s", queue, exc)
            await asyncio.sleep(2)


# ── Entry point ─────────────────────────────────────────────────────────────────

def _file_watchers_active() -> bool:
    """Check if inotifywait relay watchers are still running (Phase 1 overlap guard)."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "inotifywait.*telegram-relay"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[relay-consumer] %(asctime)s %(levelname)s %(message)s",
    )

    # Guard: refuse to start if file-based watchers are still active (double-injection)
    if _file_watchers_active():
        logger.error(
            "inotifywait relay watchers still active — refusing to start. "
            "Disable file watchers before enabling Redis consumer (Phase 3)."
        )
        sys.exit(1)

    active: dict[str, dict] = {}
    for queue, config in QUEUE_MAP.items():
        session = config["tmux"].split(":")[0]
        result = subprocess.run(["tmux", "has-session", "-t", session], capture_output=True)
        if result.returncode == 0:
            active[queue] = config
            logger.info("Queue %s → %s (session exists)", queue, config["tmux"])
        else:
            logger.info("Queue %s SKIPPED (session %s not found)", queue, session)

    if not active:
        logger.warning("No active tmux sessions found. Exiting.")
        return

    tasks = [asyncio.create_task(consume_queue(q, c)) for q, c in active.items()]
    logger.info("Started %d consumers", len(tasks))

    # Graceful shutdown: cancel tasks on SIGTERM/SIGINT, let in-flight messages drain
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: [t.cancel() for t in tasks])

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Shutdown signal received — consumers stopped gracefully")


if __name__ == "__main__":
    asyncio.run(main())
