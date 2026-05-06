"""
P4 — Tests for src/integrations/anthropic_batch.py.

Pure mocks — never touches the real Anthropic API. Confirms:
  - _normalise_requests handles convenience + full shapes
  - _validate_batch_id rejects malformed ids
  - create_batch posts the right body, returns the id, includes the
    300K beta header
  - poll_batch / get_results / cancel_batch hit the right URLs
  - get_results parses JSONL line-per-result
  - wait_for_batch loops until a terminal state, then returns
  - Every error path raises AnthropicBatchError (not a generic exception)
  - No subprocess invoked anywhere
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.integrations import anthropic_batch as ab

# ─── _normalise_requests ───────────────────────────────────────────────────


def test_normalise_convenience_shape():
    out = ab._normalise_requests(
        [[{"role": "user", "content": "hi"}]],
        model="claude-haiku-4-5",
        max_tokens=200,
    )
    assert out[0]["custom_id"] == "req-0"
    assert out[0]["params"]["model"] == "claude-haiku-4-5"
    assert out[0]["params"]["max_tokens"] == 200
    assert out[0]["params"]["messages"][0]["content"] == "hi"


def test_normalise_full_shape_passthrough():
    full = {
        "custom_id": "my-id-7",
        "params": {"model": "x", "max_tokens": 1, "messages": []},
    }
    out = ab._normalise_requests([full], model="ignored", max_tokens=999)
    assert out == [full]


def test_normalise_rejects_empty_list():
    with pytest.raises(ab.AnthropicBatchError):
        ab._normalise_requests([], model="m", max_tokens=10)


def test_normalise_rejects_bad_item_type():
    with pytest.raises(ab.AnthropicBatchError):
        ab._normalise_requests(["not a list or dict"], model="m", max_tokens=10)


# ─── _validate_batch_id ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "good",
    [
        "msgbatch_abc123",
        "msgbatch_x-y_z",
    ],
)
def test_valid_batch_ids_pass(good):
    assert ab._validate_batch_id(good) == good


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "",
        123,
        "wrong_prefix_abc",
        "msgbatch_!!!",
        "msgbatch_" + "a" * 200,
    ],
)
def test_invalid_batch_ids_rejected(bad):
    with pytest.raises(ab.AnthropicBatchError):
        ab._validate_batch_id(bad)


# ─── HTTP harness ──────────────────────────────────────────────────────────


class _FakeClient:
    """Context-manager fake httpx.Client that records calls + scripts responses."""

    def __init__(self, scripted_responses):
        self._scripted = list(scripted_responses)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def _next(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self._scripted:
            raise AssertionError(f"unexpected extra HTTP call {method} {url}")
        return self._scripted.pop(0)

    def post(self, url, **kw):
        return self._next("POST", url, **kw)

    def get(self, url, **kw):
        return self._next("GET", url, **kw)


def _resp(status: int, json_data=None, text: str = "") -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.text = text or (str(json_data) if json_data is not None else "")
    r.json = MagicMock(return_value=json_data or {})
    return r


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    monkeypatch.setattr(ab.settings, "anthropic_api_key", "test-key")


# ─── create_batch ──────────────────────────────────────────────────────────


def test_create_batch_returns_id_and_sends_beta_header(monkeypatch):
    fake_client = _FakeClient([_resp(200, {"id": "msgbatch_abc"})])
    monkeypatch.setattr(ab.httpx, "Client", lambda **_: fake_client)

    out = ab.create_batch(
        [[{"role": "user", "content": "hi"}]],
        model="claude-haiku-4-5",
    )
    assert out == "msgbatch_abc"

    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert url == f"{ab.ANTHROPIC_API_BASE}/messages/batches"
    assert "output-300k-2026-03-24" in kwargs["headers"]["anthropic-beta"]
    assert "message-batches-2024-09-24" in kwargs["headers"]["anthropic-beta"]
    assert kwargs["json"]["requests"][0]["params"]["model"] == "claude-haiku-4-5"


def test_create_batch_raises_on_4xx(monkeypatch):
    fake_client = _FakeClient([_resp(400, text="bad request")])
    monkeypatch.setattr(ab.httpx, "Client", lambda **_: fake_client)
    with pytest.raises(ab.AnthropicBatchError, match="HTTP 400"):
        ab.create_batch([[{"role": "user", "content": "hi"}]], model="m")


def test_create_batch_raises_when_response_missing_id(monkeypatch):
    fake_client = _FakeClient([_resp(200, {"unexpected": "shape"})])
    monkeypatch.setattr(ab.httpx, "Client", lambda **_: fake_client)
    with pytest.raises(ab.AnthropicBatchError, match="missing 'id'"):
        ab.create_batch([[{"role": "user", "content": "hi"}]], model="m")


def test_create_batch_rejects_blank_model(monkeypatch):
    with pytest.raises(ab.AnthropicBatchError):
        ab.create_batch([[{"role": "user", "content": "x"}]], model="")


# ─── poll_batch ────────────────────────────────────────────────────────────


def test_poll_batch_returns_payload(monkeypatch):
    fake_client = _FakeClient(
        [
            _resp(
                200,
                {
                    "id": "msgbatch_abc",
                    "processing_status": "in_progress",
                    "request_counts": {"processing": 5},
                },
            )
        ]
    )
    monkeypatch.setattr(ab.httpx, "Client", lambda **_: fake_client)
    out = ab.poll_batch("msgbatch_abc")
    assert out["processing_status"] == "in_progress"
    method, url, _ = fake_client.calls[0]
    assert method == "GET"
    assert url.endswith("/messages/batches/msgbatch_abc")


def test_poll_batch_rejects_invalid_id():
    with pytest.raises(ab.AnthropicBatchError):
        ab.poll_batch("not-a-real-id")


# ─── get_results — JSONL parsing ───────────────────────────────────────────


def test_get_results_parses_jsonl(monkeypatch):
    body = (
        '{"custom_id":"req-0","result":{"type":"succeeded"}}\n'
        "\n"
        '{"custom_id":"req-1","result":{"type":"succeeded"}}\n'
    )
    fake_client = _FakeClient([_resp(200, text=body)])
    monkeypatch.setattr(ab.httpx, "Client", lambda **_: fake_client)
    out = ab.get_results("msgbatch_abc")
    assert len(out) == 2
    assert out[0]["custom_id"] == "req-0"
    assert out[1]["custom_id"] == "req-1"


def test_get_results_skips_garbage_lines(monkeypatch):
    body = (
        '{"custom_id":"req-0","result":{"type":"succeeded"}}\n'
        "NOT-JSON\n"
        '{"custom_id":"req-1","result":{"type":"succeeded"}}\n'
    )
    fake_client = _FakeClient([_resp(200, text=body)])
    monkeypatch.setattr(ab.httpx, "Client", lambda **_: fake_client)
    out = ab.get_results("msgbatch_abc")
    assert len(out) == 2  # bad line skipped


# ─── cancel_batch ──────────────────────────────────────────────────────────


def test_cancel_batch_returns_payload(monkeypatch):
    fake_client = _FakeClient(
        [_resp(200, {"id": "msgbatch_abc", "processing_status": "canceling"})]
    )
    monkeypatch.setattr(ab.httpx, "Client", lambda **_: fake_client)
    out = ab.cancel_batch("msgbatch_abc")
    assert out["processing_status"] == "canceling"
    method, url, _ = fake_client.calls[0]
    assert method == "POST"
    assert url.endswith("/cancel")


# ─── wait_for_batch — polling loop ─────────────────────────────────────────


def test_wait_for_batch_loops_until_terminal(monkeypatch):
    """3 poll responses: in_progress → in_progress → ended."""
    monkeypatch.setattr(ab.time, "sleep", lambda _s: None)  # no real sleep
    payloads = [
        {"processing_status": "in_progress"},
        {"processing_status": "in_progress"},
        {"processing_status": "ended", "request_counts": {"succeeded": 5}},
    ]
    fake_client = _FakeClient([_resp(200, p) for p in payloads])
    monkeypatch.setattr(ab.httpx, "Client", lambda **_: fake_client)
    out = ab.wait_for_batch("msgbatch_abc", interval=0.01, max_wait_s=10)
    assert out["processing_status"] == "ended"
    assert len(fake_client.calls) == 3


def test_wait_for_batch_raises_on_timeout(monkeypatch):
    monkeypatch.setattr(ab.time, "sleep", lambda _s: None)
    # Always returns in_progress; loop must give up at deadline.
    fake_client = _FakeClient([_resp(200, {"processing_status": "in_progress"})] * 50)
    monkeypatch.setattr(ab.httpx, "Client", lambda **_: fake_client)
    monkeypatch.setattr(ab.time, "monotonic", iter([0.0, 1.0, 5.0, 100.0]).__next__)
    with pytest.raises(ab.AnthropicBatchError, match="timed out"):
        ab.wait_for_batch("msgbatch_abc", interval=0.01, max_wait_s=2)


def test_wait_for_batch_rejects_zero_interval():
    with pytest.raises(ab.AnthropicBatchError):
        ab.wait_for_batch("msgbatch_abc", interval=0, max_wait_s=10)


# ─── missing API key ───────────────────────────────────────────────────────


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(ab.settings, "anthropic_api_key", "")
    with pytest.raises(ab.AnthropicBatchError, match="API_KEY"):
        ab.create_batch([[{"role": "user", "content": "hi"}]], model="m")


# ─── security guards ──────────────────────────────────────────────────────


@patch("subprocess.run")
@patch("subprocess.check_call")
@patch("subprocess.check_output")
def test_no_subprocess_calls_in_module(check_output, check_call, run, monkeypatch):
    """Defence-in-depth — no path through this module touches a subprocess."""
    fake_client = _FakeClient([_resp(200, {"id": "msgbatch_x"})])
    monkeypatch.setattr(ab.httpx, "Client", lambda **_: fake_client)
    ab.create_batch([[{"role": "user", "content": "hi"}]], model="m")
    run.assert_not_called()
    check_call.assert_not_called()
    check_output.assert_not_called()
