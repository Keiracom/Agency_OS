"""enforcer_deterministic.py — deterministic governance rule checks.

Deterministic-first architecture: each check runs a fast regex/text scan
BEFORE the LLM call. If deterministic returns a result, the caller skips
gpt-4o-mini. If it returns None, the caller falls through to LLM.

Rules implemented: R4 (deterministic)
Stubs (pending subsequent PRs): R2, R3, R6, R8
Retired (docs/governance/deprecated/): R1 (concur_gate.py), R5, R7
LLM-only: R9 (semantic, stays in RULES_PROMPT)
"""

from __future__ import annotations

import re
from pathlib import Path

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
# Stubs — R2, R3, R6, R8  (return None = fall through to LLM)
# R5 + R7 RETIRED — see docs/governance/deprecated/
# ---------------------------------------------------------------------------


def check_r2(
    text: str,
    inbox_dir: Path,
    window_sec: int = 300,
) -> dict | None:
    """R2 — STEP-0-BEFORE-EXECUTION.  Stub — deterministic impl pending PR #2."""
    return None


def check_r3(text: str) -> tuple[dict | None, bool]:
    """R3 — COMPLETION-REQUIRES-VERIFICATION.  Stub — deterministic impl pending PR #2.

    Returns (result, skip_llm).  Both False here — fall through to LLM.
    """
    return None, False



def check_r6(text: str) -> tuple[dict | None, bool]:
    """R6 — SAVE-CLAIM-REQUIRES-PROOF.  Stub — deterministic impl pending PR #2.

    Returns (result, skip_llm).  Both False here — fall through to LLM.
    """
    return None, False


def check_r8(text: str, recent_messages: list[str]) -> dict | None:
    """R8 — DISPATCH-COORDINATION.  Stub — deterministic impl pending PR #2."""
    return None
