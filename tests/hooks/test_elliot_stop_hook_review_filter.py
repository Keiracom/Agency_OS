"""Tests for the #ceo review-chatter filter in elliot_stop_hook.classify().

Dave directive 2026-05-20: review-nudge / PR-HOLD / review-status chatter must
NOT reach #ceo (that belongs in #execution). #ceo keeps only merge-completed
outcomes, blockers needing Dave, and Dave-decisions. classify() suppresses
review-process turns before they trip the completion / merge_ready / blocker
classifiers.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "hooks" / "elliot_stop_hook.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("elliot_stop_hook", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["elliot_stop_hook"] = m
    spec.loader.exec_module(m)
    return m


# --- review-process chatter → SUPPRESSED (kind is None) ---------------------


@pytest.mark.parametrize(
    "text",
    [
        "[NEXT-WORK:elliot] FIX your own 2 blocked PRs first: [1104, 1105] — "
        "then review 3 PRs awaiting your verdict: [1100, 1102, 1106].",
        "You have REVIEW-PR-1106 claimed. Resume building. Title: Review PR #1106.",
        "Posted [REVIEW:orion] APPROVE on PR #1105 after dual-Sonar check — clean.",
        "PR #1102 is on HOLD — reviewer verdict from Aiden pending, dispatched "
        "the author to push a fix-up.",
        "[FIXED:orion] PR #1104 fix-up pushed; CI re-running, awaiting your verdict.",
        "PR-HOLD on #1100 — review-status: 1 approve, 1 hold, needs round-2 concur.",
    ],
)
def test_review_chatter_is_suppressed(mod, text):
    kind, _ = mod.classify(text + " " * 30, verbosity="chatty")
    assert kind is None, f"review chatter must be suppressed, got kind={kind!r}"


# --- genuine outcomes → STILL POST ------------------------------------------


def test_merge_completed_outcome_still_posts(mod):
    """A real merge-completed outcome carries no review-process marker — keep it."""
    text = (
        "Orchestrator remediation merged to main — fleet-supervisor re-enabled, "
        "IDENTITY.md bootstrap shipped. All four audit items closed and deployed."
    )
    kind, _ = mod.classify(text, verbosity="quiet")
    assert kind in ("completion", "merge_ready"), f"merge outcome must post, got {kind!r}"


def test_genuine_incident_still_posts(mod):
    text = "The cognee indexer service crashed and the ingest pipeline is stalled."
    kind, _ = mod.classify(text, verbosity="quiet")
    assert kind == "incident"


def test_genuine_blocker_still_posts(mod):
    """A real CEO-blocker with no review-process markers still classifies."""
    text = (
        "Blocked on a vendor decision — need your call on whether to pay for the "
        "Salesforge Growth tier before the validation run can proceed."
    )
    kind, _ = mod.classify(text, verbosity="quiet")
    assert kind == "blocker"
