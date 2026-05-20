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
from datetime import UTC, datetime

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
    r"all stores written"
    r"|4-store save complete"
    r"|store save complete"
    r"|task complete"
    r"|build complete"
    r"|deployment complete"
    r"|migration complete"
    r"|merge complete",
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
# Track 4 (FP-tuning 2026-05-11): protocol-tag superset (mirror PR #710's R9).
# Track 5 (FP-tuning 2026-05-11): verification-style phrasing exempts —
# "merged and verified" / "merged at <ISO>" / "mergeCommit" — caught by Max's
# post-Track-4 trace at 23:23:13 UTC.
_R2_EXEMPT_RE = re.compile(
    r"\bpr\s*#\d+\s+merged\s+(?:earlier|prior|already|2026)"
    r"|\bmerged\s+and\s+verified\b"  # Track 5: verification-style status post
    r"|\bmerged\s+at\s+\d{4}-"  # Track 5: ISO timestamp form
    r"|\bmergeCommit\b"  # Track 5: gh JSON field reference
    r"|\b(?:will|going to|about to|planning to|propose to)\s+(?:commit|push|deploy|merge|create|trigger)"
    r"|\b(?:not|haven't|won't)\s+(?:yet\s+)?(?:committed|pushed|deployed|merged)"
    r"|\[(?:propose|summary-draft|concur-request|concur|ready|busy|fp-log|valid-fire|dispatch|dispatch-proposal|dispatch-complete|state|complete)[\w:-]*\]"
    # Track 8: status-report exempts — past-tense reporting, not new execution
    r"|\bdeployed\b.*\blistener\s+restart"
    r"|\bfully\s+deployed\b"
    r"|\d+\s+PRs?\s+merged"
    r"|\bsession\s+(?:total|tally)\b.*\bmerged\b"
    r"|\bmerge\s+pull\s+request\b"
    r"|\bdeployed\s+at\s+\d"
    r"|\bshipped\s+in\s+PR\b",
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
# Track 5 (FP-tuning 2026-05-11): added COO/CTO own-clone dispatch exempt
# + Dave-authorized cross-dispatch exempt. Per memory pin: clones are 1:1
# (elliot→atlas, aiden→orion); dispatching your own clone is operationally
# normal and doesn't need a [DISPATCH-PROPOSAL]→[CONCUR] cycle. Cross-
# dispatch requires Dave authorization (override flag).
_R8_CONDITIONAL_RE = re.compile(
    r"\b(?:can|could|would|will|may|might)\s+(?:dispatch|dispatching)\b"
    r"|\b(?:if|once|after|when)\s+(?:you|elliot|max|aiden)\s+(?:confirm|concur|approve)"
    # Track 5: COO/CTO own-clone dispatch — always valid, no proposal needed
    r"|\belliot[\s\S]{0,40}?dispatched?\s+\w*atlas"
    r"|\baiden[\s\S]{0,40}?dispatched?\s+\w*orion"
    # Track 5: Dave-authorized dispatches (CEO override)
    r"|\bdave[\s-]?(?:authoris|authoriz)(?:e|ed|ation)"
    r"|\bcross[\s-]dispatch\s+override"
    r"|\bdave\s+directive\s+#\d+"
    r"|\bceo[\s-]?(?:delegated|override)",
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


# ---------------------------------------------------------------------------
# R10 — LINEAR-KEI-GATE (Wave 2 Outcome 3, Dave priority-reset ts 1778570450)
# ---------------------------------------------------------------------------

# Completion-claim phrases that should be paired with a Linear KEI status update.
# Mirrors enforcer_rules.TRIGGER_PATTERNS for the completion-claim subset but
# narrower — only the patterns that signal "work just shipped", not generic
# discussion of work.
_R10_COMPLETION_RE = re.compile(
    r"\bpr\s*#\d+\s+(?:merged|shipped|landed|deployed)\b"
    r"|\bmerged\s+(?:at\s+)?(?:sha\s+)?[a-f0-9]{7,40}\b"
    r"|\[READY:[a-z]+\]"
    r"|\b(?:directive|wave|outcome)\s+(?:\w+\s+)?(?:complete|completed|shipped|done)\b"
    r"|\ball\s+stores?\s+written\b"
    r"|\bfour[-\s]?store\s+save\s+complete\b",
    re.IGNORECASE,
)

# Anti-broadening: exempt past-tense citations / future intent / negation.
_R10_EXEMPT_RE = re.compile(
    r"\b(?:will|going to|about to|planning to)\s+(?:ship|merge|deploy)"
    r"|\bhaven't\s+(?:shipped|merged|deployed)\b"
    r"|\bnot\s+(?:shipped|merged|deployed)\s+yet\b"
    r"|\b(?:retro|review|recap)\b",
    re.IGNORECASE,
)

# KEI tag extraction. Linear's identifier prefix is KEI-<digits>.
_R10_KEI_RE = re.compile(r"\bKEI-\d+\b")


def check_r10(
    text: str,
    *,
    linear_kei_recently_updated: callable = None,
    window_seconds: int = 60,
) -> dict | None:
    """R10 — LINEAR-KEI-GATE.

    Fires when a completion claim (PR merged / [READY:] / sha line / wave done)
    lacks a corresponding Linear KEI status update within `window_seconds`.

    Two failure modes:
      (a) Completion claim with NO KEI-<N> tag → "untaggable, can't verify".
      (b) Completion claim with KEI tag, but Linear shows no recent updatedAt
          mutation on that KEI → "claim without Linear sync".

    `linear_kei_recently_updated(kei_id: str, window_seconds: int) -> bool` is
    injected for testability; default None skips the (b) check entirely (returns
    None for (a)-only mode) so tests can exercise just the pattern logic.
    """
    if not _R10_COMPLETION_RE.search(text):
        return None
    if _R10_EXEMPT_RE.search(text):
        return None
    kei_matches = _R10_KEI_RE.findall(text)

    if not kei_matches:
        return {
            "violation": True,
            "rule_number": 10,
            "rule_name": "LINEAR-KEI-GATE",
            "detail": (
                "Completion claim without KEI-<N> tag — cannot verify Linear sync. "
                "Tag the Linear issue so the orchestrator can mirror state."
            ),
            "should_have": (
                "Include the KEI tag (e.g. 'KEI-17') in the completion message OR "
                "ensure the PR title contains it."
            ),
        }

    if linear_kei_recently_updated is None:
        # No injectable check provided — treat as conservative pass (the tag is
        # present; caller will run the Linear check separately if desired).
        return None

    stale_keis: list[str] = []
    for kei in set(kei_matches):
        try:
            if not linear_kei_recently_updated(kei, window_seconds):
                stale_keis.append(kei)
        except Exception:  # noqa: BLE001 — best-effort; conservative pass on probe failure
            continue
    if not stale_keis:
        return None
    return {
        "violation": True,
        "rule_number": 10,
        "rule_name": "LINEAR-KEI-GATE",
        "detail": (
            f"Completion claim references {', '.join(sorted(stale_keis))} but no "
            f"Linear status update in last {window_seconds}s — sync KEI state."
        ),
        "should_have": (
            "Update the Linear KEI state to Done / In Review / appropriate next state "
            "before posting the completion claim — or within the 60s window after."
        ),
    }


# ---------------------------------------------------------------------------
# R11 — CEO-FORMAT-GATE (Dave directive ts ~1778582530)
# ---------------------------------------------------------------------------
#
# Mechanical enforcement of the #ceo plain-English bullets-only convention.
# Fires on outbound to channel "ceo" (C0B2PM3TV0B) when the body violates the
# format. Pin-discipline isn't enough; this is the runtime gate that blocks
# bad-format posts BEFORE they hit Slack.
#
# Wired into scripts/slack_relay.py main() AFTER concur-gate (so the system-
# generated CONCUR-REQUEST replacements pass through; only original agent text
# is gated).

# Bold category header — markdown ** ** at line start.
_R11_HEADER_RE = re.compile(r"^\s*\*\*[^*]+\*\*", re.MULTILINE)

# Bullet markers: -, *, •, numbered (1.) at line start.
_R11_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+\.)\s+", re.MULTILINE)

# Banned tokens that indicate technical-density (not plain-English):
_R11_BANNED_RES = (
    re.compile(r"\bPR\s*#\d+", re.IGNORECASE),  # PR references
    re.compile(r"\b[a-f0-9]{7,40}\b"),  # commit SHAs
    re.compile(r"\bscripts/[A-Za-z0-9_/.\-]+"),  # file paths under scripts/
    re.compile(r"\bsrc/[A-Za-z0-9_/.\-]+"),  # file paths under src/
    re.compile(r"\.claude/[A-Za-z0-9_/.\-]+"),  # file paths under .claude/
    re.compile(r"\b[A-Z][A-Z_]+_API_KEY\b"),  # env var names ending API_KEY
    re.compile(r"\b[A-Z][A-Z_]+_PROVIDER\b"),  # env var names ending PROVIDER
    re.compile(r"```"),  # code fences
)

# Exempt: system-generated CONCUR-REQUEST replacements (concur_gate output).
_R11_EXEMPT_RE = re.compile(
    r"\[CONCUR-REQUEST:[A-Z]+\]"
    r"|requesting concurrence from peer"
    # KEI-33 — R13 blocker escalation. When slack_relay redirects a
    # [BLOCKED:<callsign>] message from #execution to #ceo, the urgency of
    # the blocker overrides #ceo plain-English format. Exempt so the
    # original blocker payload reaches Dave without format-gate friction.
    r"|\[BLOCKED:[A-Za-z][A-Za-z0-9_-]*\]",
    re.IGNORECASE,
)


def _r11_prose_paragraph_present(text: str) -> bool:
    """Heuristic: any 'line' that's >150 chars AND has 2+ sentences (period followed
    by space) AND has NO bullet marker is a prose paragraph.

    Threshold deliberately conservative — single long bulleted explanation is fine;
    only un-bulleted multi-sentence runs trip the rule.
    """
    for line in text.splitlines():
        s = line.strip()
        if len(s) < 150:
            continue
        if _R11_BULLET_RE.match(line):
            continue
        # Count sentence terminators (period followed by space or end of line).
        # Non-capturing group makes alternation precedence explicit (SonarCloud S5850).
        sentence_count = len(re.findall(r"\.(?:\s+|$)", s))
        if sentence_count >= 2:
            return True
    return False


def check_r11(text: str, *, channel: str | None = None) -> dict | None:
    """R11 — CEO-FORMAT-GATE.

    Fires when:
      - channel is the #ceo channel (C0B2PM3TV0B); AND
      - message body violates the plain-English bullets convention.

    Failure modes:
      (a) Lacks any **bold category header** (markdown ** ** at line start)
      (b) Contains a prose paragraph (>=150 char un-bulleted line with 2+ sentences)
      (c) Contains banned technical tokens: PR #N, commit SHAs, file paths
          under scripts/|src/|.claude/, env var names ending _API_KEY|_PROVIDER,
          code fences ```

    `channel` defaults to None (treat as non-ceo → pass).
    `text` body of the message.

    Returns violation dict with `rule_number=11` + `detail` listing violations,
    or None when channel != ceo OR text is exempt OR text passes all checks.
    """
    CEO_CHANNEL_ID = "C0B2PM3TV0B"
    if channel != CEO_CHANNEL_ID:
        return None
    if _R11_EXEMPT_RE.search(text):
        return None

    violations: list[str] = []

    # (a) Missing bold header
    if not _R11_HEADER_RE.search(text):
        violations.append("no bold category header (**...** at line start)")

    # (b) Prose paragraph
    if _r11_prose_paragraph_present(text):
        violations.append("prose paragraph (un-bulleted line ≥150 chars with 2+ sentences)")

    # (c) Banned technical tokens
    banned_found: list[str] = []
    for pat in _R11_BANNED_RES:
        m = pat.search(text)
        if m:
            banned_found.append(m.group(0)[:30])
    if banned_found:
        violations.append(f"banned technical tokens: {', '.join(banned_found)}")

    if not violations:
        return None

    return {
        "violation": True,
        "rule_number": 11,
        "rule_name": "CEO-FORMAT-GATE",
        "detail": "#ceo post violates plain-English bullets-only convention: "
        + "; ".join(violations),
        "should_have": (
            "Rewrite as: **Bold Category** headers + bullet list (- or •) only. "
            "Lead with OUTCOME + business meaning. No PR numbers, commit SHAs, "
            "file paths, env vars, or code fences. Technical detail stays in "
            "#execution. See feedback_ceo_plain_english_summaries.md."
        ),
    }


# ---------------------------------------------------------------------------
# R14 — ORCHESTRATOR-DISPATCH-DISCIPLINE (KEI-34 component 2)
# ---------------------------------------------------------------------------
#
# Per CEO directive ts ~1778628900 + dual-CTO ratified Step 0 (Max+Elliot
# ts ~1778629820+1778629779): an Elliot post in #execution that enumerates
# idle agents (acknowledgement) MUST also contain a dispatch token in the
# same message body. Strict-zero / inline-token shape parallel to R13.
# Failure to dispatch within the same message → fire to #ceo.
#
# Pass: regex match for any dispatch token in the post body.
# Fail: idle-status acknowledged but no dispatch token → fire.

# Trigger phrases — idle-agent enumeration / acknowledgement patterns.
_R14_IDLE_STATUS_RE = re.compile(
    r"\bidle (?:agents?|clones?)\b"
    r"|\[READY:[a-z]+\]"
    r"|agent(?:s)? idle"
    r"|standing(?:\sby)? (?:on )?(?:agents?|idle)",
    re.IGNORECASE,
)

# Dispatch tokens — markers that the same message body contains a dispatch.
_R14_DISPATCH_TOKEN_RE = re.compile(
    r"\[DISPATCH-PROPOSAL:"
    r"|\[DISPATCH:"
    r"|\bdispatching\b"
    r"|\bEXPLICIT (?:DISPATCH|GO)\b"
    r"|\bbranch\s+[\w/-]+\b"
    r"|\bopen(?:ing)?\s+PR\b"
    r"|\bpicks?\s+up\s+KEI-\d+",
    re.IGNORECASE,
)

# Elliot is the orchestrator under R14 — only Elliot's posts trigger.
_R14_ORCHESTRATOR_CALLSIGN = "elliot"

# Channel id for #execution. Orion's PR #814 R13 introduces a module-level
# EXECUTION_CHANNEL_ID with the same value; this internal duplicate is
# defensive against ordering. If #814 merges first the inline below stays
# private + correct; if this PR merges first #814 reuses its own def.
_R14_EXECUTION_CHANNEL_ID = "C0B3QB0K1GQ"


def check_r14(
    text: str,
    *,
    channel: str | None = None,
    callsign: str | None = None,
) -> dict | None:
    """R14 — ORCHESTRATOR-DISPATCH-DISCIPLINE.

    Strict-zero / inline-token interpretation (dual-CTO ratified):
      - Applies only to messages on #execution (channel id C0B3QB0K1GQ).
      - Applies only to Elliot's posts (orchestrator-specific discipline;
        Aiden/Max/clones don't have orchestrator-dispatch responsibility).
      - Fires when text matches IDLE_STATUS but NOT DISPATCH_TOKEN.
      - No-op for #ceo posts (rule only enforces #execution leak),
        for non-Elliot callsigns, for non-idle messages, and for any
        message outside #execution.

    Returns a violation dict for fire-to-#ceo, or None on pass / no-op.
    """
    if channel != _R14_EXECUTION_CHANNEL_ID:
        return None
    if (callsign or "").lower() != _R14_ORCHESTRATOR_CALLSIGN:
        return None
    if not _R14_IDLE_STATUS_RE.search(text):
        return None
    if _R14_DISPATCH_TOKEN_RE.search(text):
        return None
    return {
        "violation": True,
        "rule_number": 14,
        "rule_name": "ORCHESTRATOR-DISPATCH-DISCIPLINE",
        "detail": "Idle agents enumerated in #execution by Elliot without an "
        "inline dispatch token in the same message body. Dave directive "
        "ts ~1778628900: 'agents should never rely on Elliot to dispatch "
        "routine work — Elliot becomes exception handler only.'",
        "should_have": (
            "Pair the idle-agent acknowledgement with a dispatch in the same "
            "message body (e.g. '[DISPATCH-PROPOSAL:<callsign>] ...', "
            "'Dispatching <callsign> to KEI-NN', 'EXPLICIT DISPATCH ...', "
            "'Branch <name> off main') OR run bd ready + assign-first-unblocked "
            "before posting idle-state."
        ),
        "fire_message": "Idle agents enumerated without dispatch — orchestrator "
        "action gap. [paste message]",
    }


# ---------------------------------------------------------------------------
# R12 — AUTO-KEI ENFORCER (KEI-18 / Linear KEI-18)
# ---------------------------------------------------------------------------
#
# Per CEO directive ts ~1778665700: any CEO directive posted to #ceo that
# does not result in a new Linear KEI within 5 minutes triggers a reminder
# to Elliot to create one. Closes the conversational-directive →
# tracked-work gap.
#
# Detection has two parts:
#   1. is_directive(text) — pattern match for CEO-directive shape
#   2. check_r12(directive_ts, now, linear_keis_since_callback) —
#      fires if 5+ minutes have elapsed and the callback reports no new
#      Linear KEI created in the window.
#
# The polling loop invokes check_r12 against pending directive timestamps
# captured by is_directive. Stateless detector + stateful timer; same
# composition pattern as R13 + R14.

# CEO-directive markers — imperative verbs, urgency keywords, action targets.
# Conservative bias: false-positives on Dave status-questions are
# acceptable (R12 reminder is non-destructive); false-negatives on real
# directives are the failure mode this rule closes.
_R12_DIRECTIVE_PATTERNS: tuple[str, ...] = (
    r"\b(?:URGENT|IMMEDIATELY|NOW)\b",
    r"\b(?:build|ship|deliver|ratify|dispatch|raise|execute|merge|self-merge"
    r"|claim|fix|amend|extend|close|open|push|run|create|file)\b",
    r"\bdrop\s+everything\b",
    r"\b(?:should|must)\s+(?:be\s+)?(?:done|shipped|built|fixed|ratified|merged|closed)\b",
)
_R12_DIRECTIVE_RE = re.compile("|".join(_R12_DIRECTIVE_PATTERNS), re.IGNORECASE)

# Questions are NEVER directives — trailing '?' on the last sentence excludes.
_R12_QUESTION_TAIL_RE = re.compile(r"\?\s*$")

# Dave's Slack user ID. Defensive: any callsign starting with U (Slack user
# ID convention) and matching Dave's specific ID. Falls back to a 'dave'
# callsign for testing convenience.
_R12_CEO_USER_ID = "U091TGTPB9U"
_R12_CEO_CALLSIGN_ALIASES = ("dave", "ceo", _R12_CEO_USER_ID)

# #ceo channel id — channel-gated to the CEO discussion lane only.
_R12_CEO_CHANNEL_ID = "C0B2PM3TV0B"

# 5-minute response window per Dave verbatim.
_R12_KEI_CREATE_WINDOW_SECONDS = 300


def is_r12_directive(
    text: str,
    *,
    channel: str | None = None,
    callsign: str | None = None,
) -> bool:
    """True if the post is a CEO-directive shape in #ceo from Dave.

    Channel-gated to #ceo; callsign-gated to Dave's user_id / 'dave' /
    'ceo'. Pattern match: any of URGENT / imperative-verb / 'drop
    everything' / 'should/must be <action>' AND last sentence is NOT a
    question. Stateless. Used by the polling loop to stamp directive
    timestamps; the 5-min timer + Linear scan is in check_r12.
    """
    if channel != _R12_CEO_CHANNEL_ID:
        return False
    if (callsign or "").lower() not in {a.lower() for a in _R12_CEO_CALLSIGN_ALIASES}:
        return False
    if not text.strip():
        return False
    if _R12_QUESTION_TAIL_RE.search(text):
        return False
    return bool(_R12_DIRECTIVE_RE.search(text))


def check_r12(
    directive_text: str,
    directive_ts: datetime,
    *,
    now: datetime | None = None,
    linear_keis_since_count: int = 0,
    channel: str | None = None,
    callsign: str | None = None,
) -> dict | None:
    """R12 — AUTO-KEI ENFORCER.

    Fires when:
      - directive_text was a CEO directive in #ceo from Dave (is_r12_directive),
      - 5+ minutes have elapsed since directive_ts,
      - linear_keis_since_count == 0 (no new KEI created in the window).

    Returns a violation dict for reminder-post-to-#execution, or None on
    pass / no-op. Caller (polling loop) supplies the Linear count via the
    callback / argument.
    """
    if not is_r12_directive(directive_text, channel=channel, callsign=callsign):
        return None
    n = now or datetime.now(UTC)
    if (n - directive_ts).total_seconds() < _R12_KEI_CREATE_WINDOW_SECONDS:
        return None
    if linear_keis_since_count > 0:
        return None
    return {
        "violation": True,
        "rule_number": 12,
        "rule_name": "AUTO-KEI-ENFORCER",
        "detail": "CEO directive posted to #ceo at "
        f"{directive_ts.isoformat()} without a new Linear KEI created within "
        f"{_R12_KEI_CREATE_WINDOW_SECONDS // 60} minutes. Conversational "
        "directives must land in Linear for tracked-work continuity.",
        "should_have": (
            "Elliot (or any agent the directive targets) creates a Linear KEI "
            "within 5 minutes of the #ceo directive — `bd create` + Linear "
            "sync OR direct Linear GraphQL issueCreate. Use 'orchestration:"
            "directive_NN' ceo_memory anchor if the directive is governance- "
            "or rule-level."
        ),
        "fire_message": (
            f"[R12-REMINDER:elliot] CEO directive at {directive_ts.isoformat()} "
            f"has no Linear KEI after {_R12_KEI_CREATE_WINDOW_SECONDS // 60} "
            "minutes — create one OR confirm directive is informational-only. "
            "Excerpt: [paste first 200 chars of directive_text]"
        ),
    }
