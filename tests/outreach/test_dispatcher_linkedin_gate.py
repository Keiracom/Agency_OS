"""
Tests for dispatcher LinkedIn DM gate (PHASE-2-SLICE-7 Track D).

Verifies that OutreachDispatcher.send_linkedin consults LinkedInAccountState
before firing a DM and skips with linkedin_gate:connect_not_accepted when the
connect is pending, rejected, or stale_skipped.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.outreach.dispatcher import OutreachDispatcher
from src.outreach.safety.linkedin_account_state import (
    ConnectionRecord,
    LinkedInAccountState,
    LinkedInState,
)


class _FakeStore:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], ConnectionRecord] = {}

    def get(self, account_id: str, prospect_id: str) -> ConnectionRecord | None:
        return self.rows.get((account_id, prospect_id))

    def upsert(self, record: ConnectionRecord) -> None:
        self.rows[(record.account_id, record.prospect_id)] = record

    def list_pending(self, account_id: str | None = None) -> list[ConnectionRecord]:
        return list(self.rows.values())


def _seed(state: LinkedInState) -> tuple[LinkedInAccountState, _FakeStore]:
    store = _FakeStore()
    clock = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    mgr = LinkedInAccountState(
        get_record=store.get,
        upsert_record=store.upsert,
        list_pending=store.list_pending,
        now_fn=lambda: clock,
    )
    store.upsert(ConnectionRecord(
        account_id="acct-1", prospect_id="p-1", state=state,
        sent_at=clock, accepted_at=clock if state is LinkedInState.ACCEPTED else None,
        days_pending=0,
    ))
    return mgr, store


def _touch(event_type: str | None = "message") -> dict:
    content: dict = {
        "unipile_account_id": "acct-1",
        "chat_id": "chat-xyz",
        "text": "hello",
    }
    if event_type is not None:
        content["event_type"] = event_type
    return {
        "channel": "linkedin",
        "prospect_id": "p-1",
        "lead_id": "lead-1",
        "client_id": "client-1",
        "content": content,
    }


def _dispatcher(linkedin_state, unipile_response=None) -> OutreachDispatcher:
    unipile = MagicMock()
    unipile.send_message = AsyncMock(return_value=unipile_response or {"message_id": "mid-1"})
    # rate_limiter=None prevents auto-instantiation (which would need 5 injected
    # callables not relevant to this gate test).
    return OutreachDispatcher(
        unipile_client=unipile,
        linkedin_state=linkedin_state,
        rate_limiter=None,
    )


# -- dispatch-level DM gate (the 4 required scenarios) ---------------------

@pytest.mark.asyncio
async def test_accepted_allows_dm():
    mgr, _ = _seed(LinkedInState.ACCEPTED)
    d = _dispatcher(mgr)
    result = await d.send_linkedin(_touch())
    assert result.status == "sent"
    assert result.provider == "unipile"
    d.unipile.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_pending_connect_blocks_dm():
    mgr, _ = _seed(LinkedInState.CONNECT_SENT)
    d = _dispatcher(mgr)
    result = await d.send_linkedin(_touch())
    assert result.status == "skipped"
    assert result.reason == "linkedin_gate:connect_not_accepted"
    assert result.extra["event_type"] == "message"
    d.unipile.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejected_blocks_dm():
    mgr, _ = _seed(LinkedInState.REJECTED)
    d = _dispatcher(mgr)
    result = await d.send_linkedin(_touch())
    assert result.status == "skipped"
    assert result.reason == "linkedin_gate:connect_not_accepted"
    d.unipile.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_skipped_blocks_dm():
    mgr, _ = _seed(LinkedInState.STALE_SKIPPED)
    d = _dispatcher(mgr)
    result = await d.send_linkedin(_touch())
    assert result.status == "skipped"
    assert result.reason == "linkedin_gate:connect_not_accepted"


# -- gate-bypass paths ------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_event_bypasses_gate_even_without_record():
    # No record for (acct-1, p-1) → allows_dm=False, but event_type=connect
    # should skip the gate entirely (connects are how we REACH accepted).
    store = _FakeStore()
    mgr = LinkedInAccountState(
        get_record=store.get, upsert_record=store.upsert,
        list_pending=store.list_pending,
    )
    d = _dispatcher(mgr)
    result = await d.send_linkedin(_touch(event_type="connect"))
    assert result.status == "sent"


@pytest.mark.asyncio
async def test_gate_disabled_when_no_linkedin_state_configured():
    # linkedin_state=None → dispatcher fires regardless of connect status.
    unipile = MagicMock()
    unipile.send_message = AsyncMock(return_value={"message_id": "mid-1"})
    d = OutreachDispatcher(
        unipile_client=unipile, linkedin_state=None, rate_limiter=None,
    )
    result = await d.send_linkedin(_touch())
    assert result.status == "sent"


@pytest.mark.asyncio
async def test_gate_default_event_type_is_message():
    # Missing event_type on content → treated as DM → blocked when not accepted.
    mgr, _ = _seed(LinkedInState.CONNECT_SENT)
    d = _dispatcher(mgr)
    result = await d.send_linkedin(_touch(event_type=None))
    assert result.status == "skipped"
    assert result.reason == "linkedin_gate:connect_not_accepted"
