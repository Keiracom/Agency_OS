#!/usr/bin/env python3
"""Enforcer Bot — lightweight governance enforcement daemon.

Reads Telegram group messages, checks against 5 pilot rules via gpt-4o-mini,
interjects on violations. NOT a Claude Code session — stateless per-check.
"""

import asyncio
import contextlib
import json
import logging
import os
import re
import time
from collections import deque
from datetime import UTC, datetime

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

# Event-state tracker — persists across messages, resets on restart
# Keys: "last_concur_elliot", "last_concur_aiden", "last_step0", "last_stage0_request"
# Values: {"timestamp": ISO, "text_snippet": first 100 chars, "topic_hint": str}
enforce_events: dict[str, dict] = {}

RULES_PROMPT = """You are a governance enforcement bot for a multi-agent development team.

You monitor group chat messages between two AI agents (Elliot and Aiden) and their human manager (Dave).

CHECK these 7 rules against the CURRENT MESSAGE in context of the RECENT MESSAGES:

Rule 1 — CONCUR-BEFORE-SUMMARY: If the current message is a bot addressing Dave with a summary, recommendation, or decision (look for "Dave —", "Dave,", "your call", "here's the plan", "here's what"), check if the OTHER bot posted explicit concurrence ("concur", "concur confirmed", "CONCUR") in recent messages OR in GOVERNANCE_EVENTS (last_concur_elliot / last_concur_aiden) for the same topic. Missing concurrence = VIOLATION. NOTE: /stage0 gating is handled externally in code — evaluate Rule 1 on its merits and report if concurrence is missing.

Rule 2 — STEP-0-BEFORE-EXECUTION: If the current message shows execution starting (mentions committing, pushing, deploying, triggering flows, creating PRs), check whether EITHER of the following governance signals exists in recent_messages or governance_events for the same topic:
  (a) a Dave-directed Step 0 / RESTATE post, OR
  (b) a dual peer-Step-0 pair — BOTH `[FINAL CONCUR:ELLIOT]` AND `[FINAL CONCUR:AIDEN]` tags present in recent_messages on the same topic (dual-concur governance ratified 2026-04-22).
Having EITHER signal = PASS. Missing BOTH = VIOLATION.
EXCEPTIONS (always PASS, no Step 0 required):
  (i)   PR merge on explicit CEO instruction (Dave posts "merge N" or "merge N + continue")
  (ii)  Rebase performed as peer-review fix (continuation of original dispatch, not new directive)
  (iii) Orchestrator tagging peer replies (acknowledgement, not execution)
  (iv)  CEO removed Step 0 confirmation gate ("no more approvals" or "only merge approvals") — bots post RESTATE for discipline but execution proceeds without Dave-pause. Only PR-merge actions require explicit Dave approval.
  (v)   Task approved via [PROPOSE:<callsign>] + Dave "approve" — execution starts immediately after approval without separate Step 0 post.

Rule 3 — COMPLETION-REQUIRES-VERIFICATION: If the current message claims task completion ("complete", "done", "all stores written", "4-store save complete"), check if verification evidence was posted (terminal output, SQL results, test output, commit hashes). Claim without evidence = VIOLATION.
EXCEPTIONS (always PASS, not a completion claim):
  (i)   Messages starting with '[GOVERNANCE] Gatekeeper DENY' or '[GATEKEEPER-DENY:' — these are automated gate outputs (the opposite of completion claims), not bot assertions of done.
  (ii)  Messages reporting a Gatekeeper allow/deny verdict as test evidence — the verdict IS the verification output.
  (iii) Messages containing 'observe-only' or 'synthetic test' — these are test/verify actions, not real completion claims.

Rule 4 — NO-UNREVIEWED-MAIN-PUSH: If the current message mentions pushing directly to main without mentioning PR review or peer approval, flag as WARNING (not hard violation).

Rule 5 — SHARED-FILE-CLAIM: If the current message mentions editing memory_listener.py, chat_bot.py, store.py, listener_discernment.py, or any CLAUDE.md file, check if "[CLAIM:" was posted. Missing claim = VIOLATION.

Rule 6 — SAVE-CLAIM-REQUIRES-PROOF: If the current message claims a save was completed ("state saved", "4-store save complete", "ceo_memory updated", "MANUAL updated", "Drive mirrored", "daily_log written", "stores written"), check that the message includes SPECIFIC EVIDENCE for EACH store claimed. Evidence means: commit hashes for MANUAL, SQL confirmation for ceo_memory, byte count or success message for Drive mirror, query result for daily_log. A bot saying "all stores written ✓" without showing the actual outputs for each store = VIOLATION. The claim must be backed by verifiable proof in recent messages, not just checkmarks.

Rule 8 — DISPATCH-COORDINATION: If the current message shows a clone dispatch being injected (mentions "dispatched", "injected", "tmux paste", "ATLAS dispatched", "ORION dispatched", or dispatch JSON), check whether a [DISPATCH-PROPOSAL:<callsign>] was posted in recent_messages AND the peer posted [CONCUR] on that proposal BEFORE the dispatch. Dispatching without prior proposal + peer concur = VIOLATION. Exception: if only one bot is active (peer offline/reset), solo dispatch with proposal posted is sufficient.

Rule 9 — DIRECTIVE-INITIATIVE: If the current message is from a bot (ELLIOT or AIDEN) and ends with open-ended agenda-setting phrases directed at Dave — such as "standing by for directive", "ready for next directive", "what's next", "awaiting your call", "what would you like", or any question asking Dave to SET the agenda rather than APPROVE a proposal — flag as VIOLATION. Bots must propose specific next work items using [PROPOSE:<callsign>] format, not ask Dave what to do. Exception: [SESSION-WRAP:<callsign>] is allowed for genuine end-of-session. First violation = warning, second = governance debt log.

Rule 7 — CLONE-DIRECT-GROUP-POST: If the current message's bot/sender prefix is a CLONE callsign (ATLAS, ORION, or any `[<callsign>]` tag other than ELLIOT, AIDEN, DAVE, SCOUT, ENFORCER), flag as VIOLATION — clones are prohibited from posting to group per C3 Prime-Only Clone Channel. Clone output must go only to parent inbox via relay-watcher push. Parent surfaces clone artefacts to group via `[CONSUMED:<parent>] <path> + verbatim excerpt` post. Seeing a clone callsign in group means either (a) the clone violated C3 directly, or (b) a parent wrote under the wrong prefix — either way, flag.

RESPOND WITH ONLY THIS JSON:
{
  "violation": true/false,
  "rule_number": N or null,
  "rule_name": "name" or null,
  "detail": "specific issue" or null,
  "should_have": "what should have happened" or null
}

If NO violation, return {"violation": false, "rule_number": null, "rule_name": null, "detail": null, "should_have": null}

You also have access to GOVERNANCE_EVENTS — a state tracker of the most recent concur, Step 0, and /stage0 events. Use these to check rules even when the events fall outside the recent_messages window.

IMPORTANT: Flag violations when detected. Err on the side of flagging — missed violations are worse than false alarms.
Do NOT flag Dave's messages — he is not subject to bot rules.
Do NOT flag messages that are clearly part of peer discussion (not Dave-facing).
Messages labeled as 'test' or 'deliberate violation' are STILL subject to rule evaluation — flag them the same as real violations.
"""

# Trigger patterns that warrant a check
# NOTE: named TRIGGER_PATTERNS here (not QUICK_CHECK_KEYWORDS as some docs call it).
TRIGGER_PATTERNS = [
    "dave —",
    "dave,",
    "your call",
    "here's the plan",
    "here's what",
    "commit",
    "pushed",
    "pr #",
    "merged",
    "deployed",
    "triggered",
    "complete",
    "done",
    "all stores written",
    "4-store",
    "git push origin main",
    "memory_listener.py",
    "chat_bot.py",
    "store.py",
    "listener_discernment.py",
    "claude.md",
    "state saved",
    "ceo_memory updated",
    "manual updated",
    "drive mirror",
    "daily_log written",
    "stores written",
    "store save complete",
    "session closed",
    "[atlas]",
    "[orion]",
    # Dual-concur governance (2026-04-22): [FINAL CONCUR:*] is peer-Step-0 signal for Rule 2
    "[final concur",
    "final concur:elliot",
    "final concur:aiden",
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

    user_content = json.dumps(
        {
            "current_message": current_msg,
            "recent_messages": recent_msgs[-MAX_WINDOW:],
            "governance_events": enforce_events,
        },
        ensure_ascii=False,
    )

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


BOT_INBOXES = [
    "/tmp/telegram-relay-elliot/inbox",
    "/tmp/telegram-relay-aiden/inbox",
    "/tmp/telegram-relay-max/inbox",  # NEW — Dave directive 2026-05-02
]

# Regex to detect PR number adjacent to a positive-claim keyword (either order).
# Liberal on purpose — false positives are cheap (verification is mechanical and fast).
# Matches both "#521 merged" and "521 passed" (bare number) and reverse-order "merged #521".
# "approved" / "approved by both" included so review-state claims trigger mechanical check.
PR_CLAIM_RE = re.compile(
    r"#?(\d+).{0,80}?(merged|approved(?:\s+by\s+both)?|complete|passed?|green|all\s+tests|ci\s+pass|ship)"
    r"|(merged|approved(?:\s+by\s+both)?|complete|passed?|green|all\s+tests|ci\s+pass).{0,80}?#?(\d+)",
    re.IGNORECASE,
)


async def send_interjection(text: str) -> None:
    """Post enforcement interjection to the group AND to bot inboxes."""
    # 1. Post to Telegram group (Dave sees it)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                url,
                json={
                    "chat_id": GROUP_CHAT_ID,
                    "text": text,
                },
            )
    except Exception as exc:
        logger.error("Failed to send TG interjection: %s", exc)

    # 2. Write to bot inboxes (bots see it in their tmux sessions)
    import uuid

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    for inbox in BOT_INBOXES:
        try:
            os.makedirs(inbox, exist_ok=True)
            fname = f"{ts}_{uuid.uuid4().hex[:8]}.json"
            payload = {
                "id": fname.replace(".json", ""),
                "type": "text",
                "chat_id": int(GROUP_CHAT_ID),
                "text": f"[ENFORCER]: {text}",
                "sender": "enforcer",
                "timestamp": datetime.now(UTC).isoformat(),
            }
            with open(os.path.join(inbox, fname), "w") as f:
                json.dump(payload, f)
        except Exception as exc:
            logger.error("Failed to write to %s: %s", inbox, exc)


async def process_message(message: dict) -> None:
    """Process a single Telegram message."""
    text = message.get("text", "")
    if not text:
        return

    # Add to sliding window
    sender = message.get("from", {})
    sender_name = sender.get("first_name", "Unknown")
    sender_username = sender.get("username", "")
    sender_is_bot = sender.get("is_bot", False)
    window_entry = f"[{sender_name}]: {text[:500]}"
    message_window.append(window_entry)

    # --- Update event-state tracker ---
    now_iso = datetime.now(UTC).isoformat()
    text_lower = text.lower()

    # Track Dave's /stage0 requests (Dave = not a bot)
    if not sender_is_bot and (
        text.strip().endswith("/stage0") or text.strip().endswith("/stage 0")
    ):
        enforce_events["last_stage0_request"] = {
            "timestamp": now_iso,
            "text_snippet": text[:100],
            "topic_hint": text[:60],
        }
        logger.info("EVENT: last_stage0_request updated")

    # Track bot concurrence
    if sender_is_bot and ("concur" in text_lower):
        callsign = sender_name.lower()
        if "elliot" in callsign:
            enforce_events["last_concur_elliot"] = {
                "timestamp": now_iso,
                "text_snippet": text[:100],
                "topic_hint": text[:60],
            }
            logger.info("EVENT: last_concur_elliot updated")
        elif "aiden" in callsign:
            enforce_events["last_concur_aiden"] = {
                "timestamp": now_iso,
                "text_snippet": text[:100],
                "topic_hint": text[:60],
            }
            logger.info("EVENT: last_concur_aiden updated")

    # Track Step 0 / RESTATE posts
    if "step 0" in text_lower or "restate" in text_lower:
        enforce_events["last_step0"] = {
            "timestamp": now_iso,
            "text_snippet": text[:100],
            "topic_hint": text[:60],
        }
        logger.info("EVENT: last_step0 updated")

    # Only check bot messages
    logger.info("MSG from=%s is_bot=%s text=%s", sender_username, sender_is_bot, text[:80])

    if not is_bot_message(message):
        logger.info("Skipped (not bot): %s", sender_username)
        return

    # Pre-filter
    if not should_check(text):
        logger.info("Skipped (no trigger): %s", text[:60])
        return

    logger.info("CHECKING message from %s against rules", sender_username)

    # --- /stage0 gate: deterministic Python check (not LLM) ---
    stage0_active = False
    last_stage0 = enforce_events.get("last_stage0_request", {})
    if last_stage0:
        stage0_ts = last_stage0.get("timestamp", "")
        if stage0_ts:
            try:
                ts = datetime.fromisoformat(stage0_ts)
                age_minutes = (datetime.now(UTC) - ts).total_seconds() / 60
                stage0_active = age_minutes < 30
            except Exception:
                pass
    logger.info("/stage0 gate: active=%s", stage0_active)

    recent_window = list(message_window)
    result = await check_with_llm(text, recent_window)

    if result and result.get("violation"):
        rule_num = result.get("rule_number", "?")
        rule_name = result.get("rule_name", "unknown")
        detail = result.get("detail", "")
        should_have = result.get("should_have", "")

        # Rules 1+2 require /stage0 to be active — suppress if not
        if rule_num in (1, 2) and not stage0_active:
            logger.info("Rule %s violation suppressed — /stage0 not active", rule_num)
            return

        # Rate limit: don't re-flag same rule within cooldown
        flag_key = f"rule_{rule_num}"
        now = time.time()
        if (
            flag_key in last_flag_times
            and (now - last_flag_times[flag_key]) < FLAG_COOLDOWN_SECONDS
        ):
            logger.info("Skipping re-flag for rule %s (cooldown)", rule_num)
            return

        last_flag_times[flag_key] = now

        interjection = f"[ENFORCER] Rule {rule_num} -- {rule_name}: {detail}. {should_have}."
        logger.info("VIOLATION: %s", interjection)
        await send_interjection(interjection)


ENFORCER_INBOX = "/tmp/telegram-relay-enforcer/inbox"


async def watch_inbox() -> None:
    """Watch the enforcer inbox for cross-posted messages from chat_bot.py."""
    os.makedirs(ENFORCER_INBOX, exist_ok=True)
    logger.info("Enforcer watching inbox: %s", ENFORCER_INBOX)

    while True:
        try:
            files = sorted(f for f in os.listdir(ENFORCER_INBOX) if f.endswith(".json"))
            for fname in files:
                fpath = os.path.join(ENFORCER_INBOX, fname)
                try:
                    with open(fpath) as f:
                        msg = json.load(f)
                    os.unlink(fpath)

                    text = msg.get("text", "")
                    callsign = msg.get("sender_callsign", "unknown")
                    is_bot = msg.get("sender_is_bot", False)

                    message_dict = {
                        "text": text,
                        "from": {
                            "first_name": callsign,
                            "username": callsign,
                            "is_bot": is_bot,
                        },
                    }
                    await process_message(message_dict)
                except Exception as exc:
                    logger.error("Error processing %s: %s", fname, exc)
                    with contextlib.suppress(OSError):
                        os.unlink(fpath)

        except Exception as exc:
            logger.error("Inbox watch error: %s", exc)

        await asyncio.sleep(1)  # check inbox every second


MAX_OUTBOX = "/tmp/telegram-relay-max/outbox"


async def watch_max_outbox() -> None:
    """Watch MAX's outbox for PR/completion claims and mechanically verify them.

    Applies regex pre-filter (cheap) before running verify_pr.sh (slightly heavier).
    Fail-open: errors in verification log a warning and continue — never crash the watcher.
    """
    os.makedirs(MAX_OUTBOX, exist_ok=True)
    logger.info("Enforcer watching MAX outbox: %s", MAX_OUTBOX)

    while True:
        try:
            files = sorted(f for f in os.listdir(MAX_OUTBOX) if f.endswith(".json"))
            for fname in files:
                fpath = os.path.join(MAX_OUTBOX, fname)
                try:
                    with open(fpath) as f:
                        msg = json.load(f)
                    os.unlink(fpath)

                    text = msg.get("text", "")
                    if not text:
                        continue

                    # Cheap regex pre-filter — skip if no PR claim detected
                    match = PR_CLAIM_RE.search(text)
                    if not match:
                        logger.debug("MAX outbox: no PR claim in %s", fname)
                        continue

                    # Extract PR number from first numeric capture group
                    pr_num_str = match.group(1) or match.group(4)
                    if not pr_num_str:
                        logger.debug("MAX outbox: regex matched but no PR number in %s", fname)
                        continue
                    pr_num = int(pr_num_str)

                    # Determine which claim keyword triggered the match
                    claim_kw = (match.group(2) or match.group(3) or "").lower().strip()

                    logger.info(
                        "MAX outbox: PR claim detected — PR #%d keyword=%r in %s",
                        pr_num,
                        claim_kw,
                        fname,
                    )

                    # Mechanical verification via verify_pr.sh
                    try:
                        script_path = os.path.join(
                            os.path.dirname(
                                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                            ),
                            "scripts",
                            "verify_pr.sh",
                        )
                        proc = await asyncio.create_subprocess_exec(
                            "bash",
                            script_path,
                            str(pr_num),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        try:
                            stdout_b, stderr_b = await asyncio.wait_for(
                                proc.communicate(), timeout=15
                            )
                        except TimeoutError:
                            proc.kill()
                            await proc.wait()
                            logger.warning("verify_pr.sh timed out for PR #%d — skipping", pr_num)
                            continue
                        stdout = stdout_b.decode()
                        stderr = stderr_b.decode()
                        if not stdout.strip():
                            logger.warning(
                                "verify_pr.sh returned no output for PR #%d (exit %d): %s",
                                pr_num,
                                proc.returncode,
                                stderr[:200],
                            )
                            continue

                        verify = json.loads(stdout)
                    except json.JSONDecodeError as exc:
                        logger.warning(
                            "verify_pr.sh output not valid JSON for PR #%d: %s", pr_num, exc
                        )
                        continue
                    except Exception as exc:
                        logger.warning("verify_pr.sh error for PR #%d: %s", pr_num, exc)
                        continue

                    # Mechanical comparison against verify_pr.sh output.
                    mismatch_reason = None

                    if claim_kw in ("merged", "complete", "ship") and not verify.get("merged"):
                        mismatch_reason = (
                            f"claimed '{claim_kw}' but merged=false (state={verify.get('state')})"
                        )
                    elif claim_kw in (
                        "passed",
                        "pass",
                        "green",
                        "all tests",
                        "ci pass",
                    ) and not verify.get("ci_passing"):
                        mismatch_reason = f"claimed '{claim_kw}' but ci_passing=false"
                    elif re.match(r"approved", claim_kw, re.IGNORECASE):
                        review_state = verify.get("review_state", "unknown")
                        if review_state != "APPROVED":
                            mismatch_reason = (
                                f"claimed '{claim_kw}' but review_state={review_state}"
                            )

                    if mismatch_reason:
                        failed = verify.get("failed_checks", [])
                        source_excerpt = text[:100].replace("\n", " ")
                        interjection = (
                            f"[ENFORCER] Rule 3 — COMPLETION-REQUIRES-VERIFICATION:\n"
                            f"MAX claimed PR #{pr_num} {mismatch_reason}. "
                            f"state={verify.get('state')} ci_passing={verify.get('ci_passing')} "
                            f"review_state={verify.get('review_state')}. "
                            f"Failed checks: {failed}. "
                            f"Source: {source_excerpt}"
                        )
                        logger.info("MISMATCH: %s", interjection)
                        await send_interjection(interjection)
                    else:
                        logger.debug(
                            "MAX PR #%d claim verified OK (merged=%s ci_passing=%s)",
                            pr_num,
                            verify.get("merged"),
                            verify.get("ci_passing"),
                        )

                except Exception as exc:
                    logger.error("Error processing MAX outbox %s: %s", fname, exc)
                    with contextlib.suppress(OSError):
                        os.unlink(fpath)

        except Exception as exc:
            logger.error("MAX outbox watch error: %s", exc)

        await asyncio.sleep(1)  # check outbox every second


def main():
    """Entry point — watches inbox and MAX outbox concurrently, sends interjections via Bot API."""
    if not BOT_TOKEN:
        logger.error("ENFORCER_BOT_TOKEN not set")
        return
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — enforcement checks disabled")

    logger.info("Enforcer bot starting — inbox mode, group %s", GROUP_CHAT_ID)

    async def main_loop() -> None:
        """Run inbox watcher and MAX outbox watcher concurrently."""
        await asyncio.gather(watch_inbox(), watch_max_outbox())

    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
