"""Tests for KEI-55 discovery validation governance.

Covers:
  AC1 — schema defines 12 governance properties
  AC2 — Tier 1 auto-promote after 24h expiry
  AC3 — Tier 2 concur enforcement
  AC4 — Tier 3 Dave notification on creation
  AC5 — Staleness flag injection (KEI-58)
  AC6 — Challenge state transition
  AC7 — 500-token ceiling enforcement
  AC8 — Staging and expired exclusion in claim injection
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from infra.weaviate.staging_schema import (
    _CLASS_DEFINITION,
    MANDATORY_PROPERTIES,
    STAGING_CLASS,
    STAGING_PROPERTIES,
)
from src.governance.claim_injection import render_for_claim
from src.governance.discovery_validation import (
    challenge,
    classify_tier,
    expire_stale_staging,
    promote_to_permanent,
    submit_concur,
    submit_discovery,
)

# ============================================================================
# AC1 — Schema properties exist
# ============================================================================


def test_ac1_staging_schema_has_mandatory_properties() -> None:
    """AC1: staging schema includes 5 mandatory properties from schema.py."""
    mandatory_names = {p["name"] for p in MANDATORY_PROPERTIES}
    assert mandatory_names == {"raw_text", "environment_hash", "created_at", "agent", "kei"}


def test_ac1_staging_schema_has_12_governance_properties() -> None:
    """AC1: staging schema includes 12 governance properties for tier workflow."""
    governance_names = {p["name"] for p in STAGING_PROPERTIES}
    expected = {
        "validation_tier",
        "tier_classification_reason",
        "state",
        "concur_callsign",
        "concur_at",
        "challenged_by",
        "challenged_at",
        "tier_3_dave_notified_at",
        "submitted_by",
        "expires_at",
        "context_version",
        "counter_findings",
    }
    assert governance_names == expected, (
        f"governance properties mismatch; got {governance_names}, expected {expected}"
    )


def test_ac1_class_definition_combines_mandatory_and_governance() -> None:
    """AC1: class definition includes all properties."""
    props = _CLASS_DEFINITION["properties"]
    prop_names = {p["name"] for p in props}
    assert len(prop_names) == 17
    assert _CLASS_DEFINITION["class"] == STAGING_CLASS


# ============================================================================
# AC2 — Tier 1 auto-promote after 24h expiry
# ============================================================================


@patch("src.governance.discovery_validation.promote_to_permanent")
@patch("src.governance.discovery_validation._query_staging_objects")
def test_ac2_tier1_auto_promote_on_expiry(
    mock_query: MagicMock,
    mock_promote: MagicMock,
) -> None:
    """AC2: tier-1 discoveries past expiry are auto-promoted."""
    now = datetime.now(UTC)
    past = now - timedelta(hours=1)

    # Mock a tier-1 staging discovery with expired timestamp.
    mock_query.return_value = [
        {
            "id": "test-id-123",
            "properties": {
                "state": "staging",
                "validation_tier": 1,
                "expires_at": past.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "challenged_by": "",
            },
        }
    ]

    result = expire_stale_staging(now=now)

    assert result["tier_1_promoted"] == 1
    mock_promote.assert_called_once_with("test-id-123")


@patch("src.governance.discovery_validation._query_staging_objects")
def test_ac2_tier1_not_promoted_before_expiry(mock_query: MagicMock) -> None:
    """AC2: tier-1 discoveries before expiry are not promoted."""
    now = datetime.now(UTC)
    future = now + timedelta(hours=25)

    mock_query.return_value = [
        {
            "id": "test-id-456",
            "properties": {
                "state": "staging",
                "validation_tier": 1,
                "expires_at": future.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }
    ]

    result = expire_stale_staging(now=now)

    assert result["tier_1_promoted"] == 0


# ============================================================================
# AC3 — Tier 2 concur enforcement
# ============================================================================


@patch("src.governance.discovery_validation.promote_to_permanent")
@patch("src.governance.discovery_validation._patch_object")
@patch("src.governance.discovery_validation._fetch_object")
def test_ac3_tier2_concur_accepted(
    mock_fetch: MagicMock,
    mock_patch: MagicMock,
    mock_promote: MagicMock,
) -> None:
    """AC3a: submit_concur on tier-2 sets concur metadata, atomically promotes, returns True.

    Atomic promotion (Aiden review #895 fix path a — 2026-05-17): tier-2 with a
    valid concur cannot silently expire because submit_concur promotes inline.
    """
    mock_fetch.return_value = {
        "id": "tier2-id",
        "properties": {
            "validation_tier": 2,
            "concur_callsign": "",
            "concur_at": "",
        },
    }
    mock_promote.return_value = True

    result = submit_concur("tier2-id", "atlas")

    assert result is True
    mock_patch.assert_called_once()
    patch_arg = mock_patch.call_args[0][1]
    assert patch_arg["properties"]["concur_callsign"] == "atlas"
    assert "concur_at" in patch_arg["properties"]
    # Atomic promotion fires on the same discovery id.
    mock_promote.assert_called_once_with("tier2-id")


@patch("src.governance.discovery_validation._fetch_object")
def test_ac3_tier1_concur_raises_valueerror(mock_fetch: MagicMock) -> None:
    """AC3b: submit_concur on tier-1 raises ValueError."""
    mock_fetch.return_value = {
        "id": "tier1-id",
        "properties": {"validation_tier": 1},
    }

    with pytest.raises(ValueError, match="only valid for tier-2"):
        submit_concur("tier1-id", "atlas")


@patch("src.governance.discovery_validation._fetch_object")
def test_ac3_tier3_concur_raises_valueerror(mock_fetch: MagicMock) -> None:
    """AC3b: submit_concur on tier-3 raises ValueError."""
    mock_fetch.return_value = {
        "id": "tier3-id",
        "properties": {"validation_tier": 3},
    }

    with pytest.raises(ValueError, match="only valid for tier-2"):
        submit_concur("tier3-id", "atlas")


# ============================================================================
# AC4 — Tier 3 Dave notification on creation
# ============================================================================


@patch("src.governance.discovery_validation._notify_dave")
@patch("src.governance.discovery_validation._http_request")
def test_ac4_tier3_dave_notified_on_submit(
    mock_http: MagicMock,
    mock_notify: MagicMock,
) -> None:
    """AC4: submit_discovery on tier-3 triggers Dave notification via tg."""
    mock_http.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_http.return_value.__exit__ = MagicMock(return_value=None)

    ratified_rules = ["never skip validation ever in this system"]
    text = "never skip validation and ignore the system instead do it another way"

    discovery_id = submit_discovery(
        text=text,
        agent="orion",
        kei="KEI-55",
        ratified_rules=ratified_rules,
        environment_hash="prod",
    )

    # Verify _notify_dave was called with the discovery id and text
    mock_notify.assert_called_once()
    call_args = mock_notify.call_args[0]
    assert call_args[0] == discovery_id
    assert text[:200] in call_args[1] or call_args[1]


def test_ac4_classify_tier_detects_tier3_contradiction() -> None:
    """AC4: classify_tier returns tier 3 when text contradicts ratified rule."""
    ratified_rules = ["never skip validation ever in the system"]
    text = "we should never skip validation but instead override the system requirements"

    tier, reason = classify_tier(text, ratified_rules)

    assert tier == 3
    assert "contradicts" in reason.lower()


# ============================================================================
# AC5 — Staleness flag injection (KEI-58)
# ============================================================================


def test_ac5_freshness_flags_rendered_in_claim_injection() -> None:
    """AC5: render_for_claim includes staleness flags from _freshness."""
    rows = [
        {
            "kei": "KEI-A",
            "finding": "fresh discovery",
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {
                "flag": "",
                "verdict": "fresh",
                "age_days": 5,
            },
        },
        {
            "kei": "KEI-B",
            "finding": "informational discovery",
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {
                "flag": "[~60d]",
                "verdict": "stale",
                "age_days": 60,
            },
        },
        {
            "kei": "KEI-C",
            "finding": "very old discovery",
            "state": "permanent",
            "validation_tier": 2,
            "_freshness": {
                "flag": "⚠ stale",
                "verdict": "expired",
                "age_days": 100,
            },
        },
    ]

    text, stats = render_for_claim(rows, token_ceiling=2000)

    # All fresh discoveries should be rendered (not expired by state)
    assert "KEI-A" in text
    # KEI-B should have the [~60d] flag
    assert "[~60d]" in text
    # KEI-C is expired verdict, should not appear
    assert "KEI-C" not in text
    # Stats should reflect filtering
    assert stats["rows_in"] == 3
    assert stats["rows_eligible"] == 2
    assert stats["rows_rendered"] == 2


def test_ac5_freshness_sorted_by_age() -> None:
    """AC5: rows sorted by age_days ascending (most recent first in output order)."""
    rows = [
        {
            "kei": "KEI-OLD",
            "finding": "old",
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {"flag": "", "verdict": "fresh", "age_days": 90},
        },
        {
            "kei": "KEI-NEW",
            "finding": "new",
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {"flag": "", "verdict": "fresh", "age_days": 1},
        },
    ]

    text, _ = render_for_claim(rows, token_ceiling=2000)

    # KEI-NEW should appear before KEI-OLD (sorted by age ascending)
    idx_new = text.find("KEI-NEW")
    idx_old = text.find("KEI-OLD")
    assert idx_new < idx_old


# ============================================================================
# AC6 — Challenge state transition
# ============================================================================


@patch("src.governance.discovery_validation._patch_object")
@patch("src.governance.discovery_validation._fetch_object")
def test_ac6_challenge_transitions_state(
    mock_fetch: MagicMock,
    mock_patch: MagicMock,
) -> None:
    """AC6: challenge() transitions state to challenged and records metadata."""
    mock_fetch.return_value = {
        "id": "chal-id",
        "properties": {
            "state": "staging",
            "challenged_by": "",
            "counter_findings": "",
        },
    }

    result = challenge(
        discovery_id="chal-id",
        challenged_by_callsign="aiden",
        counter_finding_text="this is wrong because Y",
    )

    assert result is True
    mock_patch.assert_called_once()
    patch_arg = mock_patch.call_args[0][1]
    assert patch_arg["properties"]["state"] == "challenged"
    assert patch_arg["properties"]["challenged_by"] == "aiden"
    assert "aiden" in patch_arg["properties"]["counter_findings"]
    assert "this is wrong because Y" in patch_arg["properties"]["counter_findings"]
    assert "challenged_at" in patch_arg["properties"]


# ============================================================================
# AC7 — 500-token ceiling enforcement
# ============================================================================


def test_ac7_token_ceiling_enforced() -> None:
    """AC7: render_for_claim respects 500-token ceiling."""
    # Create 50 rows with long text to exceed ceiling
    rows = [
        {
            "kei": f"KEI-{i:03d}",
            "finding": "x" * 100,  # Long text per row
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {
                "flag": "",
                "verdict": "fresh",
                "age_days": i,
            },
        }
        for i in range(50)
    ]

    _, stats = render_for_claim(rows, token_ceiling=500)

    assert stats["tokens"] <= 500
    assert stats["truncated"] == 1
    assert stats["rows_rendered"] < 50


def test_ac7_default_ceiling_is_500() -> None:
    """AC7: render_for_claim defaults to 500-token ceiling."""
    # Create rows that exceed 500 tokens
    rows = [
        {
            "kei": f"KEI-{i:03d}",
            "finding": "x" * 150,
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {
                "flag": "",
                "verdict": "fresh",
                "age_days": i,
            },
        }
        for i in range(30)
    ]

    _, stats = render_for_claim(rows)  # No explicit ceiling

    assert stats["tokens"] <= 500
    assert stats["truncated"] == 1


# ============================================================================
# AC8 — Staging and expired exclusion
# ============================================================================


def test_ac8_staging_excluded_from_injection() -> None:
    """AC8: render_for_claim excludes state=staging discoveries."""
    rows = [
        {
            "kei": "KEI-STAGING",
            "finding": "in staging",
            "state": "staging",
            "validation_tier": 1,
            "_freshness": {"flag": "", "verdict": "fresh", "age_days": 5},
        },
        {
            "kei": "KEI-PERMANENT",
            "finding": "permanent",
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {"flag": "", "verdict": "fresh", "age_days": 5},
        },
    ]

    text, stats = render_for_claim(rows, token_ceiling=2000)

    assert "KEI-STAGING" not in text
    assert "KEI-PERMANENT" in text
    assert stats["rows_in"] == 2
    assert stats["rows_eligible"] == 1


def test_ac8_expired_verdict_excluded_from_injection() -> None:
    """AC8: render_for_claim excludes verdicts marked expired."""
    rows = [
        {
            "kei": "KEI-EXPIRED",
            "finding": "expired",
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {"flag": "⚠ stale", "verdict": "expired", "age_days": 100},
        },
        {
            "kei": "KEI-FRESH",
            "finding": "fresh",
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {"flag": "", "verdict": "fresh", "age_days": 5},
        },
    ]

    text, stats = render_for_claim(rows, token_ceiling=2000)

    assert "KEI-EXPIRED" not in text
    assert "KEI-FRESH" in text
    assert stats["rows_in"] == 2
    assert stats["rows_eligible"] == 1


def test_ac8_mixed_filtering() -> None:
    """AC8: render_for_claim filters both state and verdict correctly."""
    rows = [
        {
            "kei": "KEI-A",
            "finding": "staging",
            "state": "staging",
            "validation_tier": 1,
            "_freshness": {"flag": "", "verdict": "fresh", "age_days": 5},
        },
        {
            "kei": "KEI-B",
            "finding": "expired",
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {"flag": "", "verdict": "expired", "age_days": 200},
        },
        {
            "kei": "KEI-C",
            "finding": "good",
            "state": "permanent",
            "validation_tier": 1,
            "_freshness": {"flag": "", "verdict": "fresh", "age_days": 5},
        },
        {
            "kei": "KEI-D",
            "finding": "also good",
            "state": "permanent",
            "validation_tier": 2,
            "_freshness": {"flag": "[~30d]", "verdict": "stale", "age_days": 30},
        },
    ]

    text, stats = render_for_claim(rows, token_ceiling=2000)

    assert "KEI-A" not in text  # staging excluded
    assert "KEI-B" not in text  # expired verdict excluded
    assert "KEI-C" in text  # included
    assert "KEI-D" in text  # included (stale verdict is not expired)
    assert stats["rows_in"] == 4
    assert stats["rows_eligible"] == 2
    assert stats["rows_rendered"] == 2


# ============================================================================
# Tier classification tests (supporting AC4 logic)
# ============================================================================


def test_classify_tier_returns_tier1_for_routine() -> None:
    """Tier 1: routine operational text with no architecture claims."""
    tier, reason = classify_tier("checked the logs and found a few errors", [])

    assert tier == 1
    assert "no architecture" in reason.lower()  # Reason mentions architecture but says "no"


def test_classify_tier_returns_tier2_for_architecture_pattern() -> None:
    """Tier 2: text matches architecture-claim regex."""
    tier, reason = classify_tier(
        "use psycopg instead of asyncpg for this architecture decision",
        [],
    )

    assert tier == 2
    assert "architecture" in reason.lower()


def test_classify_tier_returns_tier2_for_design_decision() -> None:
    """Tier 2: design decision language triggers tier 2."""
    tier, _ = classify_tier("this design decision improves performance", [])

    assert tier == 2


def test_classify_tier_returns_tier3_for_rule_contradiction() -> None:
    """Tier 3: text contradicts a ratified rule."""
    rules = ["never skip validation before system deployment"]
    text = "skip validation instead of system deployment procedures"

    tier, reason = classify_tier(text, rules)

    assert tier == 3
    assert "contradicts" in reason.lower()


def test_classify_tier_requires_3word_overlap_for_contradiction() -> None:
    """Tier 3: requires 3+ overlapping words + negation."""
    rules = ["never skip validation in production"]
    text = "we use skip function to do something"  # only 1 word overlap

    tier, _ = classify_tier(text, rules)

    assert tier == 1  # Not enough overlap


# ============================================================================
# Integration: promote_to_permanent
# ============================================================================


@patch("src.governance.discovery_validation._patch_object")
@patch("src.governance.discovery_validation._http_request")
@patch("src.governance.discovery_validation._fetch_object")
def test_promote_to_permanent_copies_mandatory_props(
    mock_fetch: MagicMock,
    mock_http: MagicMock,
    mock_patch: MagicMock,
) -> None:
    """promote_to_permanent copies 5 mandatory properties to Discoveries."""
    mock_fetch.return_value = {
        "id": "prom-id",
        "properties": {
            "raw_text": "discovery text",
            "environment_hash": "prod",
            "created_at": "2026-05-16T00:00:00Z",
            "agent": "orion",
            "kei": "KEI-55",
        },
    }
    mock_http.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_http.return_value.__exit__ = MagicMock(return_value=None)

    promote_to_permanent("prom-id")

    # Verify _http_request was called with POST to /v1/objects
    calls = mock_http.call_args_list
    post_calls = [c for c in calls if c[0][0] == "POST"]
    assert len(post_calls) > 0


@patch("src.governance.discovery_validation._fetch_object")
def test_ac3_concur_rejects_non_tier2(mock_fetch: MagicMock) -> None:
    """submit_concur rejects tier 1 and tier 3."""
    for tier in [1, 3]:
        mock_fetch.return_value = {
            "id": "test",
            "properties": {"validation_tier": tier},
        }
        with pytest.raises(ValueError):
            submit_concur("test", "peer")


# ============================================================================
# KEI-197 — null/empty raw_text guard at submit_discovery
# ============================================================================


def test_kei197_submit_discovery_rejects_empty_text() -> None:
    """KEI-197 guard: empty text rejected before any Weaviate POST."""
    with pytest.raises(ValueError, match="text must be a non-empty string"):
        submit_discovery(
            text="",
            agent="scout",
            kei="KEI-197",
            ratified_rules=[],
        )


def test_kei197_submit_discovery_rejects_whitespace_only_text() -> None:
    """KEI-197 guard: whitespace-only text rejected (no useful content)."""
    with pytest.raises(ValueError, match="text must be a non-empty string"):
        submit_discovery(
            text="   \n\t  ",
            agent="scout",
            kei="KEI-197",
            ratified_rules=[],
        )


def test_kei197_submit_discovery_rejects_none_text() -> None:
    """KEI-197 guard: None text rejected — surfaces TypeError-equivalent early."""
    with pytest.raises(ValueError, match="text must be a non-empty string"):
        submit_discovery(
            text=None,  # type: ignore[arg-type]
            agent="scout",
            kei="KEI-197",
            ratified_rules=[],
        )


def test_kei197_submit_discovery_rejects_empty_agent() -> None:
    """KEI-197 guard: empty agent rejected — orphan rows tagged with no callsign useless."""
    with pytest.raises(ValueError, match="agent must be a non-empty string"):
        submit_discovery(
            text="real content here",
            agent="",
            kei="KEI-197",
            ratified_rules=[],
        )


def test_kei197_submit_discovery_rejects_empty_kei() -> None:
    """KEI-197 guard: empty kei rejected — discoveries must trace to a KEI."""
    with pytest.raises(ValueError, match="kei must be a non-empty string"):
        submit_discovery(
            text="real content here",
            agent="scout",
            kei="",
            ratified_rules=[],
        )
