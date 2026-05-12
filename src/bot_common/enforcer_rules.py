"""enforcer_rules.py — LLM prompt + constants for governance enforcement.

Post Phase 5 round table (2026-05-11): 8 of 9 rules are now handled by
deterministic checks in src/bot_common/enforcer_deterministic.py. This
module retains RULES_PROMPT for the sole remaining LLM-checked rule (R9)
plus R3 SOFT fallback context.

R1/R5/R7: retired (docs/governance/deprecated/)
R2/R4/R8: deterministic (enforcer_deterministic.py)
R3/R6: hybrid — deterministic pre-filter, LLM fallback for ambiguous cases
R9: LLM-only (semantic check)

TRIGGER_PATTERNS, should_check(), and constants are still imported by
concur_gate.py and central_listener.py.
"""

from __future__ import annotations

CHECK_MODEL = "gpt-4o-mini"
# R2-A (FP-tuning 2026-05-11): bumped 20→50 so Step-0 RESTATE earlier in a
# directive thread remains in scope after multiple peer interleaves.
MAX_WINDOW = 50
FLAG_COOLDOWN_SECONDS = 300

# Per PR #672 decision #2: R3 (completion-without-evidence) + R6 (save-without-proof)
# route to both #alerts AND #execution. Other rules to #alerts only.
HIGH_SEVERITY_RULES: frozenset[int] = frozenset({3, 6})


TRIGGER_PATTERNS: tuple[str, ...] = (
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
    "[final concur",
    "final concur:elliot",
    "final concur:aiden",
)


def should_check(text: str) -> bool:
    """Pre-filter: only check messages matching trigger patterns."""
    lower = text.lower()
    return any(p in lower for p in TRIGGER_PATTERNS)


RULES_PROMPT = """You are a governance enforcement bot for a multi-agent development team.

You monitor group chat messages between AI agents (Elliot, Aiden, Max, Atlas, Orion, and Scout) and their human manager (Dave).

Most rules are now checked deterministically before this LLM call. You only need to check:

Rule 3 — COMPLETION-REQUIRES-VERIFICATION (SOFT fallback only):
If the current message uses "done" in a way that might be a completion claim (not "not done", "isn't done") but does NOT contain obvious evidence (commit hashes, PR references, terminal output, test results), evaluate whether the message is actually claiming task completion. If it is a genuine completion claim without evidence, flag as VIOLATION. If "done" is used conversationally ("done reviewing", "done for the day", "done discussing"), return no violation.

Rule 9 — DIRECTIVE-INITIATIVE:
If the current message is from a bot (ELLIOT, AIDEN, MAX, ATLAS, ORION, or SCOUT) and ends with open-ended agenda-setting phrases directed at Dave — such as "standing by for directive", "ready for next directive", "what's next", "awaiting your call", "what would you like", or any question asking Dave to SET the agenda rather than APPROVE a proposal — flag as VIOLATION. Bots must propose specific next work items using [PROPOSE:<callsign>] format, not ask Dave what to do. Exceptions: [SESSION-WRAP:<callsign>] is allowed for genuine end-of-session. Bare status phrases like "Standing by", "Continuing standby", "Holding", "Awaiting concur", or "Wakeup at HH:MM" are NOT violations — these are legitimate gated-status updates when agents are blocked on pending decisions, not directive-seeking.

RESPOND WITH ONLY THIS JSON:
{
  "violation": true/false,
  "rule_number": N or null,
  "rule_name": "name" or null,
  "detail": "specific issue" or null,
  "should_have": "what should have happened" or null
}

If NO violation, return {"violation": false, "rule_number": null, "rule_name": null, "detail": null, "should_have": null}

IMPORTANT: Only check Rule 3 (soft) and Rule 9. All other rules are handled deterministically.
Do NOT flag Dave's messages.
Do NOT flag messages that are clearly part of peer discussion.
"""
