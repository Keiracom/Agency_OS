"""Tests for src/pipeline/prospect_telemetry.py.

All Supabase writes are patched out — no network calls in unit tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.prospect_telemetry import ProspectTelemetry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_write():
    """Patch _write_supabase so no subprocess is spawned."""
    return patch("src.pipeline.prospect_telemetry._write_supabase")


def _patch_query(rows: list[dict]):
    """Patch subprocess.run to return fake DB rows for summary/effectiveness queries."""
    import json

    mock_result = MagicMock()
    mock_result.stdout = json.dumps(rows)
    return patch("subprocess.run", return_value=mock_result)


# ---------------------------------------------------------------------------
# record_touch
# ---------------------------------------------------------------------------

class TestRecordTouch:
    def test_returns_correct_shape(self):
        with _patch_write():
            result = ProspectTelemetry.record_touch(
                prospect_id="p-001",
                channel="email",
                step=1,
                cost_aud=0.015,
                campaign_id="camp-A",
            )
        assert result["event_type"] == "touch"
        assert result["channel"] == "email"
        assert result["step"] == 1
        assert result["cost_aud"] == 0.015
        assert result["campaign_id"] == "camp-A"
        assert result["prospect_id"] == "p-001"
        assert "created_at" in result

    def test_cost_rounded_to_4dp(self):
        with _patch_write():
            result = ProspectTelemetry.record_touch("p-002", "linkedin", 2, cost_aud=0.123456)
        assert result["cost_aud"] == 0.1235

    def test_invalid_channel_raises(self):
        with pytest.raises(ValueError, match="channel must be one of"):
            ProspectTelemetry.record_touch("p-003", "fax", 1)

    def test_zero_cost_default(self):
        with _patch_write():
            result = ProspectTelemetry.record_touch("p-004", "voice", 3)
        assert result["cost_aud"] == 0.0

    def test_write_called_once(self):
        with _patch_write() as mock_write:
            ProspectTelemetry.record_touch("p-005", "sms", 1, cost_aud=0.05)
        mock_write.assert_called_once()


# ---------------------------------------------------------------------------
# record_response
# ---------------------------------------------------------------------------

class TestRecordResponse:
    def test_returns_correct_shape_with_intent(self):
        with _patch_write():
            result = ProspectTelemetry.record_response(
                prospect_id="p-010",
                channel="email",
                intent="interested",
                response_text="Yes, let's chat",
            )
        assert result["event_type"] == "response"
        assert result["intent"] == "interested"
        assert result["channel"] == "email"
        assert result["metadata"]["response_text"] == "Yes, let's chat"
        assert result["cost_aud"] == 0.0

    def test_empty_response_text_no_metadata_key(self):
        with _patch_write():
            result = ProspectTelemetry.record_response("p-011", "linkedin", "connected")
        assert result["metadata"] == {}

    def test_invalid_channel_raises(self):
        with pytest.raises(ValueError):
            ProspectTelemetry.record_response("p-012", "post", "reply")


# ---------------------------------------------------------------------------
# record_conversion
# ---------------------------------------------------------------------------

class TestRecordConversion:
    def test_returns_correct_shape(self):
        with _patch_write():
            result = ProspectTelemetry.record_conversion(
                prospect_id="p-020",
                conversion_type="meeting_booked",
                value_aud=500.0,
            )
        assert result["event_type"] == "conversion"
        assert result["intent"] == "meeting_booked"
        assert result["metadata"]["value_aud"] == 500.0

    def test_zero_value_default(self):
        with _patch_write():
            result = ProspectTelemetry.record_conversion("p-021", "deal_won")
        assert result["metadata"]["value_aud"] == 0.0


# ---------------------------------------------------------------------------
# get_prospect_summary
# ---------------------------------------------------------------------------

class TestGetProspectSummary:
    def _make_rows(self):
        return [
            {"event_type": "touch",    "channel": "email",    "cost_aud": 0.015},
            {"event_type": "touch",    "channel": "linkedin", "cost_aud": 0.01},
            {"event_type": "response", "channel": "email",    "cost_aud": 0.0},
            {"event_type": "conversion","channel": "email",   "cost_aud": 0.0},
        ]

    def test_aggregation_correct(self):
        with _patch_query(self._make_rows()):
            summary = ProspectTelemetry.get_prospect_summary("p-030")

        assert summary["touches"] == 2
        assert summary["responses"] == 1
        assert summary["converted"] is True
        assert summary["cost_aud"] == pytest.approx(0.025, abs=1e-4)
        assert summary["response_rate"] == pytest.approx(0.5, abs=1e-4)
        assert "email" in summary["channels_used"]
        assert "linkedin" in summary["channels_used"]

    def test_no_touches_zero_response_rate(self):
        with _patch_query([]):
            summary = ProspectTelemetry.get_prospect_summary("p-031")
        assert summary["touches"] == 0
        assert summary["response_rate"] == 0.0
        assert summary["converted"] is False

    def test_prospect_id_in_return(self):
        with _patch_query([]):
            summary = ProspectTelemetry.get_prospect_summary("p-032")
        assert summary["prospect_id"] == "p-032"


# ---------------------------------------------------------------------------
# get_campaign_effectiveness
# ---------------------------------------------------------------------------

class TestGetCampaignEffectiveness:
    def _make_rows(self):
        return [
            {"prospect_id": "p-1", "event_type": "touch",      "channel": "email",    "cost_aud": 0.015},
            {"prospect_id": "p-1", "event_type": "touch",      "channel": "linkedin", "cost_aud": 0.01},
            {"prospect_id": "p-1", "event_type": "response",   "channel": "email",    "cost_aud": 0.0},
            {"prospect_id": "p-2", "event_type": "touch",      "channel": "email",    "cost_aud": 0.015},
            {"prospect_id": "p-2", "event_type": "conversion", "channel": "email",    "cost_aud": 0.0},
        ]

    def test_totals_correct(self):
        with _patch_query(self._make_rows()):
            eff = ProspectTelemetry.get_campaign_effectiveness("camp-B")

        assert eff["total_prospects"] == 2
        assert eff["total_touches"] == 3
        assert eff["total_responses"] == 1
        assert eff["response_rate"] == pytest.approx(1 / 3, abs=1e-4)
        assert eff["conversion_rate"] == pytest.approx(0.5, abs=1e-4)

    def test_cost_per_response(self):
        with _patch_query(self._make_rows()):
            eff = ProspectTelemetry.get_campaign_effectiveness("camp-B")
        # total_cost = 0.015 + 0.01 + 0.015 = 0.04; responses = 1
        assert eff["cost_per_response"] == pytest.approx(0.04, abs=1e-4)

    def test_cost_per_conversion(self):
        with _patch_query(self._make_rows()):
            eff = ProspectTelemetry.get_campaign_effectiveness("camp-B")
        # conversions = 1
        assert eff["cost_per_conversion"] == pytest.approx(0.04, abs=1e-4)

    def test_best_channel_returned(self):
        with _patch_query(self._make_rows()):
            eff = ProspectTelemetry.get_campaign_effectiveness("camp-B")
        assert eff["best_channel"] in {"email", "linkedin"}

    def test_empty_campaign(self):
        with _patch_query([]):
            eff = ProspectTelemetry.get_campaign_effectiveness("camp-empty")
        assert eff["total_prospects"] == 0
        assert eff["response_rate"] == 0.0
        assert eff["best_channel"] == "none"
