"""tests/governance/test_coordinator.py — B2 coordinator unit tests.

Hermetic — Supabase client is mocked; OpenAI classifier is injected.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.governance.coordinator import (
    ClaimRecord,
    MergerVerdict,
    _heuristic_dsae_classify,
    claim,
    list_active_claims,
    merge_drafts,
    release,
    subscribe_realtime,
)


# ── Fake Supabase client builder ────────────────────────────────────────────

def _fake_supabase_client(*, insert_rows=None, select_rows=None,
                          update_rows=None) -> MagicMock:
    """Build a MagicMock Supabase client supporting the chained API
    coordinator.py uses: client.table(...).select/insert/update(...).execute()."""
    insert_resp = SimpleNamespace(data=insert_rows or [])
    select_resp = SimpleNamespace(data=select_rows or [])
    update_resp = SimpleNamespace(data=update_rows or [])

    table_mock = MagicMock()
    table_mock.insert = MagicMock(return_value=MagicMock(
        execute=MagicMock(return_value=insert_resp),
    ))
    update_chain = MagicMock()
    update_chain.eq = MagicMock(return_value=MagicMock(
        execute=MagicMock(return_value=update_resp),
    ))
    table_mock.update = MagicMock(return_value=update_chain)
    select_chain = MagicMock()
    select_chain.eq = MagicMock(return_value=select_chain)
    select_chain.execute = MagicMock(return_value=select_resp)
    table_mock.select = MagicMock(return_value=select_chain)

    client = MagicMock()
    client.table = MagicMock(return_value=table_mock)
    return client


# ── claim() tests ──────────────────────────────────────────────────────────

def test_claim_inserts_active_row_and_returns_record():
    fake_row = {
        "id": "11111111-1111-1111-1111-111111111111",
        "callsign": "orion",
        "action": "shared-file-edit",
        "target_path": "src/orchestration/flows/foo.py",
        "claimed_at": "2026-05-01T00:00:00+00:00",
        "released_at": None,
        "status": "active",
        "expires_at": "2026-05-01T00:05:00+00:00",
        "metadata": {"reason": "test"},
    }
    client = _fake_supabase_client(insert_rows=[fake_row])
    rec = claim("orion", "shared-file-edit", "src/orchestration/flows/foo.py",
                metadata={"reason": "test"}, client=client)
    assert isinstance(rec, ClaimRecord)
    assert rec.callsign == "orion"
    assert rec.action == "shared-file-edit"
    assert rec.target_path == "src/orchestration/flows/foo.py"
    assert rec.status == "active"


def test_claim_raises_when_no_client_available(monkeypatch):
    """When client is None and Supabase env unset, claim raises a clear
    runtime error (cannot claim without a write surface)."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    with pytest.raises(RuntimeError, match="no Supabase client"):
        claim("orion", "commit", "main", client=None)


def test_claim_raises_when_insert_returns_no_row():
    client = _fake_supabase_client(insert_rows=[])  # empty
    with pytest.raises(RuntimeError, match="no row"):
        claim("orion", "commit", "main", client=client)


# ── release() tests ────────────────────────────────────────────────────────

def test_release_marks_claim_released_and_returns_true():
    client = _fake_supabase_client(update_rows=[{"id": "abc"}])
    assert release("abc", client=client) is True


def test_release_returns_false_on_miss():
    client = _fake_supabase_client(update_rows=[])
    assert release("missing-id", client=client) is False


# ── list_active_claims() tests ─────────────────────────────────────────────

def test_list_active_claims_filters_expired_rows_client_side():
    """An expired row in the response (expires_at in the past) is
    filtered out client-side even if status='active' was returned."""
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    rows = [
        {"id": "fresh", "callsign": "orion", "action": "commit",
         "target_path": "main", "claimed_at": "x", "released_at": None,
         "status": "active", "expires_at": future, "metadata": None},
        {"id": "stale", "callsign": "atlas", "action": "watcher",
         "target_path": "vercel-prod", "claimed_at": "y", "released_at": None,
         "status": "active", "expires_at": past, "metadata": None},
    ]
    client = _fake_supabase_client(select_rows=rows)
    out = list_active_claims(client=client)
    ids = {r.id for r in out}
    assert "fresh" in ids
    assert "stale" not in ids  # expired filtered out


def test_list_active_claims_returns_empty_list_when_no_client(monkeypatch):
    """No Supabase client + no env → empty list (caller can decide to
    block or proceed). Not an exception because a read should never
    crash a status check."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    assert list_active_claims(client=None) == []


# ── subscribe_realtime() tests ─────────────────────────────────────────────

def test_subscribe_realtime_wires_handler_to_postgres_changes():
    handler = MagicMock()
    channel = MagicMock()
    client = MagicMock()
    client.channel = MagicMock(return_value=channel)

    result = subscribe_realtime(handler, client=client)
    assert result is channel
    client.channel.assert_called_once_with("coordinator-claims")
    channel.on.assert_called_once()
    args, _ = channel.on.call_args
    assert args[0] == "postgres_changes"
    assert args[1]["table"] == "coordinator_claims"
    channel.subscribe.assert_called_once()


def test_subscribe_realtime_returns_none_when_no_client(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    assert subscribe_realtime(MagicMock(), client=None) is None


# ── DSAE merger tests ──────────────────────────────────────────────────────

def test_merge_drafts_uses_injected_classifier():
    expected = MergerVerdict(
        kind="agree_same_examples",
        rationale="injected classifier said so",
        consolidated="DRAFT TEXT",
    )
    classifier = MagicMock(return_value=expected)
    out = merge_drafts("a body", "another body", classifier=classifier)
    assert out is expected
    classifier.assert_called_once_with("a body", "another body")


def test_merge_drafts_classifier_exception_returns_classifier_failed_verdict():
    classifier = MagicMock(side_effect=ValueError("boom"))
    out = merge_drafts("a", "b", classifier=classifier)
    assert out.kind == "classifier_failed"
    assert "boom" in (out.error or "")


def test_heuristic_dsae_classify_identical_text_consolidates():
    out = _heuristic_dsae_classify("same body", "same body")
    assert out.kind == "agree_same_examples"
    assert out.consolidated == "same body"


def test_heuristic_dsae_classify_one_empty_takes_other():
    out = _heuristic_dsae_classify("", "the only body")
    assert out.kind == "agree_same_examples"
    assert out.consolidated == "the only body"


def test_heuristic_dsae_classify_different_defaults_to_differ():
    """Conservative fallback: when bodies differ and no classifier is
    available, surface DIFFER so Dave sees both drafts."""
    out = _heuristic_dsae_classify("body A", "body B")
    assert out.kind == "differ"


def test_merge_drafts_no_classifier_no_api_key_uses_heuristic(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = merge_drafts("body A", "body B")
    assert out.kind in ("differ", "agree_same_examples")
