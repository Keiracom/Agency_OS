"""Regression tests for Track 5 enforcer FP-tuning follow-up (2026-05-11).

Two fixes per Max's post-Track-4 FP trace:
  1. R2 exempt regex extension — adds "merged and verified" + "merged at <ISO>"
     + "mergeCommit" patterns. Closes the verification-style FP class that
     fired on Max's 23:23:13 status post.
  2. R8 conditional extension — adds COO/CTO own-clone dispatch exempt
     + Dave-authorized cross-dispatch exempt. Closes the FP on Elliot's
     Atlas dispatch at 23:32 UTC under Dave's CEO-delegated authority.

Per Max + Elliot identification, post-merge-and-deploy these two fixes should
close the remaining post-Track-4 FP classes (R2 2-fire class + R8 1-fire class).
"""

from __future__ import annotations

from src.bot_common.enforcer_deterministic import (
    _R2_EXEMPT_RE,
    _R8_CONDITIONAL_RE,
    check_r2,
    check_r8,
)

# ─────────────────────────────────────────────────────────────────────────────
# R2 — Track 5 verification-style exempts
# ─────────────────────────────────────────────────────────────────────────────


def test_r2_exempt_merged_and_verified() -> None:
    """`merged and verified` — Max's flagged FP class."""
    assert _R2_EXEMPT_RE.search("PRs #715 and #716 both merged and verified")


def test_r2_exempt_merged_at_iso_timestamp() -> None:
    """`merged at 2026-05-11T...` — JSON-shape mergedAt value."""
    text = "PR #715 merged at 2026-05-11T23:21:31Z"
    assert _R2_EXEMPT_RE.search(text)


def test_r2_exempt_mergeCommit_keyword() -> None:
    """`mergeCommit` — gh JSON output field."""
    assert _R2_EXEMPT_RE.search("Verified mergeCommit oid 286b4f0d")


def test_r2_check_passes_on_verification_style_post() -> None:
    """End-to-end: Max's actual 23:23:13 post phrasing → check_r2 PASS."""
    text = "Confirmed — PRs #715 and #716 both merged and verified"
    assert check_r2(text, recent_messages=[]) is None


def test_r2_check_still_fires_on_bare_completion_claim() -> None:
    """Anti-broadening: bare 'merged' without verification/timestamp/JSON STILL fires R2."""
    text = "All shipped to main, deployed, merged everything."
    result = check_r2(text, recent_messages=[])
    assert result is not None
    assert result["rule_number"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# R8 — Track 5 COO/CTO own-clone dispatch + Dave-authorized exempts
# ─────────────────────────────────────────────────────────────────────────────


def test_r8_exempt_elliot_dispatched_atlas() -> None:
    """Elliot dispatched her own clone Atlas — operationally normal."""
    text = "Elliot dispatched atlas at 23:32 per Dave directive #8"
    assert _R8_CONDITIONAL_RE.search(text)
    assert check_r8(text, recent_messages=[]) is None


def test_r8_exempt_aiden_dispatched_orion() -> None:
    """Aiden dispatched her own clone Orion."""
    text = "aiden dispatched orion rebase task for PR #713"
    assert _R8_CONDITIONAL_RE.search(text)


def test_r8_exempt_dave_authorized() -> None:
    """Dave-authorized cross-dispatch (CEO override)."""
    text = "dave-authorized cross-dispatch override for Atlas+Orion ping audit"
    assert _R8_CONDITIONAL_RE.search(text)


def test_r8_exempt_dave_directive_reference() -> None:
    """Reference to a Dave directive in the dispatch context."""
    text = "Dispatched per Dave directive #8 — attribution audit."
    assert _R8_CONDITIONAL_RE.search(text)


def test_r8_exempt_ceo_delegated() -> None:
    """CEO-delegated dispatch authority."""
    text = "Dispatched atlas under ceo-delegated authority"
    assert _R8_CONDITIONAL_RE.search(text)


def test_r8_still_fires_on_unauthorized_cross_dispatch() -> None:
    """Anti-broadening: a clone-to-clone dispatch with no CEO authority STILL needs proposal."""
    text = "Aiden dispatched atlas without coordination."
    # Aiden→atlas is cross-dispatch (not own clone). No Dave/CEO authority in text.
    # R8 should still flag this for proposal/concur.
    assert not _R8_CONDITIONAL_RE.search(text)
