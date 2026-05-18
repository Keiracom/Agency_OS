"""KEI-20 — severity → channel routing pure-function tests.

Dispatch (Elliot 2026-05-18): "P0 → #ceo, P1 → #execution, lower → alerts.
Configure Better Stack webhook router to split. Acceptance: synthetic P0
alert lands in #ceo, P1 in #execution."

Bucket constants live in the module under test — assert against canonical
channel IDs explicitly so a typo doesn't silently re-route.
"""

from __future__ import annotations

import pytest

from src.api.webhooks.betterstack_severity_router import (
    CHANNEL_ALERTS,
    CHANNEL_CEO,
    CHANNEL_EXECUTION,
    SEVERITY_OTHER,
    SEVERITY_P0,
    SEVERITY_P1,
    classify,
    extract_severity_token,
    route,
    severity_to_channel,
)

# ---------------------------------------------------------------------------
# Canonical channel IDs — regression guard
# ---------------------------------------------------------------------------


def test_channel_ids_are_canonical() -> None:
    # Anchored to the IDs used elsewhere in the repo (slack_relay, BS routing
    # policy). A drift here re-routes alerts silently.
    assert CHANNEL_CEO == "C0B2PM3TV0B"
    assert CHANNEL_EXECUTION == "C0B3QB0K1GQ"
    assert CHANNEL_ALERTS == "C0B2EJU53EK"


# ---------------------------------------------------------------------------
# classify: token → bucket
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "token",
    ["P0", "p0", " P0 ", "critical", "Critical", "sev0", "sev-0", "urgent"],
)
def test_classify_p0_synonyms(token: str) -> None:
    assert classify(token) == SEVERITY_P0


@pytest.mark.parametrize(
    "token",
    ["P1", "p1", " P1 ", "high", "High", "sev1", "sev-1"],
)
def test_classify_p1_synonyms(token: str) -> None:
    assert classify(token) == SEVERITY_P1


@pytest.mark.parametrize(
    "token",
    ["P2", "P3", "P4", "low", "info", "warning", "warning - degraded", ""],
)
def test_classify_lower_severities_fall_through_to_other(token: str) -> None:
    assert classify(token) == SEVERITY_OTHER


def test_classify_unknown_string_falls_through() -> None:
    # Defensive: unknown / malformed tokens MUST route to OTHER (which routes
    # to #alerts), never silently drop. KEI-20 fail-noisy contract.
    assert classify("garbage-token-xyz") == SEVERITY_OTHER
    assert classify("!@#$") == SEVERITY_OTHER


# ---------------------------------------------------------------------------
# severity_to_channel: bucket → channel ID
# ---------------------------------------------------------------------------


def test_severity_to_channel_p0_routes_to_ceo() -> None:
    assert severity_to_channel(SEVERITY_P0) == CHANNEL_CEO


def test_severity_to_channel_p1_routes_to_execution() -> None:
    assert severity_to_channel(SEVERITY_P1) == CHANNEL_EXECUTION


def test_severity_to_channel_other_routes_to_alerts() -> None:
    assert severity_to_channel(SEVERITY_OTHER) == CHANNEL_ALERTS


def test_severity_to_channel_unknown_bucket_falls_to_alerts() -> None:
    # If we ever add a new bucket and forget to extend severity_to_channel,
    # the fallback must still be #alerts — never silently #ceo.
    assert severity_to_channel("DEFINITELY_NOT_A_BUCKET") == CHANNEL_ALERTS


# ---------------------------------------------------------------------------
# extract_severity_token: payload → raw token (3-field probe order)
# ---------------------------------------------------------------------------


def test_extract_severity_token_from_priority() -> None:
    payload = {"data": {"attributes": {"priority": "P0"}}}
    assert extract_severity_token(payload) == "P0"


def test_extract_severity_token_from_severity_field() -> None:
    payload = {"data": {"attributes": {"severity": "high"}}}
    assert extract_severity_token(payload) == "high"


def test_extract_severity_token_from_metadata() -> None:
    payload = {"data": {"attributes": {"metadata": {"Priority": "P1"}}}}
    assert extract_severity_token(payload) == "P1"


def test_extract_severity_token_priority_wins_over_severity() -> None:
    # Field-priority order: priority → severity → metadata. Test the
    # tiebreaker explicitly.
    payload = {"data": {"attributes": {"priority": "P0", "severity": "P1"}}}
    assert extract_severity_token(payload) == "P0"


def test_extract_severity_token_handles_list_envelope() -> None:
    # BS sometimes wraps `data` as a list (when fan-out on a query endpoint
    # gets routed back through a webhook). Take first element.
    payload = {"data": [{"attributes": {"priority": "P0"}}]}
    assert extract_severity_token(payload) == "P0"


def test_extract_severity_token_handles_flat_payload() -> None:
    # Operator-flattened payloads have attributes at the top level.
    payload = {"attributes": {"priority": "P1"}}
    assert extract_severity_token(payload) == "P1"


def test_extract_severity_token_empty_when_no_signal() -> None:
    payload = {"data": {"attributes": {"name": "monitor", "cause": "timeout"}}}
    assert extract_severity_token(payload) == ""


# ---------------------------------------------------------------------------
# route: end-to-end (payload → (bucket, channel))
# ---------------------------------------------------------------------------


def test_route_synthetic_p0_lands_in_ceo() -> None:
    payload = {"data": {"attributes": {"priority": "P0", "name": "Test P0 incident"}}}
    bucket, channel = route(payload)
    assert bucket == SEVERITY_P0
    assert channel == CHANNEL_CEO


def test_route_synthetic_p1_lands_in_execution() -> None:
    payload = {"data": {"attributes": {"priority": "P1", "name": "Test P1 incident"}}}
    bucket, channel = route(payload)
    assert bucket == SEVERITY_P1
    assert channel == CHANNEL_EXECUTION


def test_route_synthetic_p2_lands_in_alerts() -> None:
    payload = {"data": {"attributes": {"priority": "P2", "name": "Test P2 incident"}}}
    bucket, channel = route(payload)
    assert bucket == SEVERITY_OTHER
    assert channel == CHANNEL_ALERTS


def test_route_synthetic_no_severity_lands_in_alerts() -> None:
    # KEI-20 fail-noisy: payloads without a routing signal default to the
    # lowest-priority channel. They are NOT silently dropped.
    payload = {"data": {"attributes": {"name": "Test unspecified"}}}
    bucket, channel = route(payload)
    assert bucket == SEVERITY_OTHER
    assert channel == CHANNEL_ALERTS
