"""prospect_telemetry.py — Per-prospect outreach effectiveness tracking.

Records touches (email sent, call made, LinkedIn message), responses
(reply, voicemail, LinkedIn accept), and conversion events (meeting booked,
deal won). Queryable for campaign-level aggregations.

Storage: public.outreach_telemetry via MCP bridge (best-effort, non-fatal).
All costs in AUD (LAW II).
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_BRIDGE = "/home/elliotbot/clawd/skills/mcp-bridge/scripts/mcp-bridge.js"
_PROJECT_ID = "jatzvazlbusedwsnqxzr"

VALID_CHANNELS = {"email", "linkedin", "voice", "sms"}
VALID_EVENT_TYPES = {"touch", "response", "conversion"}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _escape(val: str) -> str:
    return str(val).replace("'", "''")


def _write_supabase(row: dict[str, Any]) -> None:
    """Best-effort insert into public.outreach_telemetry via MCP bridge."""
    meta = json.dumps(row.get("metadata", {})).replace("'", "''")
    step_sql = f"{row['step']}" if row.get("step") is not None else "NULL"
    intent_sql = f"'{_escape(row['intent'])}'" if row.get("intent") else "NULL"
    campaign_sql = f"'{_escape(row['campaign_id'])}'" if row.get("campaign_id") else "NULL"

    sql = (
        "INSERT INTO public.outreach_telemetry "
        "(prospect_id, campaign_id, event_type, channel, step, intent, cost_aud, metadata, created_at) "
        f"VALUES ('{_escape(row['prospect_id'])}', {campaign_sql}, '{_escape(row['event_type'])}', "
        f"'{_escape(row['channel'])}', {step_sql}, {intent_sql}, "
        f"{float(row.get('cost_aud', 0))}, '{meta}', '{row['created_at']}');"
    )
    args = json.dumps({"project_id": _PROJECT_ID, "query": sql})
    try:
        subprocess.run(
            ["node", _BRIDGE, "call", "supabase", "execute_sql", args],
            capture_output=True,
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("prospect_telemetry: Supabase write failed (non-fatal): %s", exc)


class ProspectTelemetry:
    """Track outreach effectiveness per prospect.

    Records: touches sent (by channel), responses received (by intent),
    total cost, conversion outcome. Queryable for campaign effectiveness.
    """

    @staticmethod
    def record_touch(
        prospect_id: str,
        channel: str,
        step: int,
        cost_aud: float = 0.0,
        campaign_id: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Record an outreach touch (email sent, call made, LinkedIn message sent)."""
        if channel not in VALID_CHANNELS:
            raise ValueError(f"channel must be one of {VALID_CHANNELS}, got {channel!r}")
        row = {
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "event_type": "touch",
            "channel": channel,
            "step": step,
            "intent": None,
            "cost_aud": round(float(cost_aud), 4),
            "metadata": metadata or {},
            "created_at": _now_iso(),
        }
        _write_supabase(row)
        logger.info(
            "telemetry: touch prospect=%s channel=%s step=%s cost_aud=%.4f",
            prospect_id,
            channel,
            step,
            cost_aud,
        )
        return row

    @staticmethod
    def record_response(
        prospect_id: str,
        channel: str,
        intent: str,
        response_text: str = "",
        campaign_id: str | None = None,
    ) -> dict:
        """Record a response received (reply, voicemail, LinkedIn accept)."""
        if channel not in VALID_CHANNELS:
            raise ValueError(f"channel must be one of {VALID_CHANNELS}, got {channel!r}")
        row = {
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "event_type": "response",
            "channel": channel,
            "step": None,
            "intent": intent,
            "cost_aud": 0.0,
            "metadata": {"response_text": response_text} if response_text else {},
            "created_at": _now_iso(),
        }
        _write_supabase(row)
        logger.info(
            "telemetry: response prospect=%s channel=%s intent=%s",
            prospect_id,
            channel,
            intent,
        )
        return row

    @staticmethod
    def record_conversion(
        prospect_id: str,
        conversion_type: str,
        value_aud: float = 0.0,
        campaign_id: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Record a conversion event (meeting booked, deal won, etc)."""
        row = {
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "event_type": "conversion",
            "channel": "email",  # channel required by schema; conversions are cross-channel
            "step": None,
            "intent": conversion_type,
            "cost_aud": 0.0,
            "metadata": {**(metadata or {}), "value_aud": round(float(value_aud), 4)},
            "created_at": _now_iso(),
        }
        _write_supabase(row)
        logger.info(
            "telemetry: conversion prospect=%s type=%s value_aud=%.2f",
            prospect_id,
            conversion_type,
            value_aud,
        )
        return row

    @staticmethod
    def get_prospect_summary(prospect_id: str) -> dict:
        """Get full outreach history for a prospect from Supabase.

        Returns:
            {touches: int, responses: int, cost_aud: float,
             channels_used: list, response_rate: float, converted: bool}
        """
        sql = (
            "SELECT event_type, channel, cost_aud "
            "FROM public.outreach_telemetry "
            f"WHERE prospect_id = '{_escape(prospect_id)}';"
        )
        args = json.dumps({"project_id": _PROJECT_ID, "query": sql})
        rows: list[dict] = []
        try:
            result = subprocess.run(
                ["node", _BRIDGE, "call", "supabase", "execute_sql", args],
                capture_output=True,
                text=True,
                timeout=10,
            )
            payload = json.loads(result.stdout or "[]")
            if isinstance(payload, list):
                rows = payload
            elif isinstance(payload, dict) and "result" in payload:
                rows = json.loads(payload["result"]) if isinstance(payload["result"], str) else []
        except Exception as exc:  # noqa: BLE001
            logger.warning("prospect_telemetry: get_prospect_summary fetch failed: %s", exc)

        touches = [r for r in rows if r.get("event_type") == "touch"]
        responses = [r for r in rows if r.get("event_type") == "response"]
        converted = any(r.get("event_type") == "conversion" for r in rows)
        total_cost = sum(float(r.get("cost_aud", 0)) for r in touches)
        channels = list({r["channel"] for r in rows if r.get("channel")})
        response_rate = len(responses) / len(touches) if touches else 0.0

        return {
            "prospect_id": prospect_id,
            "touches": len(touches),
            "responses": len(responses),
            "cost_aud": round(total_cost, 4),
            "channels_used": sorted(channels),
            "response_rate": round(response_rate, 4),
            "converted": converted,
        }

    @staticmethod
    def get_campaign_effectiveness(campaign_id: str) -> dict:
        """Aggregate telemetry across all prospects in a campaign.

        Returns:
            {total_prospects: int, total_touches: int, total_responses: int,
             response_rate: float, conversion_rate: float, cost_per_response: float,
             cost_per_conversion: float, best_channel: str}
        """
        sql = (
            "SELECT prospect_id, event_type, channel, cost_aud "
            "FROM public.outreach_telemetry "
            f"WHERE campaign_id = '{_escape(campaign_id)}';"
        )
        args = json.dumps({"project_id": _PROJECT_ID, "query": sql})
        rows: list[dict] = []
        try:
            result = subprocess.run(
                ["node", _BRIDGE, "call", "supabase", "execute_sql", args],
                capture_output=True,
                text=True,
                timeout=10,
            )
            payload = json.loads(result.stdout or "[]")
            if isinstance(payload, list):
                rows = payload
            elif isinstance(payload, dict) and "result" in payload:
                rows = json.loads(payload["result"]) if isinstance(payload["result"], str) else []
        except Exception as exc:  # noqa: BLE001
            logger.warning("prospect_telemetry: get_campaign_effectiveness fetch failed: %s", exc)

        prospects = {r["prospect_id"] for r in rows if r.get("prospect_id")}
        touches = [r for r in rows if r.get("event_type") == "touch"]
        responses = [r for r in rows if r.get("event_type") == "response"]
        conversions = [r for r in rows if r.get("event_type") == "conversion"]
        total_cost = sum(float(r.get("cost_aud", 0)) for r in touches)

        response_rate = len(responses) / len(touches) if touches else 0.0
        conversion_rate = len(conversions) / len(prospects) if prospects else 0.0
        cost_per_response = total_cost / len(responses) if responses else 0.0
        cost_per_conversion = total_cost / len(conversions) if conversions else 0.0

        # Best channel = highest response rate across touch channels
        channel_touches: dict[str, int] = {}
        channel_responses: dict[str, int] = {}
        for r in touches:
            ch = r.get("channel", "")
            channel_touches[ch] = channel_touches.get(ch, 0) + 1
        for r in responses:
            ch = r.get("channel", "")
            channel_responses[ch] = channel_responses.get(ch, 0) + 1
        best_channel = (
            max(
                channel_touches,
                key=lambda ch: channel_responses.get(ch, 0) / channel_touches[ch],
                default="none",
            )
            if channel_touches
            else "none"
        )

        return {
            "campaign_id": campaign_id,
            "total_prospects": len(prospects),
            "total_touches": len(touches),
            "total_responses": len(responses),
            "response_rate": round(response_rate, 4),
            "conversion_rate": round(conversion_rate, 4),
            "cost_per_response": round(cost_per_response, 4),
            "cost_per_conversion": round(cost_per_conversion, 4),
            "best_channel": best_channel,
        }
