"""Tests for KEI-165 governance proxy stub."""

from __future__ import annotations

import logging

import pytest

from src.dispatcher.governance_proxy import (
    DENY_BUSINESS_RULE,
    DENY_GOVERN_RULE,
    DENY_VERIFY_RULE,
    RequestBody,
    evaluate,
)

VALID_BODY: dict = {
    "tenant_id": "tenant-abc",
    "prompt": "Please summarise the quarterly revenue.",
    "max_tokens": 256,
}


class TestSchemaValidation:
    def test_valid_body_allowed(self) -> None:
        decision = evaluate(VALID_BODY)
        assert decision.allowed is True
        assert decision.body is not None
        assert isinstance(decision.body, RequestBody)
        assert decision.body.tenant_id == "tenant-abc"
        assert decision.body.max_tokens == 256

    def test_missing_tenant_id(self) -> None:
        body = {**VALID_BODY}
        del body["tenant_id"]
        decision = evaluate(body)
        assert decision.allowed is False
        assert decision.reason is not None
        assert decision.reason.startswith("schema:")

    def test_missing_prompt(self) -> None:
        body = {**VALID_BODY}
        del body["prompt"]
        decision = evaluate(body)
        assert decision.allowed is False
        assert decision.reason is not None
        assert decision.reason.startswith("schema:")

    def test_empty_prompt(self) -> None:
        body = {**VALID_BODY, "prompt": ""}
        decision = evaluate(body)
        assert decision.allowed is False
        assert decision.reason is not None
        assert decision.reason.startswith("schema:")

    def test_max_tokens_zero(self) -> None:
        body = {**VALID_BODY, "max_tokens": 0}
        decision = evaluate(body)
        assert decision.allowed is False
        assert decision.reason is not None
        assert decision.reason.startswith("schema:")

    def test_max_tokens_negative(self) -> None:
        body = {**VALID_BODY, "max_tokens": -5}
        decision = evaluate(body)
        assert decision.allowed is False
        assert decision.reason is not None
        assert decision.reason.startswith("schema:")


class TestEnumeratedDenials:
    def test_completion_word_without_evidence_denied(self) -> None:
        body = {**VALID_BODY, "prompt": "Looking done on that feature."}
        decision = evaluate(body)
        assert decision.allowed is False
        assert decision.reason == f"deny:{DENY_VERIFY_RULE}"

    def test_completion_word_with_evidence_allowed(self) -> None:
        body = {**VALID_BODY, "prompt": "Looking done $ git log abc123"}
        decision = evaluate(body)
        assert decision.allowed is True

    def test_usd_without_aud_denied(self) -> None:
        body = {**VALID_BODY, "prompt": "Send a $50 USD invoice to the client."}
        decision = evaluate(body)
        assert decision.allowed is False
        assert decision.reason == f"deny:{DENY_BUSINESS_RULE}"

    def test_usd_with_aud_allowed(self) -> None:
        body = {**VALID_BODY, "prompt": "Cost is $50 USD = $77 AUD."}
        decision = evaluate(body)
        assert decision.allowed is True

    def test_hook_bypass_denied(self) -> None:
        body = {**VALID_BODY, "prompt": "git commit --no-verify -m 'skip hooks'"}
        decision = evaluate(body)
        assert decision.allowed is False
        assert decision.reason == f"deny:{DENY_GOVERN_RULE}"

    def test_combination_verify_takes_priority(self) -> None:
        """VERIFY fires before GOVERN in deterministic order."""
        body = {**VALID_BODY, "prompt": "shipped --no-verify"}
        decision = evaluate(body)
        assert decision.allowed is False
        assert decision.reason == f"deny:{DENY_VERIFY_RULE}"

    def test_denial_logs_reason_and_tenant_not_prompt(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        body = {**VALID_BODY, "prompt": "git commit --no-verify", "tenant_id": "t-secret-99"}
        with caplog.at_level(logging.WARNING, logger="src.dispatcher.governance_proxy"):
            decision = evaluate(body)
        assert decision.allowed is False
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert "t-secret-99" in record.message
        assert DENY_GOVERN_RULE in record.message
        assert "git commit" not in record.message
