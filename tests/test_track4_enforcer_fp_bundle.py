"""Regression tests for Track 4 enforcer FP-tuning bundle (2026-05-11).

Three fixes covered:
  1. R2 exempt regex extension — adds [concur:|ready:|busy:|fp-log:|valid-fire:
     |dispatch:|dispatch-proposal:] to the exempt set (mirror PR #710's R9
     superset). Closes R2 ×6 FPs this session on status posts containing
     merge/ship keywords.
  2. R3 post-LLM evidence exempt — suppress LLM-hallucinated R3 fires on
     messages that contain commit hashes, PR refs, gh CLI output, test counts.
     Closes the LLM-hallucination class that PR #714's r3_skip short-circuit
     doesn't cover.
  3. R8 conditional-language fix — `\bdispatch(ing)?\b` over-matched on offers
     ("I can dispatch", "will dispatch if you confirm"). Tightened to past-tense
     /completed-action verbs; conditional clause exempts the trigger.

Per Elliot dispatch ts 1778540XXX (Track 4 bundle queued behind PR-A
opens-for-concur).
"""

from __future__ import annotations

import re
import sys
import types

from src.bot_common.enforcer_deterministic import (
    _R2_EXEMPT_RE,
    _R8_CONDITIONAL_RE,
    _R8_DISPATCH_RE,
    check_r2,
    check_r8,
)

# Stub slack_sdk for _R3_LLM_EVIDENCE_RE import (same shim pattern as PR #711)
for mod_name in (
    "slack_sdk",
    "slack_sdk.socket_mode",
    "slack_sdk.socket_mode.request",
    "slack_sdk.socket_mode.response",
    "slack_sdk.web",
):
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))
sys.modules["slack_sdk.socket_mode"].SocketModeClient = type("SocketModeClient", (), {})  # type: ignore[attr-defined]
sys.modules["slack_sdk.socket_mode.request"].SocketModeRequest = type("SocketModeRequest", (), {})  # type: ignore[attr-defined]
sys.modules["slack_sdk.socket_mode.response"].SocketModeResponse = type(
    "SocketModeResponse", (), {}
)  # type: ignore[attr-defined]
sys.modules["slack_sdk.web"].WebClient = type("WebClient", (), {})  # type: ignore[attr-defined]

from src.bot_common.enforcer_deterministic import _R3_EVIDENCE_RE  # noqa: E402
from src.slack_bot.central_listener import _R3_LLM_EVIDENCE_EXTRAS_RE  # noqa: E402


def _r3_post_llm_match(text: str) -> bool:
    """Mirror central_listener.run_enforcer's post-LLM R3 evidence check."""
    return bool(_R3_EVIDENCE_RE.search(text) or _R3_LLM_EVIDENCE_EXTRAS_RE.search(text))


# ─────────────────────────────────────────────────────────────────────────────
# R2 exempt regex — protocol-tag coverage
# ─────────────────────────────────────────────────────────────────────────────


def test_r2_exempt_propose_tag() -> None:
    assert _R2_EXEMPT_RE.search("[PROPOSE:AIDEN] merge PR #710 on green")


def test_r2_exempt_ready_tag() -> None:
    assert _R2_EXEMPT_RE.search("[READY:aiden] PR merged, standing down.")


def test_r2_exempt_busy_nested_task_id() -> None:
    assert _R2_EXEMPT_RE.search("[BUSY:aiden:dispatch-batch-2026-05-11-20:40] working")


def test_r2_exempt_concur_tag() -> None:
    assert _R2_EXEMPT_RE.search("[CONCUR:elliot] PR #710 verified, merging")


def test_r2_exempt_fp_log_tag() -> None:
    assert _R2_EXEMPT_RE.search("[FP-LOG:R9] post-restart fire on shipping claim")


def test_r2_exempt_dispatch_proposal_tag() -> None:
    assert _R2_EXEMPT_RE.search("[DISPATCH-PROPOSAL:AIDEN] Orion rebase task per Elliot")


def test_r2_check_passes_when_protocol_tag_present() -> None:
    """End-to-end: text with execution language + protocol tag → check_r2 PASS."""
    text = "[READY:aiden] merged PR #710 to main, deployment done."
    assert check_r2(text, recent_messages=[]) is None


def test_r2_check_still_fires_on_unprotected_execution() -> None:
    """Anti-broadening: text with execution language but NO protocol tag + NO Step 0 in
    recent_messages → still fires R2."""
    text = "Shipping PR #999 now, deployed to main, merged everything."
    result = check_r2(text, recent_messages=[])
    assert result is not None
    assert result["rule_number"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# R8 conditional-language fix
# ─────────────────────────────────────────────────────────────────────────────


def test_r8_conditional_can_dispatch_exempt() -> None:
    """`I can dispatch` is an offer, not an action."""
    text = "I can dispatch Orion to do it if you confirm."
    assert _R8_CONDITIONAL_RE.search(text)
    # check_r8 should return None (no violation) even though "dispatch" appears
    assert check_r8(text, recent_messages=[]) is None


def test_r8_conditional_will_dispatch_if_exempt() -> None:
    text = "Will dispatch if Elliot confirms the rebase plan."
    assert _R8_CONDITIONAL_RE.search(text)


def test_r8_does_not_fire_on_gerund_alone() -> None:
    """Bare 'dispatching' (gerund) without past-tense/completed-action should NOT match.

    Prior version had `dispatching now` which matched; tightened to require
    `firing dispatch now` or `dispatch fired` instead.
    """
    assert not _R8_DISPATCH_RE.search("dispatching the task takes ~30s")


def test_r8_fires_on_past_tense() -> None:
    """`dispatched` (past tense) IS an action — should match."""
    assert _R8_DISPATCH_RE.search("Atlas dispatched the ping per Dave directive #8")


def test_r8_fires_on_imperative_now() -> None:
    """`firing dispatch now` is imperative + completed-action — should match."""
    assert _R8_DISPATCH_RE.search("firing dispatch now to Orion's inbox")


# ─────────────────────────────────────────────────────────────────────────────
# R3 LLM-evidence exempt
# ─────────────────────────────────────────────────────────────────────────────


def test_r3_llm_evidence_commit_hash() -> None:
    assert _r3_post_llm_match("commit 6a3661b1 verified")


def test_r3_llm_evidence_pr_ref() -> None:
    assert _r3_post_llm_match("PR #715 open with all CI green")


def test_r3_llm_evidence_gh_json_state() -> None:
    assert _r3_post_llm_match('{"state":"MERGED","mergeCommit":{"oid":"abc123"}}')


def test_r3_llm_evidence_pytest_count() -> None:
    assert _r3_post_llm_match("14 passed in 0.18s")


def test_r3_llm_evidence_ci_success() -> None:
    assert _r3_post_llm_match("CI: ALL SUCCESS\nDead Reference Guard")


def test_r3_llm_evidence_terminal_prefix() -> None:
    # Multiline mode required for ^ to match line starts
    pat = re.compile(r"^[\$>→]", re.MULTILINE)
    assert pat.search("Something then\n$ gh pr view 715")


def test_r3_llm_evidence_gh_cli() -> None:
    assert _r3_post_llm_match("$ gh pr view 715 --json state")


def test_r3_llm_evidence_no_match_on_bare_dave_directed() -> None:
    """Anti-broadening: a real R3-violation candidate (no evidence) should NOT match."""
    assert not _r3_post_llm_match("Dave, the task is complete.")
    assert not _r3_post_llm_match("Done!")
