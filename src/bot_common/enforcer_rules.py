"""Enforcer rule definitions — structured, importable, testable.

Provenance: texts extracted byte-for-byte from
  src/telegram_bot/enforcer_bot.py lines 42-96 (RULES_PROMPT).
The narrative wrapper (opening paragraphs + JSON-format closing block)
is preserved verbatim for build_prompt(); only the per-rule body text
(i.e. everything after "Rule N — NAME: ") is stored in each record's
`text` field.

See also: docs/enforcer_redesign_spec.md §3.1 and §3.2.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Rule records
# ---------------------------------------------------------------------------
# Each `text` field is a byte-equal substring of src/telegram_bot/enforcer_bot.py.
# Specifically: the body that follows "Rule N — NAME: " on that rule's first line
# (multi-line rules continue until the next blank line or Rule header).
# The `exceptions` lists for R2 and R3 reproduce the five / three enumerated
# EXCEPTIONS paragraphs from lines 54-65 of the same file.
# ---------------------------------------------------------------------------

RULES: list[dict] = [
    {
        "id": "R1",
        "name": "CONCUR-BEFORE-SUMMARY",
        "text": (
            "If the current message is a bot addressing Dave with a summary, "
            "recommendation, or decision (look for \"Dave —\", \"Dave,\", \"your call\", "
            "\"here's the plan\", \"here's what\"), check if the OTHER bot posted explicit "
            "concurrence (\"concur\", \"concur confirmed\", \"CONCUR\") in recent messages "
            "OR in GOVERNANCE_EVENTS (last_concur_elliot / last_concur_aiden) for the same "
            "topic. Missing concurrence = VIOLATION. NOTE: /stage0 gating is handled "
            "externally in code — evaluate Rule 1 on its merits and report if concurrence "
            "is missing."
        ),
        "channels": ["#execution"],
        "requires_stage0": True,
        "cooldown_s": 300,
        "exceptions": [],
    },
    {
        "id": "R2",
        "name": "STEP-0-BEFORE-EXECUTION",
        "text": (
            "If the current message shows execution starting (mentions committing, pushing, "
            "deploying, triggering flows, creating PRs), check whether EITHER of the "
            "following governance signals exists in recent_messages or governance_events for "
            "the same topic:\n"
            "  (a) a Dave-directed Step 0 / RESTATE post, OR\n"
            "  (b) a dual peer-Step-0 pair — BOTH `[FINAL CONCUR:ELLIOT]` AND "
            "`[FINAL CONCUR:AIDEN]` tags present in recent_messages on the same topic "
            "(dual-concur governance ratified 2026-04-22).\n"
            "Having EITHER signal = PASS. Missing BOTH = VIOLATION."
        ),
        "channels": ["#execution"],
        "requires_stage0": True,
        "cooldown_s": 300,
        "exceptions": [
            "PR merge on explicit CEO instruction (Dave posts \"merge N\" or \"merge N + continue\")",
            "Rebase performed as peer-review fix (continuation of original dispatch, not new directive)",
            "Orchestrator tagging peer replies (acknowledgement, not execution)",
            "CEO removed Step 0 confirmation gate (\"no more approvals\" or \"only merge approvals\") — bots post RESTATE for discipline but execution proceeds without Dave-pause. Only PR-merge actions require explicit Dave approval.",
            "Task approved via [PROPOSE:<callsign>] + Dave \"approve\" — execution starts immediately after approval without separate Step 0 post.",
        ],
    },
    {
        "id": "R3",
        "name": "COMPLETION-REQUIRES-VERIFICATION",
        "text": (
            "If the current message claims task completion (\"complete\", \"done\", "
            "\"all stores written\", \"4-store save complete\"), check if verification "
            "evidence was posted (terminal output, SQL results, test output, commit hashes). "
            "Claim without evidence = VIOLATION."
        ),
        "channels": ["#execution", "#alerts"],
        "requires_stage0": False,
        "cooldown_s": 300,
        "exceptions": [
            "Messages starting with '[GOVERNANCE] Gatekeeper DENY' or '[GATEKEEPER-DENY:' — these are automated gate outputs (the opposite of completion claims), not bot assertions of done.",
            "Messages reporting a Gatekeeper allow/deny verdict as test evidence — the verdict IS the verification output.",
            "Messages containing 'observe-only' or 'synthetic test' — these are test/verify actions, not real completion claims.",
        ],
    },
    {
        "id": "R4",
        "name": "NO-UNREVIEWED-MAIN-PUSH",
        "text": (
            "If the current message mentions pushing directly to main without mentioning "
            "PR review or peer approval, flag as WARNING (not hard violation)."
        ),
        "channels": ["#execution"],
        "requires_stage0": False,
        "cooldown_s": 300,
        "exceptions": [],
    },
    {
        "id": "R5",
        "name": "SHARED-FILE-CLAIM",
        "text": (
            "If the current message mentions editing memory_listener.py, chat_bot.py, "
            "store.py, listener_discernment.py, or any CLAUDE.md file, check if "
            "\"[CLAIM:\" was posted. Missing claim = VIOLATION."
        ),
        "channels": ["#execution"],
        "requires_stage0": False,
        "cooldown_s": 300,
        "exceptions": [],
    },
    {
        "id": "R6",
        "name": "SAVE-CLAIM-REQUIRES-PROOF",
        "text": (
            "If the current message claims a save was completed (\"state saved\", "
            "\"4-store save complete\", \"ceo_memory updated\", \"MANUAL updated\", "
            "\"Drive mirrored\", \"daily_log written\", \"stores written\"), check that "
            "the message includes SPECIFIC EVIDENCE for EACH store claimed. Evidence means: "
            "commit hashes for MANUAL, SQL confirmation for ceo_memory, byte count or "
            "success message for Drive mirror, query result for daily_log. A bot saying "
            "\"all stores written ✓\" without showing the actual outputs for each store = "
            "VIOLATION. The claim must be backed by verifiable proof in recent messages, "
            "not just checkmarks."
        ),
        "channels": ["#execution", "#alerts"],
        "requires_stage0": False,
        "cooldown_s": 300,
        "exceptions": [],
    },
    {
        "id": "R7",
        "name": "CLONE-DIRECT-GROUP-POST",
        "text": (
            "If the current message's bot/sender prefix is a CLONE callsign (ATLAS, ORION, "
            "or any `[<callsign>]` tag other than ELLIOT, AIDEN, DAVE, SCOUT, ENFORCER), "
            "flag as VIOLATION — clones are prohibited from posting to group per C3 "
            "Prime-Only Clone Channel. Clone output must go only to parent inbox via "
            "relay-watcher push. Parent surfaces clone artefacts to group via "
            "`[CONSUMED:<parent>] <path> + verbatim excerpt` post. Seeing a clone callsign "
            "in group means either (a) the clone violated C3 directly, or (b) a parent "
            "wrote under the wrong prefix — either way, flag."
        ),
        "channels": ["#execution", "#alerts"],
        "requires_stage0": False,
        "cooldown_s": 300,
        "exceptions": [],
    },
    {
        "id": "R8",
        "name": "DISPATCH-COORDINATION",
        "text": (
            "If the current message shows a clone dispatch being injected (mentions "
            "\"dispatched\", \"injected\", \"tmux paste\", \"ATLAS dispatched\", "
            "\"ORION dispatched\", or dispatch JSON), check whether a "
            "[DISPATCH-PROPOSAL:<callsign>] was posted in recent_messages AND the peer "
            "posted [CONCUR] on that proposal BEFORE the dispatch. Dispatching without "
            "prior proposal + peer concur = VIOLATION. Exception: if only one bot is active "
            "(peer offline/reset), solo dispatch with proposal posted is sufficient."
        ),
        "channels": ["#execution"],
        "requires_stage0": False,
        "cooldown_s": 300,
        "exceptions": [],
    },
    {
        "id": "R9",
        "name": "DIRECTIVE-INITIATIVE",
        "text": (
            "If the current message is from a bot (ELLIOT or AIDEN) and ends with "
            "open-ended agenda-setting phrases directed at Dave — such as "
            "\"standing by for directive\", \"ready for next directive\", \"what's next\", "
            "\"awaiting your call\", \"what would you like\", or any question asking Dave "
            "to SET the agenda rather than APPROVE a proposal — flag as VIOLATION. Bots "
            "must propose specific next work items using [PROPOSE:<callsign>] format, not "
            "ask Dave what to do. Exception: [SESSION-WRAP:<callsign>] is allowed for "
            "genuine end-of-session. First violation = warning, second = governance debt log."
        ),
        "channels": ["#execution"],
        "requires_stage0": False,
        "cooldown_s": 300,
        "exceptions": [],
    },
]

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

RULES_BY_ID: dict[str, dict] = {r["id"]: r for r in RULES}

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_PROMPT_HEADER = """\
You are a governance enforcement bot for a multi-agent development team.

You monitor group chat messages between two AI agents (Elliot and Aiden) and their human manager (Dave).

CHECK these 7 rules against the CURRENT MESSAGE in context of the RECENT MESSAGES:
"""

_PROMPT_FOOTER = """\

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

_RULE_ID_TO_NUMBER: dict[str, int] = {
    "R1": 1, "R2": 2, "R3": 3, "R4": 4, "R5": 5,
    "R6": 6, "R7": 7, "R8": 8, "R9": 9,
}


def build_prompt(channel: str) -> str:
    """Compose RULES_PROMPT for the LLM, filtered to rules active in ``channel``.

    Output is the same opening narrative + body + closing JSON-format block
    as enforcer_bot.py:42-96, but with the rule list restricted to
    ``[r for r in RULES if channel in r["channels"]]``.

    The rule number shown in the prompt body reflects the canonical integer
    (1-9) regardless of filtering — the LLM must return the original rule
    number so log grep-compat is preserved.
    """
    active = [r for r in RULES if channel in r["channels"]]
    rule_lines: list[str] = []
    for r in active:
        num = _RULE_ID_TO_NUMBER[r["id"]]
        body = r["text"]
        exceptions = r.get("exceptions", [])
        block = f"Rule {num} — {r['name']}: {body}"
        if exceptions:
            block += "\nEXCEPTIONS (always PASS, no Step 0 required):"
            for i, exc in enumerate(exceptions, 1):
                block += f"\n  ({_roman(i)})   {exc}"
        rule_lines.append(block)

    return _PROMPT_HEADER + "\n\n".join(rule_lines) + "\n" + _PROMPT_FOOTER


def _roman(n: int) -> str:
    """Return lowercase roman numeral for integers 1-9 (used in exception lists)."""
    return ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix"][n - 1]
