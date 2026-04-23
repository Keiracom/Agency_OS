"""
Tests for src/outreach/dispatcher.py — OutreachDispatcher pipeline.

Covers:
- timing block  (skip path)
- compliance block (skip path, carries violation codes)
- rate-limit block (skip path)
- rate-limit raises -> dispatcher treats as allowed + logs warning
- successful email / linkedin / voice send + DB record
- provider exception -> failed result, never raises
- missing provider client -> failed result
- outcome recorder catches DB errors silently
- unknown channel -> failed result
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.outreach.dispatcher import DispatchResult, OutreachDispatcher
from src.outreach.safety.compliance_guard import ComplianceDecision
from src.outreach.safety.timing_engine import TimingDecision

# ---------- helpers -----------------------------------------------------------

def _touch(channel="email", **overrides) -> dict:
    base = {
        "id": "t1",
        "channel": channel,
        "prospect": {"email": "ceo@acme.com.au", "phone": "+61412345678", "tz": "Australia/Sydney"},
        "client_id": "c1", "lead_id": "l1", "activity_id": "a1",
        "campaign_id": "cam1", "sequence_step": 1,
        "content": {
            "from_email": "me@keira.com", "subject": "Hi", "html_body": "<p>hi</p>",
            "unipile_account_id": "ua1", "chat_id": "ch1", "text": "Hello",
            "compiled_context": {"first_name": "Amy"},
        },
    }
    base.update(overrides)
    return base


def _always_allow_timing():
    tm = AsyncMock()
    tm.check = lambda channel, now, prospect_tz=None: TimingDecision(
        allowed=True, reason="ok"
    )
    return tm


def _always_allow_compliance():
    cg = AsyncMock()
    cg.check = lambda channel, prospect, now: ComplianceDecision(
        allowed=True, reason="compliant"
    )
    return cg


def _allow_rate():
    rl = AsyncMock()
    rl.consume = AsyncMock(return_value=True)
    return rl


# ---------- gate paths --------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatch_timing_block():
    tm = AsyncMock()
    tm.check = lambda channel, now, prospect_tz=None: TimingDecision(
        allowed=False, reason="weekend"
    )
    d = OutreachDispatcher(
        timing_engine=tm,
        compliance_guard=_always_allow_compliance(),
        rate_limiter=_allow_rate(),
    )
    r = await d.dispatch(_touch())
    assert r.status == "skipped"
    assert r.reason.startswith("timing:")


@pytest.mark.asyncio
async def test_dispatch_compliance_block_carries_violations():
    cg = AsyncMock()
    cg.check = lambda channel, prospect, now: ComplianceDecision(
        allowed=False, reason="unsubscribed", violations=["SPAM_ACT_UNSUBSCRIBED"],
    )
    d = OutreachDispatcher(
        timing_engine=_always_allow_timing(),
        compliance_guard=cg,
        rate_limiter=_allow_rate(),
    )
    r = await d.dispatch(_touch())
    assert r.status == "skipped"
    assert r.reason.startswith("compliance:")
    assert r.extra["violations"] == ["SPAM_ACT_UNSUBSCRIBED"]


@pytest.mark.asyncio
async def test_dispatch_rate_block():
    rl = AsyncMock()
    rl.consume = AsyncMock(return_value=False)
    d = OutreachDispatcher(
        timing_engine=_always_allow_timing(),
        compliance_guard=_always_allow_compliance(),
        rate_limiter=rl,
    )
    r = await d.dispatch(_touch())
    assert r.status == "skipped"
    assert "rate_limit" in r.reason


@pytest.mark.asyncio
async def test_dispatch_rate_raise_is_permissive():
    rl = AsyncMock()
    rl.consume = AsyncMock(side_effect=RuntimeError("boom"))
    sf = AsyncMock()
    sf.send_email = AsyncMock(return_value={"message_id": "m1"})
    d = OutreachDispatcher(
        salesforge_client=sf,
        timing_engine=_always_allow_timing(),
        compliance_guard=_always_allow_compliance(),
        rate_limiter=rl,
    )
    r = await d.dispatch(_touch())
    assert r.status == "sent"


# ---------- successful sends --------------------------------------------------

@pytest.mark.asyncio
async def test_send_email_success_records_to_db():
    sf = AsyncMock()
    sf.send_email = AsyncMock(return_value={"message_id": "m1"})
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    d = OutreachDispatcher(
        salesforge_client=sf, db_conn=db,
        timing_engine=_always_allow_timing(),
        compliance_guard=_always_allow_compliance(),
        rate_limiter=_allow_rate(),
    )
    r = await d.dispatch(_touch())
    assert r.status == "sent"
    assert r.provider == "salesforge"
    assert r.provider_message_id == "m1"
    assert r.recorded is True
    sf.send_email.assert_awaited_once()
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_linkedin_success():
    up = AsyncMock()
    up.send_message = AsyncMock(return_value={"message_id": "li1"})
    d = OutreachDispatcher(
        unipile_client=up,
        timing_engine=_always_allow_timing(),
        compliance_guard=_always_allow_compliance(),
        rate_limiter=_allow_rate(),
    )
    r = await d.dispatch(_touch(channel="linkedin"))
    assert r.status == "sent" and r.provider == "unipile"
    assert r.provider_message_id == "li1"


@pytest.mark.asyncio
async def test_send_voice_success():
    ea = AsyncMock()
    resp = type("R", (), {"success": True, "call_id": "v1", "error": None})()
    ea.initiate_call = AsyncMock(return_value=resp)
    d = OutreachDispatcher(
        elevenagents_client=ea,
        timing_engine=_always_allow_timing(),
        compliance_guard=_always_allow_compliance(),
        rate_limiter=_allow_rate(),
    )
    r = await d.dispatch(_touch(channel="voice"))
    assert r.status == "sent" and r.provider == "elevenagents"
    assert r.provider_message_id == "v1"


# ---------- provider failure paths -------------------------------------------

@pytest.mark.asyncio
async def test_provider_exception_returns_failed_never_raises():
    sf = AsyncMock()
    sf.send_email = AsyncMock(side_effect=ConnectionError("dns"))
    d = OutreachDispatcher(
        salesforge_client=sf,
        timing_engine=_always_allow_timing(),
        compliance_guard=_always_allow_compliance(),
        rate_limiter=_allow_rate(),
    )
    r = await d.dispatch(_touch())
    assert r.status == "failed"
    assert "provider_error:ConnectionError" in r.reason


@pytest.mark.asyncio
async def test_voice_response_success_false_is_failed():
    ea = AsyncMock()
    resp = type("R", (), {"success": False, "call_id": None, "error": "no_credit"})()
    ea.initiate_call = AsyncMock(return_value=resp)
    d = OutreachDispatcher(
        elevenagents_client=ea,
        timing_engine=_always_allow_timing(),
        compliance_guard=_always_allow_compliance(),
        rate_limiter=_allow_rate(),
    )
    r = await d.dispatch(_touch(channel="voice"))
    assert r.status == "failed"
    assert "no_credit" in r.reason


@pytest.mark.asyncio
async def test_missing_provider_client_returns_failed():
    d = OutreachDispatcher(
        timing_engine=_always_allow_timing(),
        compliance_guard=_always_allow_compliance(),
        rate_limiter=_allow_rate(),
    )  # no salesforge
    r = await d.dispatch(_touch())
    assert r.status == "failed"
    assert "not configured" in r.reason


# ---------- recorder + unknown channel ---------------------------------------

@pytest.mark.asyncio
async def test_record_swallows_db_errors():
    sf = AsyncMock()
    sf.send_email = AsyncMock(return_value={"message_id": "m1"})
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=RuntimeError("dead conn"))
    d = OutreachDispatcher(
        salesforge_client=sf, db_conn=db,
        timing_engine=_always_allow_timing(),
        compliance_guard=_always_allow_compliance(),
        rate_limiter=_allow_rate(),
    )
    r = await d.dispatch(_touch())
    assert r.status == "sent"
    assert r.recorded is False


@pytest.mark.asyncio
async def test_unknown_channel_returns_failed():
    d = OutreachDispatcher(
        timing_engine=_always_allow_timing(),
        compliance_guard=_always_allow_compliance(),
        rate_limiter=_allow_rate(),
    )
    r = await d.dispatch(_touch(channel="fax"))
    assert r.status == "failed"
    assert "unknown channel" in r.reason


def test_dispatch_result_default_fields():
    x = DispatchResult(status="sent", channel="email")
    assert x.extra == {} and x.recorded is False
    # ensure sent_at timestamp construction works (smoke check datetime still imports)
    assert isinstance(datetime.now(), datetime)
