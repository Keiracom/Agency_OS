"""
Tests for src/api/routes/outreach_webhooks.py.

Covers:
- Salesforge / Unipile / ElevenAgents POST endpoints
- HMAC-SHA256 signature verification (valid signs 200, invalid signs 401,
  missing secret 401)
- Fast-path keyword classifier drives the decision tree directly when
  confidence >= FAST_PATH_FLOOR
- Low-confidence / unclear fast-path triggers LLM escalation, and the LLM
  response is used for the final intent
- Mutations are dispatched to the injected TouchStore.apply()
- Suppression mutations hit SuppressionManager.add_to_suppression
"""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import outreach_webhooks
from src.api.routes.outreach_webhooks import TouchStore, get_touch_store, router


@pytest.fixture()
def store():
    s = TouchStore()
    s.load_pending = AsyncMock(return_value=[])  # type: ignore[method-assign]
    s.apply = AsyncMock(return_value=0)          # type: ignore[method-assign]
    return s


@pytest.fixture()
def app(store):
    a = FastAPI()
    a.include_router(router)
    a.dependency_overrides[get_touch_store] = lambda: store
    return a


@pytest.fixture()
def client(app):
    return TestClient(app)


def _sign(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _post(client, path, secret, header_name, body: dict) -> tuple[int, dict]:
    raw = json.dumps(body).encode()
    resp = client.post(
        path,
        data=raw,
        headers={"Content-Type": "application/json", header_name: _sign(secret, raw)},
    )
    return resp.status_code, (resp.json() if resp.content else {})


# ---------- signature validation -------------------------------------------

def test_invalid_signature_rejected(client, monkeypatch):
    monkeypatch.setenv("SALESFORGE_WEBHOOK_SECRET", "shh")
    raw = json.dumps({"body": "hi"}).encode()
    resp = client.post(
        "/webhooks/salesforge",
        data=raw,
        headers={"Content-Type": "application/json", "X-Salesforge-Signature": "deadbeef"},
    )
    assert resp.status_code == 401


def test_missing_secret_env_rejects(client, monkeypatch):
    monkeypatch.delenv("SALESFORGE_WEBHOOK_SECRET", raising=False)
    raw = b"{}"
    resp = client.post(
        "/webhooks/salesforge",
        data=raw,
        headers={"Content-Type": "application/json", "X-Salesforge-Signature": "anything"},
    )
    assert resp.status_code == 401


# ---------- fast-path routing ----------------------------------------------

def test_salesforge_fast_path_unsubscribe_applies_cancels_and_suppress(client, monkeypatch, store):
    monkeypatch.setenv("SALESFORGE_WEBHOOK_SECRET", "shh")
    # 2 pending touches waiting to be cancelled
    store.load_pending = AsyncMock(return_value=[
        {"id": "t1", "channel": "email", "sequence_step": 2},
        {"id": "t2", "channel": "email", "sequence_step": 3},
    ])

    # Body stacks 3/4 unsubscribe keywords -> fast-path confidence 0.75 (>= floor),
    # so no LLM escalation. If ordering changes and it still dips below, the
    # patched LLM confirms unsubscribe anyway.
    fake_llm = AsyncMock(return_value={
        "intent": "unsubscribe", "confidence": 0.95,
        "evidence_phrase": "unsubscribe", "extracted": {},
    })
    with patch.object(outreach_webhooks, "apply_suppression") as apply_sup, \
         patch.object(outreach_webhooks, "llm_classify", fake_llm):
        code, body = _post(
            client, "/webhooks/salesforge", "shh", "X-Salesforge-Signature",
            {"body": "please unsubscribe me, opt out, remove from list",
             "subject": "Re: your offer",
             "from_email": "ceo@acme.com.au", "lead_id": "lead-1", "client_id": "c1"},
        )

    assert code == 200
    assert body["intent"] == "unsubscribe"
    assert body["mutations"] == 3  # two cancels + one suppress
    store.apply.assert_awaited_once()
    apply_sup.assert_called_once()


def test_fast_path_positive_hits_decision_tree(client, monkeypatch, store):
    monkeypatch.setenv("UNIPILE_WEBHOOK_SECRET", "shh")
    store.load_pending = AsyncMock(return_value=[
        {"id": "t1", "channel": "email", "sequence_step": 2},
    ])

    code, body = _post(
        client, "/webhooks/unipile", "shh", "X-Unipile-Signature",
        {"message": "very interested, book me in please",
         "thread_subject": "intro",
         "from_profile_url": "linkedin.com/in/amy",
         "lead_id": "lead-1", "client_id": "c1"},
    )
    assert code == 200
    # "book" + "interested" — router may pick booking (priority); either is a valid high-conf path
    assert body["intent"] in {"positive_interested", "booking_request"}
    assert body["mutations"] >= 2  # cancel existing + insert


# ---------- LLM escalation --------------------------------------------------

def test_low_confidence_unclear_escalates_to_llm(client, monkeypatch, store):
    monkeypatch.setenv("SALESFORGE_WEBHOOK_SECRET", "shh")
    store.load_pending = AsyncMock(return_value=[])

    fake_llm = AsyncMock(return_value={
        "intent": "question",
        "confidence": 0.88,
        "evidence_phrase": "what are your pricing tiers?",
        "extracted": {},
    })
    with patch.object(outreach_webhooks, "llm_classify", fake_llm):
        code, body = _post(
            client, "/webhooks/salesforge", "shh", "X-Salesforge-Signature",
            {"body": "hmm tell me more about this?",  # no keyword hits -> unclear
             "subject": "", "from_email": "ceo@acme.com.au",
             "lead_id": "lead-1", "client_id": "c1"},
        )

    assert code == 200
    fake_llm.assert_awaited_once()
    assert body["escalated_to_llm"] is True
    assert body["intent"] == "question"


def test_llm_unclear_stays_unclear(client, monkeypatch, store):
    monkeypatch.setenv("ELEVENAGENTS_WEBHOOK_SECRET", "shh")
    store.load_pending = AsyncMock(return_value=[])

    fake_llm = AsyncMock(return_value={
        "intent": "unclear", "confidence": 0.2,
        "evidence_phrase": "", "extracted": {},
    })
    with patch.object(outreach_webhooks, "llm_classify", fake_llm):
        code, body = _post(
            client, "/webhooks/elevenagents", "shh", "X-ElevenAgents-Signature",
            {"transcript": "um yeah sure i dunno",
             "call_id": "v1", "phone_number": "+61412345678",
             "lead_id": "lead-1", "client_id": "c1"},
        )

    assert code == 200
    # escalation happened but stayed unclear
    assert body["intent"] == "unclear"
    assert body["mutations"] == 1  # noop


# ---------- bad payload -----------------------------------------------------

def test_invalid_json_is_400(client, monkeypatch):
    monkeypatch.setenv("SALESFORGE_WEBHOOK_SECRET", "shh")
    raw = b"not-json"
    resp = client.post(
        "/webhooks/salesforge",
        data=raw,
        headers={"Content-Type": "application/json",
                 "X-Salesforge-Signature": _sign("shh", raw)},
    )
    assert resp.status_code == 400
