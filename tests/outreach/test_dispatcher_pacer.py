"""
Tests for SendPacer integration in OutreachDispatcher.

Coverage:
    1. Dispatcher with no pacer configured — asyncio.sleep never called.
    2. Dispatcher with pacer + delay > 0 — asyncio.sleep called with that delay.
    3. Dispatcher records send on pacer after successful send.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.outreach.dispatcher import OutreachDispatcher
from src.outreach.safety.compliance_guard import ComplianceDecision
from src.outreach.safety.send_pacer import SendPacer
from src.outreach.safety.timing_engine import Channel, TimingDecision


# ---------- helpers -----------------------------------------------------------


def _touch(channel="email", account_id="mailbox-1") -> dict:
    return {
        "channel": channel,
        "account_id": account_id,
        "prospect": {
            "email": "ceo@acme.com.au",
            "phone": "+61412345678",
            "tz": "Australia/Sydney",
        },
        "client_id": "c1",
        "lead_id": "l1",
        "activity_id": "a1",
        "campaign_id": "cam1",
        "sequence_step": 1,
        "content": {
            "from_email": "me@keira.com",
            "subject": "Hi",
            "html_body": "<p>hi</p>",
        },
    }


def _allow_timing():
    tm = MagicMock()
    tm.check = lambda channel, now, prospect_tz=None: TimingDecision(allowed=True, reason="ok")
    return tm


def _allow_compliance():
    cg = MagicMock()
    cg.check = lambda channel, prospect, now: ComplianceDecision(allowed=True, reason="compliant")
    return cg


def _mock_salesforge(success: bool = True) -> AsyncMock:
    client = AsyncMock()
    if success:
        client.send_email = AsyncMock(return_value={"message_id": "msg-1"})
    else:
        client.send_email = AsyncMock(side_effect=RuntimeError("provider down"))
    return client


def _allow_rate() -> AsyncMock:
    rl = AsyncMock()
    rl.consume = AsyncMock(return_value=True)
    return rl


# ---------- test 1: no pacer — asyncio.sleep never called ---------------------


@pytest.mark.asyncio
async def test_no_pacer_no_sleep():
    dispatcher = OutreachDispatcher(
        salesforge_client=_mock_salesforge(),
        timing_engine=_allow_timing(),
        compliance_guard=_allow_compliance(),
        rate_limiter=_allow_rate(),
        send_pacer=None,
    )
    with patch("src.outreach.dispatcher.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await dispatcher.dispatch(_touch())

    mock_sleep.assert_not_called()


# ---------- test 2: pacer with delay > 0 — sleep called with returned delay ---


@pytest.mark.asyncio
async def test_pacer_with_positive_delay_calls_sleep():
    pacer = MagicMock(spec=SendPacer)
    pacer.compute_delay.return_value = 45.0
    pacer.record_send = MagicMock()

    dispatcher = OutreachDispatcher(
        salesforge_client=_mock_salesforge(),
        timing_engine=_allow_timing(),
        compliance_guard=_allow_compliance(),
        rate_limiter=_allow_rate(),
        send_pacer=pacer,
    )
    with patch("src.outreach.dispatcher.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await dispatcher.dispatch(_touch())

    mock_sleep.assert_called_once_with(45.0)


# ---------- test 3: pacer.record_send called after successful send ------------


@pytest.mark.asyncio
async def test_pacer_record_send_called_on_success():
    pacer = MagicMock(spec=SendPacer)
    pacer.compute_delay.return_value = 0.0
    pacer.record_send = MagicMock()

    dispatcher = OutreachDispatcher(
        salesforge_client=_mock_salesforge(success=True),
        timing_engine=_allow_timing(),
        compliance_guard=_allow_compliance(),
        rate_limiter=_allow_rate(),
        send_pacer=pacer,
    )
    with patch("src.outreach.dispatcher.asyncio.sleep", new_callable=AsyncMock):
        result = await dispatcher.dispatch(_touch(account_id="mailbox-99"))

    assert result.status == "sent"
    pacer.record_send.assert_called_once()
    call_kwargs = pacer.record_send.call_args
    assert call_kwargs.kwargs["channel"] == Channel.EMAIL
    assert call_kwargs.kwargs["account_id"] == "mailbox-99"


# ---------- bonus: pacer.record_send NOT called when send fails ---------------


@pytest.mark.asyncio
async def test_pacer_record_send_not_called_on_failure():
    pacer = MagicMock(spec=SendPacer)
    pacer.compute_delay.return_value = 0.0
    pacer.record_send = MagicMock()

    dispatcher = OutreachDispatcher(
        salesforge_client=_mock_salesforge(success=False),
        timing_engine=_allow_timing(),
        compliance_guard=_allow_compliance(),
        rate_limiter=_allow_rate(),
        send_pacer=pacer,
    )
    with patch("src.outreach.dispatcher.asyncio.sleep", new_callable=AsyncMock):
        result = await dispatcher.dispatch(_touch())

    assert result.status == "failed"
    pacer.record_send.assert_not_called()
