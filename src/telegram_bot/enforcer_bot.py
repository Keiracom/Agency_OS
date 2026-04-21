#!/usr/bin/env python3
"""Enforcer Bot — lightweight governance enforcement daemon.

Reads Telegram group messages, checks against 5 pilot rules via gpt-4o-mini,
interjects on violations. NOT a Claude Code session — stateless per-check.
"""

import asyncio
import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("enforcer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

# Config
BOT_TOKEN = os.environ.get("ENFORCER_BOT_TOKEN", "")
GROUP_CHAT_ID = os.environ.get("ENFORCER_GROUP_CHAT_ID", "-1003926592540")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
CHECK_MODEL = "gpt-4o-mini"

# Sliding window of recent messages for context
MAX_WINDOW = 20
message_window: deque = deque(maxlen=MAX_WINDOW)

# Rate limit: don't re-flag same rule within 5 minutes
last_flag_times: dict[str, float] = {}
FLAG_COOLDOWN_SECONDS = 300

RULES_PROMPT = """You are a governance enforcement bot for a multi-agent development team.

You monitor group chat messages between two AI agents (Elliot and Aiden) and their human manager (Dave).

CHECK these 5 rules against the CURRENT MESSAGE in context of the RECENT MESSAGES:

Rule 1 — CONCUR-BEFORE-SUMMARY: If the current message is a bot addressing Dave with a summary, recommendation, or decision (look for "Dave —", "Dave,", "your call", "here's the plan", "here's what"), check if the OTHER bot posted explicit concurrence ("concur", "concur confirmed", "CONCUR") in recent messages for the same topic. Missing concurrence = VIOLATION.

Rule 2 — STEP-0-BEFORE-EXECUTION: If the current message shows execution starting (mentions committing, pushing, deploying, triggering flows, creating PRs), check if "Step 0" or "RESTATE" was posted earlier for this directive. Missing Step 0 = VIOLATION.

Rule 3 — COMPLETION-REQUIRES-VERIFICATION: If the current message claims task completion ("complete", "done", "all stores written", "4-store save complete"), check if verification evidence was posted (terminal output, SQL results, test output, commit hashes). Claim without evidence = VIOLATION.

Rule 4 — NO-UNREVIEWED-MAIN-PUSH: If the current message mentions pushing directly to main without mentioning PR review or peer approval, flag as WARNING (not hard violation).

Rule 5 — SHARED-FILE-CLAIM: If the current message mentions editing memory_listener.py, chat_bot.py, store.py, listener_discernment.py, or any CLAUDE.md file, check if "[CLAIM:" was posted. Missing claim = VIOLATION.

RESPOND WITH ONLY THIS JSON:
{
  "violation": true/false,
  "rule_number": N or null,
  "rule_name": "name" or null,
  "detail": "specific issue" or null,
  "should_have": "what should have happened" or null
}

If NO violation, return {"violation": false, "rule_number": null, "rule_name": null, "detail": null, "should_have": null}

IMPORTANT: Only flag CLEAR violations. If unsure, return no violation. False positives are worse than false negatives.
Do NOT flag Dave's messages — he is not subject to bot rules.
Do NOT flag messages that are clearly part of peer discussion (not Dave-facing).
"""

# Trigger patterns that warrant a check
TRIGGER_PATTERNS = [
    "dave —", "dave,", "your call", "here's the plan", "here's what",
    "commit", "pushed", "pr #", "merged", "deployed", "triggered",
    "complete", "done", "all stores written", "4-store",
    "git push origin main",
    "memory_listener.py", "chat_bot.py", "store.py", "listener_discernment.py", "claude.md",
]


def should_check(text: str) -> bool:
    """Pre-filter: only check messages matching trigger patterns."""
    lower = text.lower()
    return any(p in lower for p in TRIGGER_PATTERNS)


def is_bot_message(message: dict) -> bool:
    """Check if message is from a bot (not Dave)."""
    sender = message.get("from", {})
    return sender.get("is_bot", False) or "bot" in sender.get("username", "").lower()


async def check_with_llm(current_msg: str, recent_msgs: list[str]) -> dict | None:
    """Call gpt-4o-mini to check for rule violations."""
    if not OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY — skipping check")
        return None

    user_content = json.dumps({
        "current_message": current_msg,
        "recent_messages": recent_msgs[-MAX_WINDOW:],
    }, ensure_ascii=False)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": CHECK_MODEL,
                    "messages": [
                        {"role": "system", "content": RULES_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 300,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as exc:
        logger.warning("LLM check failed: %s", exc)
        return None


async def send_interjection(text: str) -> None:
    """Post enforcement interjection to the group."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={
                "chat_id": GROUP_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            })
    except Exception as exc:
        logger.error("Failed to send interjection: %s", exc)


async def process_message(message: dict) -> None:
    """Process a single Telegram message."""
    text = message.get("text", "")
    if not text:
        return

    # Add to sliding window
    sender = message.get("from", {})
    sender_name = sender.get("first_name", "Unknown")
    window_entry = f"[{sender_name}]: {text[:500]}"
    message_window.append(window_entry)

    # Only check bot messages
    if not is_bot_message(message):
        return

    # Pre-filter
    if not should_check(text):
        return

    # Rate limit check
    recent_window = list(message_window)
    result = await check_with_llm(text, recent_window)

    if result and result.get("violation"):
        rule_num = result.get("rule_number", "?")
        rule_name = result.get("rule_name", "unknown")
        detail = result.get("detail", "")
        should_have = result.get("should_have", "")

        # Rate limit: don't re-flag same rule within cooldown
        flag_key = f"rule_{rule_num}"
        now = time.time()
        if flag_key in last_flag_times and (now - last_flag_times[flag_key]) < FLAG_COOLDOWN_SECONDS:
            logger.info("Skipping re-flag for rule %s (cooldown)", rule_num)
            return

        last_flag_times[flag_key] = now

        interjection = (
            f"\u26a0\ufe0f [ENFORCER] Rule {rule_num} \u2014 {rule_name}: "
            f"{detail}. {should_have}."
        )
        logger.info("VIOLATION: %s", interjection)
        await send_interjection(interjection)


async def poll_updates() -> None:
    """Long-poll Telegram for new messages."""
    offset = 0
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    logger.info("Enforcer bot starting — polling group %s", GROUP_CHAT_ID)

    while True:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                resp = await client.get(url, params={
                    "offset": offset,
                    "timeout": 30,
                    "allowed_updates": json.dumps(["message"]),
                })
                data = resp.json()

            if not data.get("ok"):
                logger.warning("Telegram API error: %s", data)
                await asyncio.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if msg and str(msg.get("chat", {}).get("id")) == GROUP_CHAT_ID:
                    await process_message(msg)

        except Exception as exc:
            logger.error("Poll error: %s", exc)
            await asyncio.sleep(5)


def main():
    """Entry point."""
    if not BOT_TOKEN:
        logger.error("ENFORCER_BOT_TOKEN not set")
        return
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — enforcement checks disabled")

    asyncio.run(poll_updates())


if __name__ == "__main__":
    main()
