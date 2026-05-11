"""Regression tests for `_R9_EXEMPT_RE` in src/slack_bot/central_listener.py.

Locks the post-LLM R9 exempt regex after PR #710 (Max) broadened it to
cover all structured protocol tags (propose, ready, busy, concur,
concur-request, fp-log, valid-fire, dispatch).

Backport of test set Elliot drafted in deleted branch
elliot/r9-busy-ready-exempt (SHA 71cb3748, see #execution audit trail
2026-05-11). Empirical 24h FP validation served as de-facto regression
when PR #710 shipped without tests; this PR locks the regex shape so a
future regression can't silently re-introduce the FP class.
"""

from __future__ import annotations

import sys
import types

# central_listener.py imports slack_sdk at module level, but the test target
# (_R9_EXEMPT_RE) has no Slack runtime dependency. Stub slack_sdk before
# import so the module loads in test environments without the SDK installed.
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

from src.slack_bot.central_listener import _R9_EXEMPT_RE  # noqa: E402


def test_propose_tag_exempt() -> None:
    """[PROPOSE:callsign] tag → R9 exempt."""
    assert _R9_EXEMPT_RE.search("[PROPOSE:AIDEN] open new branch and ship it")


def test_ready_tag_exempt() -> None:
    """[READY:callsign] status close tag → R9 exempt."""
    assert _R9_EXEMPT_RE.search("[READY:aiden] PR merged, standing down.")


def test_busy_tag_with_nested_task_id_exempt() -> None:
    """[BUSY:callsign:task-id] with colon-and-hyphen task id → R9 exempt.

    Locks the `[\\w:-]*` post-colon pattern that was absent from the
    pre-#710 regex (which only had `\\w+`).
    """
    assert _R9_EXEMPT_RE.search(
        "[BUSY:aiden:dispatch-batch-2026-05-11-20:40] working both discussions"
    )


def test_concur_tag_exempt() -> None:
    """[CONCUR:peer] tag → R9 exempt."""
    assert _R9_EXEMPT_RE.search("[CONCUR:elliot] PR #710 verified")


def test_concur_request_tag_exempt() -> None:
    """[CONCUR-REQUEST:callsign] tag → R9 exempt."""
    assert _R9_EXEMPT_RE.search("[CONCUR-REQUEST:AIDEN] requesting concurrence from peer on: ...")


def test_fp_log_tag_exempt() -> None:
    """[FP-LOG:rule-N] meta-log tag → R9 exempt."""
    assert _R9_EXEMPT_RE.search("[FP-LOG:R9] post-restart fire #3")


def test_valid_fire_tag_exempt() -> None:
    """[VALID-FIRE:rule-N] meta-log tag → R9 exempt."""
    assert _R9_EXEMPT_RE.search("[VALID-FIRE:R3] genuine completion claim missing evidence")


def test_dispatch_proposal_tag_exempt() -> None:
    """[DISPATCH-PROPOSAL:callsign] tag → R9 exempt."""
    assert _R9_EXEMPT_RE.search(
        "[DISPATCH-PROPOSAL:AIDEN] dispatching Orion ping per Dave directive #8"
    )


def test_case_insensitive() -> None:
    """Tag matching is case-insensitive (Slack inbound has mixed case)."""
    assert _R9_EXEMPT_RE.search("[propose:aiden] lowercase")
    assert _R9_EXEMPT_RE.search("[PROPOSE:AIDEN] uppercase")
    assert _R9_EXEMPT_RE.search("[Propose:Aiden] mixed")


def test_next_action_subject_exempt() -> None:
    """`I'll/will <verb>` next-action subjects → R9 exempt."""
    assert _R9_EXEMPT_RE.search("Aiden will ship the regex tweak this hour.")
    assert _R9_EXEMPT_RE.search("I'll merge once CI greens.")
    assert _R9_EXEMPT_RE.search("Elliot will rebase prime.")


def test_at_mention_action_exempt() -> None:
    """`@callsign ships/drops/owns` action mention → R9 exempt."""
    assert _R9_EXEMPT_RE.search("@max ships PR #710 on CI green.")
    assert _R9_EXEMPT_RE.search("@aiden owns the FP tally.")


def test_at_mention_rollup_exempt() -> None:
    """`@callsign — roll-up/audit/review/own/next` → R9 exempt."""
    assert _R9_EXEMPT_RE.search("@elliot — roll-up to Dave please.")
    assert _R9_EXEMPT_RE.search("@max — audit pending.")


def test_anti_broadening_dave_directed_agenda() -> None:
    """Genuine Dave-directed agenda-setting → NOT exempt (R9 should still fire)."""
    assert not _R9_EXEMPT_RE.search("Dave, what should we do next?")
    assert not _R9_EXEMPT_RE.search("Dave — your call on whether to proceed with the migration.")
    assert not _R9_EXEMPT_RE.search("Holding pattern indefinitely, awaiting CEO guidance.")


def test_anti_broadening_random_brackets() -> None:
    """Random bracketed text that isn't a protocol tag → NOT exempt."""
    assert not _R9_EXEMPT_RE.search("[random] should not exempt.")
    assert not _R9_EXEMPT_RE.search("[note: something] should not exempt.")
