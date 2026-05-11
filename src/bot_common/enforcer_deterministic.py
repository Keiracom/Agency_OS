"""enforcer_deterministic.py — deterministic governance rule checks.

Deterministic-first architecture: each check runs a fast regex/text scan
BEFORE the LLM call. If deterministic returns a result, the caller skips
gpt-4o-mini. If it returns None, the caller falls through to LLM.

Rules implemented: R2, R4, R8 (deterministic); R3, R6 (hybrid pre-filter + LLM fallback)
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
# R3 — COMPLETION-REQUIRES-VERIFICATION (hybrid)
# R5 + R7 RETIRED — see docs/governance/deprecated/
# ---------------------------------------------------------------------------

# Exceptions: gatekeeper and synthetic messages always pass.
_R3_EXCEPTION_RE = re.compile(
    r"\[GOVERNANCE\]\s+Gatekeeper"
    r"|observe-only"
    r"|synthetic test",
    re.IGNORECASE,
)

# STRICT completion triggers — always check for evidence.
_R3_STRICT_RE = re.compile(
    r"\bcomplete\b"
    r"|all stores written"
    r"|4-store save complete"
    r"|store save complete"
    r"|task complete"
    r"|build complete",
    re.IGNORECASE,
)

# SOFT trigger — "done" at word boundary, not preceded by "not", "isn't", "won't be".
_R3_SOFT_RE = re.compile(r"(?<!not\s)(?<!isn't\s)(?<!won't be\s)\bdone\b", re.IGNORECASE)

# Evidence patterns — if any match alongside a claim → PASS.
# FP-tuning 2026-05-11: expanded with JSON-shape patterns to catch verbatim
# `gh pr view` / CI rollup output that prior regex missed (FP-LOG:R3 ×3 on
# 2026-05-11 ~20:31–20:35 — messages had 7+ SUCCESS rows + commit hashes
# but R3 STRICT still fired because evidence regex required prose form).
_R3_EVIDENCE_RE = re.compile(
    r"\b[0-9a-f]{7,40}\b"  # commit hash
    r"|PR\s*#\d+\s+(?:merged|closed|open)"  # PR reference with state (prose)
    r'|"state"\s*:\s*"(?:MERGED|OPEN|CLOSED)"'  # gh pr view JSON state
    r'|"mergeCommit"\s*:\s*\{'  # gh pr view JSON mergeCommit
    r'|"mergedAt"\s*:\s*"\d{4}-'  # gh pr view JSON mergedAt timestamp
    r"|\bMERGEABLE\b|\bMERGED\b"  # gh CLI state words
    r"|\bSUCCESS\b|\bFAILURE\b"  # CI check status row
    r"|^[\$>→]"  # terminal output line
    r"|PID\s+\d+"  # PID
    r"|ActiveState="  # systemd state
    r"|exit\s+code"  # exit code
    r"|\d+/\d+\s+(?:pass|fail)"  # test counts ratio form
    r"|\d+\s+(?:passed|failed|error|errors)\b"  # pytest "N passed in 0.69s" form
    r"|tests?\s+pass"  # test pass
    r"|rows?\s+affected"  # SQL output
    r"|\bSELECT\b|\bINSERT\b|\bUPDATE\b"  # SQL keywords
    r"|\d+\s+(?:insertion|deletion)"  # git diff stats
    r"|\d{4}-\d{2}-\d{2}.*UTC"  # timestamp with detail
    r"|commit\s+[0-9a-f]{7,}",  # commit message format
    re.IGNORECASE | re.MULTILINE,
)


def check_r3(text: str) -> tuple[dict | None, bool]:
    """R3 — COMPLETION-REQUIRES-VERIFICATION (hybrid).

    Returns (result, skip_llm):
      - STRICT claim + evidence    → (None, True)       PASS, skip LLM
      - STRICT claim + no evidence → (violation, True)  VIOLATION, skip LLM
      - SOFT "done" + evidence     → (None, True)       PASS, skip LLM
      - SOFT "done" + no evidence  → (None, False)      ambiguous, fall through to LLM
      - No claim                   → (None, False)      not applicable, fall through to LLM
    """
    if _R3_EXCEPTION_RE.search(text):
        return None, True

    has_evidence = bool(_R3_EVIDENCE_RE.search(text))

    if _R3_STRICT_RE.search(text):
        if has_evidence:
            return None, True
        return {
            "violation": True,
            "rule_number": 3,
            "rule_name": "COMPLETION-REQUIRES-VERIFICATION",
            "detail": "Completion claim made without inline evidence (commit hash, PR state, terminal output, etc.).",
            "should_have": "Every completion claim must include verifiable evidence such as a commit hash, PR number with state, or raw terminal output.",
        }, True

    if _R3_SOFT_RE.search(text):
        if has_evidence:
            return None, True
        return None, False

    return None, False


# ---------------------------------------------------------------------------
# R6 — SAVE-CLAIM-REQUIRES-PROOF (hybrid)
# ---------------------------------------------------------------------------

_R6_SAVE_RE = re.compile(
    r"state saved"
    r"|4-store save complete"
    r"|ceo_memory updated"
    r"|manual updated"
    r"|drive mirror"
    r"|daily_log written"
    r"|stores written"
    r"|store save complete",
    re.IGNORECASE,
)

_R6_EVIDENCE_RE = re.compile(
    r"\b[0-9a-f]{7,40}\b"  # commit hash (MANUAL)
    r"|rows?\s+affected"  # SQL output (ceo_memory)
    r"|\bINSERT\b|\bupsert\b"  # SQL keywords (ceo_memory)
    r"|updated_at"  # ceo_memory field
    r"|\d+\s*bytes?"  # byte count (Drive)
    r"|\bsuccess\b|\bmirrored\b"  # Drive success marker
    r"|\bSELECT\b"  # query result (daily_log)
    r"|\brow\b"  # row reference (daily_log)
    r"|\bdaily_log\b",  # explicit daily_log mention with evidence context
    re.IGNORECASE,
)


def check_r6(text: str) -> tuple[dict | None, bool]:
    """R6 — SAVE-CLAIM-REQUIRES-PROOF (hybrid).

    Returns (result, skip_llm):
      - Save claim + ≥1 store evidence → (None, True)       PASS, skip LLM
      - Save claim + 0 store evidence  → (violation, True)  VIOLATION, skip LLM
      - No save claim                  → (None, False)      not applicable, fall through to LLM
    """
    if not _R6_SAVE_RE.search(text):
        return None, False

    if _R6_EVIDENCE_RE.search(text):
        return None, True

    return {
        "violation": True,
        "rule_number": 6,
        "rule_name": "SAVE-CLAIM-REQUIRES-PROOF",
        "detail": "Save/store claim made without store-specific evidence (commit hash, SQL output, byte count, etc.).",
        "should_have": "Every save claim must include proof: commit hash for MANUAL, SQL rows affected for ceo_memory, byte count or 'mirrored' for Drive, query result for daily_log.",
    }, True


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
# Track 4 (FP-tuning 2026-05-11): expanded protocol-tag list to mirror PR #710's
# R9 exempt superset. Prior version covered only [propose:|summary-draft:|
# concur-request:]; missed [concur:|ready:|busy:|fp-log:|valid-fire:|dispatch:]
# which produced R2 ×6 FPs this session on status posts containing merge/ship
# keywords. The `[\w:-]*\]` post-colon pattern absorbs nested-task-id form
# like [BUSY:aiden:dispatch-batch-2026-05-11-20:40].
_R2_EXEMPT_RE = re.compile(
    r"\bpr\s*#\d+\s+merged\s+(?:earlier|prior|already|2026)"
    r"|\b(?:will|going to|about to|planning to|propose to)\s+(?:commit|push|deploy|merge|create|trigger)"
    r"|\b(?:not|haven't|won't)\s+(?:yet\s+)?(?:committed|pushed|deployed|merged)"
    r"|\[(?:propose|summary-draft|concur-request|concur|ready|busy|fp-log|valid-fire|dispatch|dispatch-proposal)[\w:-]*\]",
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

# Track 4 (FP-tuning 2026-05-11): tightened to past-tense / definite-action verbs
# only. Prior version matched "dispatching" (gerund) which over-matched on
# conditional/offer phrasing like "I can dispatch" or "dispatching takes ~30s".
# Now requires explicit completed-action or imperative form, NOT conditional.
_R8_DISPATCH_RE = re.compile(
    r"\b(?:dispatched|injected|tmux paste|tmux send-keys|"
    r"atlas dispatched|orion dispatched|clone dispatch|"
    r"sent dispatch|firing dispatch now|dispatch fired)\b",
    re.IGNORECASE,
)

# Conditional/offer language that explicitly is NOT a dispatch action.
_R8_CONDITIONAL_RE = re.compile(
    r"\b(?:can|could|would|will|may|might)\s+(?:dispatch|dispatching)\b"
    r"|\b(?:if|once|after|when)\s+(?:you|elliot|max|aiden)\s+(?:confirm|concur|approve)",
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
    # Track 4: exempt conditional/offer language ("I can dispatch", "will dispatch
    # if you confirm"). These are not dispatch actions; they're proposals.
    if _R8_CONDITIONAL_RE.search(text):
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
