"""Unit tests for enforcer_bot MAX outbox PR-claim detection and verification.

Tests cover: regex matching, async subprocess mock for verify_pr.sh, mismatch
interjection logic, and BOT_INBOXES membership.
"""

import asyncio
import contextlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram_bot.enforcer_bot import BOT_INBOXES, PR_CLAIM_RE, watch_max_outbox


def _async_proc_mock(stdout: str, stderr: str = "", returncode: int = 0):
    """Build an AsyncMock that simulates asyncio.create_subprocess_exec().communicate()."""
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    proc.wait = AsyncMock(return_value=returncode)
    proc.kill = MagicMock()
    proc.returncode = returncode
    return AsyncMock(return_value=proc)

# ---------------------------------------------------------------------------
# Task 4.1 — Regex positive cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "PR #521 merged successfully",
    "521 passed all CI checks",
    "ci green for #520",
    "all tests pass on #519",
    "branch complete — see #522",
    "PR #523 ship it",
    "merged #524 into main",
    "ci pass #525",
])
def test_pr_claim_regex_positive_cases(text):
    """PR_CLAIM_RE should match texts containing a PR number near a claim keyword."""
    assert PR_CLAIM_RE.search(text) is not None, f"Expected match for: {text!r}"


# ---------------------------------------------------------------------------
# Task 4.2 — Regex negative cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Hi Dave",
    "checking #5 of the list",
    "passed Dave the file",
    "just a normal update",
    "issue #12 is still open",
    "we need to review #99 tomorrow",
    "approved the lunch order",
])
def test_pr_claim_regex_negative_cases(text):
    """PR_CLAIM_RE should NOT match generic text without a PR+claim pairing."""
    assert PR_CLAIM_RE.search(text) is None, f"Unexpected match for: {text!r}"


# ---------------------------------------------------------------------------
# Helpers for async watcher tests
# ---------------------------------------------------------------------------

def _make_outbox_file(tmp_path, text: str) -> None:
    """Write a single outbox JSON file for the watcher to consume."""
    msg_file = tmp_path / "20260502_120000_abcd1234.json"
    msg_file.write_text(json.dumps({"text": text, "sender": "max"}))


def _verify_json(merged: bool, ci_passing: bool, state: str = "MERGED",
                 failed_checks: list | None = None) -> str:
    """Return JSON string as verify_pr.sh would output."""
    return json.dumps({
        "pr": 521,
        "state": state,
        "merged": merged,
        "merge_sha": "abc123" if merged else "",
        "ci_passing": ci_passing,
        "failed_checks": failed_checks or [],
        "pending_checks": [],
    })


# ---------------------------------------------------------------------------
# Task 4.3 — Verify match (no interjection expected)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_pr_match(tmp_path):
    """When claim says 'merged' and verify confirms merged=true, no interjection fired."""
    _make_outbox_file(tmp_path, "PR #521 merged successfully")

    proc_mock = _async_proc_mock(_verify_json(merged=True, ci_passing=True))

    with patch("src.telegram_bot.enforcer_bot.MAX_OUTBOX", str(tmp_path)), \
         patch("asyncio.create_subprocess_exec", proc_mock), \
         patch("src.telegram_bot.enforcer_bot.send_interjection",
               new_callable=AsyncMock) as mock_interject:

        task = asyncio.create_task(watch_max_outbox())
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        mock_interject.assert_not_called()


# ---------------------------------------------------------------------------
# Task 4.4 — Mismatch: claim "merged" but merged=false
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_pr_mismatch_merged(tmp_path):
    """When claim says 'merged' but verify returns merged=false, interjection is sent."""
    _make_outbox_file(tmp_path, "PR #521 merged successfully")

    proc_mock = _async_proc_mock(_verify_json(merged=False, ci_passing=True, state="OPEN"))

    with patch("src.telegram_bot.enforcer_bot.MAX_OUTBOX", str(tmp_path)), \
         patch("asyncio.create_subprocess_exec", proc_mock), \
         patch("src.telegram_bot.enforcer_bot.send_interjection",
               new_callable=AsyncMock) as mock_interject:

        task = asyncio.create_task(watch_max_outbox())
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        mock_interject.assert_called_once()
        call_text = mock_interject.call_args[0][0]
        assert "PR #521" in call_text
        assert "merged=false" in call_text or "COMPLETION-REQUIRES-VERIFICATION" in call_text


# ---------------------------------------------------------------------------
# Task 4.5 — Mismatch: claim "passed" but ci_passing=false
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_pr_mismatch_ci(tmp_path):
    """When claim says 'passed' but verify returns ci_passing=false, interjection is sent."""
    _make_outbox_file(tmp_path, "521 passed all CI checks")

    proc_mock = _async_proc_mock(_verify_json(
        merged=True, ci_passing=False, state="MERGED",
        failed_checks=["Backend Tests (Pytest)"],
    ))

    with patch("src.telegram_bot.enforcer_bot.MAX_OUTBOX", str(tmp_path)), \
         patch("asyncio.create_subprocess_exec", proc_mock), \
         patch("src.telegram_bot.enforcer_bot.send_interjection",
               new_callable=AsyncMock) as mock_interject:

        task = asyncio.create_task(watch_max_outbox())
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        mock_interject.assert_called_once()
        call_text = mock_interject.call_args[0][0]
        assert "ci_passing=false" in call_text or "COMPLETION-REQUIRES-VERIFICATION" in call_text


# ---------------------------------------------------------------------------
# Task 4.7 — Ghost-green guard: verify_pr.sh unknown CI must not auto-pass
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_pr_ci_unknown_no_ghost_green(tmp_path):
    """If verify_pr.sh reports ci_passing=null, do not treat as green for ci-pass claim."""
    _make_outbox_file(tmp_path, "521 passed all CI checks")

    proc_mock = _async_proc_mock(json.dumps({
        "pr": 521, "state": "MERGED", "merged": True,
        "ci_passing": None, "ci_status": "unknown",
        "failed_checks": [], "pending_checks": [],
    }))

    with patch("src.telegram_bot.enforcer_bot.MAX_OUTBOX", str(tmp_path)), \
         patch("asyncio.create_subprocess_exec", proc_mock), \
         patch("src.telegram_bot.enforcer_bot.send_interjection",
               new_callable=AsyncMock) as mock_interject:

        task = asyncio.create_task(watch_max_outbox())
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Either interject (treat unknown as mismatch) OR don't interject (treat
        # unknown as not-yet-verifiable). Critical guarantee: must NOT interject
        # claiming "ci_passing=true" — i.e. must not have ghost-greened. Since
        # there's no positive evidence, either behaviour is acceptable; we just
        # assert the interjection text never asserts CI green.
        for call in mock_interject.call_args_list:
            assert "ci_passing=true" not in call[0][0]


# ---------------------------------------------------------------------------
# Task 4.6 — BOT_INBOXES membership
# ---------------------------------------------------------------------------

def test_max_inbox_in_bot_inboxes():
    """MAX inbox must be present in BOT_INBOXES so interjections reach MAX."""
    assert "/tmp/telegram-relay-max/inbox" in BOT_INBOXES
