"""Track 6 — universal protocol-tag exempt regression tests.

The universal exempt at the top of run_enforcer() early-returns on ANY message
containing a governance protocol tag. This prevents ALL rule checks from firing
on status, dispatch, and coordination messages.

Post-Track-5 FP analysis (2026-05-12) found 4 FPs — all from messages missing
protocol tags. Track 6 extends the tag list to cover [STATE:], [COMPLETE:],
and [DISPATCH-COMPLETE:] tags that were missing from the original Track 5 set.

We test the compiled regex directly (not via import) because central_listener
depends on slack_sdk which isn't available in the test environment.
"""

from __future__ import annotations

import re

_UNIVERSAL_PROTOCOL_TAG_RE = re.compile(
    r"\[(?:propose|summary-draft|concur-request|concur|ready|busy|fp-log|valid-fire|dispatch|dispatch-proposal|dispatch-complete|state|complete)[\w:-]*\]",
    re.IGNORECASE,
)


def _read_source_regex() -> str:
    """Read the regex from central_listener.py source to verify test stays in sync."""
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "src" / "slack_bot" / "central_listener.py"
    for line in src.read_text().splitlines():
        if "propose|summary-draft|concur-request" in line:
            return line.strip().strip("r\"',")
    return ""


def test_regex_matches_source() -> None:
    """Test regex must match what's in central_listener.py — prevents drift."""
    source_pattern = _read_source_regex()
    assert source_pattern == _UNIVERSAL_PROTOCOL_TAG_RE.pattern, (
        f"Test regex drifted from source.\n  Source: {source_pattern}\n  Test:   {_UNIVERSAL_PROTOCOL_TAG_RE.pattern}"
    )


class TestUniversalProtocolTagExempt:

    def test_propose_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[PROPOSE:max] next work item")

    def test_concur_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[CONCUR:elliot] PR #730")

    def test_concur_request_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[CONCUR-REQUEST:max] merge sweep")

    def test_ready_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[READY:atlas] awaiting dispatch")

    def test_busy_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[BUSY:aiden:pr-review]")

    def test_fp_log_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[FP-LOG:r9] false positive")

    def test_valid_fire_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[VALID-FIRE:r2] actual violation")

    def test_dispatch_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[DISPATCH:elliot] task for atlas")

    def test_dispatch_proposal_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[DISPATCH-PROPOSAL:max] scout audit")

    def test_summary_draft_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[SUMMARY-DRAFT:aiden] day close")

    def test_state_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[STATE:max] 5 PRs merged")

    def test_complete_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[COMPLETE:atlas] task done")

    def test_dispatch_complete_tag(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[DISPATCH-COMPLETE:elliot] batch")

    def test_state_tag_case_insensitive(self) -> None:
        assert _UNIVERSAL_PROTOCOL_TAG_RE.search("[state:max] lower case")

    def test_plain_text_no_match(self) -> None:
        assert not _UNIVERSAL_PROTOCOL_TAG_RE.search("shipped PR #720 to main")

    def test_random_brackets_no_match(self) -> None:
        assert not _UNIVERSAL_PROTOCOL_TAG_RE.search("[MAX] random message")

    def test_callsign_only_no_match(self) -> None:
        assert not _UNIVERSAL_PROTOCOL_TAG_RE.search("[ELLIOT] status update")
