"""Tests for scripts/classifier/discovery_log_classifier.py — Phase 1.2.5 artefact 5.

Negative-path discipline (Max review pattern per feedback_negative_path_test_before_approve):
classifier is a heuristic gate — tests must prove both positive (known-bucket
entry classified correctly) AND negative (ambiguous → manual-review) paths,
plus idempotency (re-run produces same classification, no drift).

6 test cases:
  (1) test_classify_known_fleet_entry — relay/tmux content → 'fleet'
  (2) test_classify_known_product_entry — keiracom chat content → 'product'
  (3) test_classify_known_archive_entry — Siege Waterfall / T0-T5 content → 'archive'
  (4) test_classify_known_cross_product_entry — separation directive content → 'cross-product'
  (5) test_classify_ambiguous_routes_to_manual_review — empty/no-keyword content → 'manual-review'
  (6) test_classify_all_is_idempotent — re-running classify_all on annotated entries does not change them
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "classifier"))

import discovery_log_classifier as clf  # noqa: E402


def test_classify_known_fleet_entry():
    """(1) — relay_watcher + tmux + session-name content → 'fleet'."""
    entry = {
        "agent": "aiden",
        "kei": "KEI-99",
        "context": "relay_watcher.sh hardcoded TMUX_TARGET silently drops messages",
        "finding": "tmux has-session liveness check is the right pattern",
        "failed_path": "branch on send-keys exit code",
        "verified_path": "priority candidate list + tmux has-session check",
        "tags": ["relay", "tmux", "session-name", "resilience"],
    }
    result = clf.classify(entry)
    assert result["label"] == "fleet", f"expected fleet, got {result}"
    assert result["scores"]["fleet"] > 0
    assert "relay" in result["matched_keywords"]


def test_classify_known_product_entry():
    """(2) — Keiracom chat / dashboard / MAL content → 'product'."""
    entry = {
        "agent": "elliot",
        "kei": "KEI-MAL-V1",
        "context": "Keiracom chat product spec — memory abstraction layer recall routing",
        "finding": "MAL V1 routes recall by context tag; tenant_isolation gate",
        "verified_path": "Hindsight self-hosted in tenant VPCs as the memory engine",
        "tags": ["keiracom_chat", "memory_abstraction_layer", "hindsight", "tenant-isolation"],
    }
    result = clf.classify(entry)
    assert result["label"] == "product", f"expected product, got {result}"
    assert result["scores"]["product"] >= 2


def test_classify_known_archive_entry():
    """(3) — Siege Waterfall / T0-T5 / Bright Data content → 'archive'."""
    entry = {
        "agent": "orion",
        "kei": "KEI-AGENCY-OS-PIPELINE",
        "context": "Siege Waterfall t1.5 LinkedIn company tier failing on Bright Data 504s",
        "finding": "Flow B asyncio.gather of t1.5 + t2 GMB + t3 email tiers needs retry",
        "verified_path": "T0 discovery + ABN match feeds Flow A; t-DM tier gates",
        "tags": ["siege_waterfall", "bright data", "flow b", "t1.5 linkedin"],
    }
    result = clf.classify(entry)
    assert result["label"] == "archive", f"expected archive, got {result}"
    assert result["scores"]["archive"] >= 2


def test_classify_known_cross_product_entry():
    """(4) — separation directive / agency_os_keiracom content → 'cross-product'."""
    entry = {
        "agent": "viktor",
        "kei": "KEI-SEPARATION-V1",
        "context": "Phase 1.2.5 bundle — 3-repo topology splits agency_os_keiracom into fleet + product + archive",
        "finding": "separation directive ratified by Dave; phase 2.0 carves fresh product repo",
        "tags": ["separation directive", "agency_os_keiracom", "phase 1.2.5", "3-repo"],
    }
    result = clf.classify(entry)
    assert result["label"] == "cross-product", f"expected cross-product, got {result}"


def test_classify_ambiguous_routes_to_manual_review():
    """(5) — no keyword hits → 'manual-review' with reason='no_keyword_hits'."""
    entry = {
        "agent": "unknown",
        "context": "Some entirely unrelated content with no domain markers",
        "finding": "A finding that does not match any bucket vocabulary",
        "tags": ["abc", "xyz"],
    }
    result = clf.classify(entry)
    assert result["label"] == "manual-review"
    assert result["reason"] == "no_keyword_hits"
    assert result["matched_keywords"] == []


def test_classify_all_is_idempotent():
    """(6) — classify_all on already-annotated entries produces no change.

    Per dispatch: 'Idempotency: re-running produces same classification.'
    Annotated entries get skipped on re-run unless --reclassify is set.
    """
    entries = [
        {"context": "relay tmux nats", "tags": ["fleet-ish"]},
        {"context": "keiracom_chat workforce", "tags": ["product-ish"]},
    ]
    first_pass = clf.classify_all(entries)
    # Capture the classification objects
    first_labels = [e["classification"]["label"] for e in first_pass]
    # Re-run on the annotated list
    second_pass = clf.classify_all(first_pass)
    second_labels = [e["classification"]["label"] for e in second_pass]
    assert first_labels == second_labels, (
        f"idempotency broken: first={first_labels}, second={second_labels}"
    )
    # And the classification object is byte-for-byte preserved (no re-classification)
    assert first_pass[0]["classification"] is second_pass[0]["classification"], (
        "second pass should not have replaced the classification object"
    )


def test_classify_all_reclassify_overrides_existing():
    """(6b) — --reclassify forces re-classification even on annotated entries.

    Inverse of (6) — proves the override flag works when needed (e.g. keyword
    list updated and operator wants fresh classifications).
    """
    annotated = [
        {
            "context": "relay tmux nats",
            "classification": {"label": "manual-review", "reason": "stale_test_data"},
        },
    ]
    result = clf.classify_all(annotated, reclassify=True)
    assert result[0]["classification"]["label"] == "fleet", (
        f"reclassify should override; got {result[0]['classification']}"
    )


def test_combine_text_handles_missing_fields():
    """combine_text robustly handles entries missing any field set."""
    assert clf.combine_text({}) == ""
    assert clf.combine_text({"context": "hello"}) == "hello"
    # tags are stringified + joined
    text = clf.combine_text({"context": "x", "tags": ["a", "b"]})
    assert "x" in text and "a" in text and "b" in text


def test_summarise_counts_labels():
    """summarise returns a Counter keyed by classification label."""
    entries = [
        {"classification": {"label": "fleet"}},
        {"classification": {"label": "fleet"}},
        {"classification": {"label": "product"}},
        {"classification": {"label": "manual-review"}},
        {},  # no classification key — should be skipped
    ]
    counts = clf.summarise(entries)
    assert counts["fleet"] == 2
    assert counts["product"] == 1
    assert counts["manual-review"] == 1
    assert sum(counts.values()) == 4
