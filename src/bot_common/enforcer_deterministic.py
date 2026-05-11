"""enforcer_deterministic.py — deterministic governance rule checks.

Deterministic-first architecture: each check runs a fast regex/text scan
BEFORE the LLM call. If deterministic returns a result, the caller skips
gpt-4o-mini. If it returns None, the caller falls through to LLM.

Rules implemented: R2, R4, R8 (deterministic)
Stubs (pending Max PR #2): R3, R6 (hybrid pre-filter + LLM fallback)
Retired (docs/governance/deprecated/): R1 (concur_gate.py), R5, R7
LLM-only: R9 (semantic, stays in RULES_PROMPT)
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# R4 — NO-UNREVIEWED-MAIN-PUSH
# ---------------------------------------------------------------------------

# Patterns that indicate a direct push to main without PR process.
_R4_VIOLATION_RE = re.compile(
    r"git push origin main"
    r"|force.pushed to main"
    r"|merged to main without pr"
    r"|bypassed pr review"
    r"|pushed straight to main",
    re.IGNORECASE,
)

# Patterns that indicate a legitimate PR merge or feature-branch push.
# If any match, we return None (PASS) even if a trigger phrase is present.
_R4_EXEMPT_RE = re.compile(
    r"pr\s*#\d+\s+merged"
    r"|merge\s+pr\s+\d+"
    r"|gh\s+pr\s+merge"
    r"|merged\s+commit"
    r"|merge\s+all\s+pr"
    r"|pushed to branch"
    r"|pushed to origin (?:elliot|aiden|max|feature|fix|chore|test)/",
    re.IGNORECASE,
)


def check_r4(text: str) -> dict | None:
    """R4 — NO-UNREVIEWED-MAIN-PUSH.

    Returns a violation dict if the text describes a direct push to main
    without a PR.  Returns None if no violation detected or the message is
    covered by an exemption.
    """
    if _R4_EXEMPT_RE.search(text):
        return None
    if _R4_VIOLATION_RE.search(text):
        return {
            "violation": True,
            "rule_number": 4,
            "rule_name": "NO-UNREVIEWED-MAIN-PUSH",
            "detail": "Message indicates a direct push to main without PR review.",
            "should_have": "All changes to main must go through a PR with at least one peer review.",
        }
    return None


# ---------------------------------------------------------------------------
# Stubs — R3, R6  (return None = fall through to LLM until Max PR #2 lands)
# R5 + R7 RETIRED — see docs/governance/deprecated/
# ---------------------------------------------------------------------------


def check_r3(text: str) -> tuple[dict | None, bool]:
    """R3 — COMPLETION-REQUIRES-VERIFICATION.  Stub — pending Max PR #2 hybrid impl.

    Returns (result, skip_llm).  Both False here — fall through to LLM.
    """
    return None, False


def check_r6(text: str) -> tuple[dict | None, bool]:
    """R6 — SAVE-CLAIM-REQUIRES-PROOF.  Stub — pending Max PR #2 hybrid impl.

    Returns (result, skip_llm).  Both False here — fall through to LLM.
    """
    return None, False


# ---------------------------------------------------------------------------
# R2 — STEP-0-BEFORE-EXECUTION
# ---------------------------------------------------------------------------

# Trigger: message indicates an execution-action is happening NOW.
_R2_EXECUTION_RE = re.compile(
    r"\b(?:committing|pushing|deploying|deployed|merging|merged|"
    r"creating pr|opened pr|triggering flow|started flow|"
    r"running migration|applied migration|shipping|shipped|"
    r"executing|executed)\b",
    re.IGNORECASE,
)

# Exemptions — these mention execution language but are NOT new actions.
_R2_EXEMPT_RE = re.compile(
    r"\bpr\s*#\d+\s+merged\s+(?:earlier|prior|already|2026)"
    r"|\b(?:will|going to|about to|planning to|propose to)\s+(?:commit|push|deploy|merge|create|trigger)"
    r"|\b(?:not|haven't|won't)\s+(?:yet\s+)?(?:committed|pushed|deployed|merged)"
    r"|\[propose:"
    r"|\[summary-draft:"
    r"|\[concur-request:",
    re.IGNORECASE,
)

# Step-0 governance signals — any of these in recent inbox = PASS.
_R2_STEP0_RE = re.compile(
    r"step\s*0|objective:|restate:|^\s*-\s*\*\*objective:?\*\*"
    r"|\[final concur:|\[propose:.*approve",
    re.IGNORECASE | re.MULTILINE,
)


def check_r2(text: str, recent_messages: list[str] | None = None) -> dict | None:
    """R2 — STEP-0-BEFORE-EXECUTION.

    If text indicates execution starting AND no Step-0 / Objective / final-concur
    signal exists in the current message OR in recent_messages → VIOLATION.
    Else PASS.
    """
    if _R2_EXEMPT_RE.search(text):
        return None
    if not _R2_EXECUTION_RE.search(text):
        return None
    if _R2_STEP0_RE.search(text):
        return None  # the message itself contains the Step 0 signal
    if recent_messages is None:
        return None  # conservative pass when no context available
    if any(_R2_STEP0_RE.search(m) for m in recent_messages):
        return None
    return {
        "violation": True,
        "rule_number": 2,
        "rule_name": "STEP-0-BEFORE-EXECUTION",
        "detail": "Execution starting without Step-0 / Objective / final-concur governance signal in recent_messages.",
        "should_have": "Post Step 0 RESTATE (or get [FINAL CONCUR] / Dave directive) before execution.",
    }


# ---------------------------------------------------------------------------
# R8 — DISPATCH-COORDINATION
# ---------------------------------------------------------------------------

_R8_DISPATCH_RE = re.compile(
    r"\b(?:dispatched|injected|tmux paste|tmux send-keys|"
    r"atlas dispatched|orion dispatched|clone dispatch|"
    r"sent dispatch|dispatching now)\b",
    re.IGNORECASE,
)

_R8_PROPOSAL_RE = re.compile(r"\[dispatch-proposal:[^\]]+\]", re.IGNORECASE)
_R8_CONCUR_RE = re.compile(r"\[concur:[^\]]+\]", re.IGNORECASE)


def check_r8(text: str, recent_messages: list[str] | None = None) -> dict | None:
    """R8 — DISPATCH-COORDINATION.

    If text shows a clone dispatch happening, require [DISPATCH-PROPOSAL:<callsign>]
    AND peer [CONCUR] in recent_messages before it. Missing either = VIOLATION.
    """
    if not _R8_DISPATCH_RE.search(text):
        return None
    if recent_messages is None:
        return None  # conservative pass when no context available
    has_proposal = any(_R8_PROPOSAL_RE.search(m) for m in recent_messages)
    has_concur = any(_R8_CONCUR_RE.search(m) for m in recent_messages)
    if has_proposal and has_concur:
        return None
    missing = []
    if not has_proposal:
        missing.append("[DISPATCH-PROPOSAL:<callsign>]")
    if not has_concur:
        missing.append("[CONCUR:<peer>]")
    return {
        "violation": True,
        "rule_number": 8,
        "rule_name": "DISPATCH-COORDINATION",
        "detail": f"Dispatch action without prior {' + '.join(missing)} in recent_messages.",
        "should_have": "Post [DISPATCH-PROPOSAL:<callsign>] and wait for peer [CONCUR] before dispatching.",
    }
