"""Tests for src/keiracom_system/vault/api_agent_cold_start.py (Agency_OS-l6i2)."""

from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock

import pytest

from src.keiracom_system.vault import api_agent_cold_start as aacs

# ---------------------------------------------------------------------------
# CALLSIGN_TO_PERSONA mapping
# ---------------------------------------------------------------------------


def test_callsign_to_persona_covers_all_chain_callsigns():
    """Every V1 chain callsign + face must have a persona mapping."""
    expected = {"aiden", "max", "nova", "orion", "atlas", "face"}
    assert set(aacs.CALLSIGN_TO_PERSONA.keys()) >= expected
    assert aacs.CALLSIGN_TO_PERSONA["aiden"] == ("deliberator", "aiden")
    assert aacs.CALLSIGN_TO_PERSONA["nova"] == ("worker", "nova")
    assert aacs.CALLSIGN_TO_PERSONA["atlas"] == ("reviewer", "atlas")


# ---------------------------------------------------------------------------
# compute_cost
# ---------------------------------------------------------------------------


def test_compute_cost_zero_tokens_zero_cost():
    usd, aud = aacs.compute_cost(0, 0)
    assert usd == 0.0
    assert aud == 0.0


def test_compute_cost_sample_tokens_and_aud_conversion():
    """1M input + 1M output → USD = 3 + 15 = 18; AUD = 18 * 1.55 = 27.9."""
    usd, aud = aacs.compute_cost(1_000_000, 1_000_000)
    assert usd == pytest.approx(18.0)
    assert aud == pytest.approx(27.9)


def test_compute_cost_small_values_preserves_precision():
    """100 in + 200 out → USD = (100*3 + 200*15)/1e6 = 0.0033."""
    usd, _ = aacs.compute_cost(100, 200)
    assert usd == pytest.approx(0.0033)


# ---------------------------------------------------------------------------
# fetch_persona — success / 404 retry / hard error / unknown callsign
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def test_fetch_persona_success(monkeypatch: pytest.MonkeyPatch):
    """Happy path: 200 with prompt_text returns (prompt, token_count) tuple."""
    captured: dict = {}

    def fake_urlopen(url, timeout=None):
        captured["url"] = url
        return _FakeResp(json.dumps({"prompt_text": "Atlas persona", "token_count": 805}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = aacs.fetch_persona("atlas")
    assert result == ("Atlas persona", 805)
    assert "/dispatcher/persona" in captured["url"]
    assert "role=reviewer" in captured["url"]
    assert "variant=atlas" in captured["url"]


def test_fetch_persona_404_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch):
    """404 → retry; eventually 200 returns (prompt, token_count). Short retry config."""
    import urllib.error

    monkeypatch.setattr(aacs, "_PERSONA_RETRY_MAX_SECONDS", 5)
    monkeypatch.setattr(aacs, "_PERSONA_RETRY_INTERVAL", 0.01)
    monkeypatch.setattr("time.sleep", lambda _s: None)

    calls = {"n": 0}

    def fake_urlopen(url, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)
        return _FakeResp(json.dumps({"prompt_text": "Nova worker", "token_count": 104}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = aacs.fetch_persona("nova")
    assert result == ("Nova worker", 104)
    assert calls["n"] == 3


def test_fetch_persona_non_404_http_error_returns_none(monkeypatch: pytest.MonkeyPatch):
    """500 (or any non-404 HTTP) is terminal — return None immediately."""
    import urllib.error

    def fake_urlopen(url, timeout=None):
        raise urllib.error.HTTPError(url, 500, "server error", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert aacs.fetch_persona("atlas") is None


def test_fetch_persona_unknown_callsign_returns_none():
    """No mapping → log error + return None (no HTTP call)."""
    assert aacs.fetch_persona("ghost") is None


# ---------------------------------------------------------------------------
# insert_attribution — fail-open + SQL shape
# ---------------------------------------------------------------------------


def _fake_conn() -> tuple[MagicMock, MagicMock]:
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn, cur


def test_insert_attribution_inserts_all_columns():
    conn, cur = _fake_conn()
    aacs.insert_attribution(
        callsign="aiden",
        chain_id="c1",
        task_id="t1",
        chain_step="aiden_plan",
        input_tokens=100,
        output_tokens=200,
        cost_usd=0.0033,
        cost_aud=0.005115,
        latency_ms=1234.5,
        conn=conn,
    )
    sql = cur.execute.call_args[0][0]
    params = cur.execute.call_args[0][1]
    assert "INSERT INTO public.keiracom_spawn_attribution" in sql
    assert "input_tokens" in sql and "output_tokens" in sql
    assert "cost_usd" in sql and "cost_aud" in sql
    assert "latency_ms" in sql and "chain_id" in sql and "task_id" in sql
    # params positional, in column order
    assert "aiden" in params
    assert 100 in params and 200 in params
    assert 0.0033 in params and 0.005115 in params


def test_insert_attribution_maps_chain_step_to_task_type():
    """V1-battery prep fix — chain_step (chain position) maps to TASK_TYPES
    (workload class) before INSERT. Raw chain_step value MUST NOT land in
    task_type column or the table CHECK constraint rejects the row.
    """
    conn, cur = _fake_conn()
    aacs.insert_attribution(
        callsign="nova",
        chain_id="c1",
        task_id="t1",
        chain_step="nova_build",
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.0,
        cost_aud=0.0,
        latency_ms=1.0,
        conn=conn,
    )
    params = cur.execute.call_args[0][1]
    # Mapped workload class lands in task_type position; raw chain_step does not.
    assert "build" in params
    assert "nova_build" not in params


def test_insert_attribution_unknown_chain_step_maps_to_unknown_task_type():
    """Chain step outside the canonical map → task_type='unknown' (honest fallback)."""
    conn, cur = _fake_conn()
    aacs.insert_attribution(
        callsign="atlas",
        chain_id="c2",
        task_id="t2",
        chain_step="some_future_step",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        cost_aud=0.0,
        latency_ms=0.0,
        conn=conn,
    )
    params = cur.execute.call_args[0][1]
    assert "unknown" in params
    assert "some_future_step" not in params


def test_insert_attribution_failopen_on_db_error():
    """conn.cursor() raising → logged + returns None (does NOT raise)."""
    conn = MagicMock()
    conn.cursor.side_effect = RuntimeError("DB down")
    # No exception bubbled.
    aacs.insert_attribution(
        callsign="aiden",
        chain_id="c1",
        task_id="t1",
        chain_step="aiden_plan",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        cost_aud=0.0,
        latency_ms=0.0,
        conn=conn,
    )


# ---------------------------------------------------------------------------
# call_anthropic — passes correct args
# ---------------------------------------------------------------------------


def test_call_anthropic_passes_model_system_brief_and_returns_text_tokens(
    monkeypatch: pytest.MonkeyPatch,
):
    """anthropic.Anthropic(api_key=...).messages.create(model, max_tokens, system, messages)."""
    captured: dict = {}

    class _FakeContent:
        def __init__(self, text):
            self.text = text

    class _FakeUsage:
        input_tokens = 42
        output_tokens = 137

    class _FakeResponse:
        content = [_FakeContent("Atlas safety-review verdict: looks OK.")]
        usage = _FakeUsage()

    class _FakeClient:
        def __init__(self, *, api_key):
            captured["api_key"] = api_key
            self.messages = self

        def create(self, **kwargs):
            captured["create_kwargs"] = kwargs
            return _FakeResponse()

    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = _FakeClient
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    text, in_t, out_t, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")

    assert text == "Atlas safety-review verdict: looks OK."
    assert in_t == 42 and out_t == 137
    assert retries == 0  # happy path → no rate-limit retries
    assert captured["api_key"] == "KEY"
    kw = captured["create_kwargs"]
    assert kw["model"] == aacs._MODEL
    assert kw["max_tokens"] == aacs._MAX_TOKENS
    assert kw["system"] == "SYS"
    assert kw["messages"] == [{"role": "user", "content": "BRIEF"}]


# ---------------------------------------------------------------------------
# run() — orchestration paths
# ---------------------------------------------------------------------------


def _seed_env(monkeypatch: pytest.MonkeyPatch, **overrides) -> None:
    defaults = {
        "ANTHROPIC_API_KEY": "test-key",
        "AGENT_CALLSIGN": "atlas",
        "CHAIN_STEP": "atlas_safety",
        "AGENT_CHAIN_ID": "chain-1",
        "AGENT_TASK_ID": "task-1",
        "AGENT_ATOM_ID": "atom-prior",
        "AGENT_BRIEF": "do the thing",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        monkeypatch.setenv(k, str(v))


def test_run_no_api_key_returns_rc_no_agent_env(monkeypatch: pytest.MonkeyPatch):
    _seed_env(monkeypatch, ANTHROPIC_API_KEY="")
    assert aacs.run() == aacs.RC_NO_AGENT_ENV


def test_run_no_callsign_returns_rc_no_agent_env(monkeypatch: pytest.MonkeyPatch):
    _seed_env(monkeypatch, AGENT_CALLSIGN="")
    assert aacs.run() == aacs.RC_NO_AGENT_ENV


def test_run_no_brief_returns_rc_no_agent_env(monkeypatch: pytest.MonkeyPatch):
    _seed_env(monkeypatch, AGENT_BRIEF="")
    assert aacs.run() == aacs.RC_NO_AGENT_ENV


def test_run_persona_failed_returns_rc_persona_failed(monkeypatch: pytest.MonkeyPatch):
    _seed_env(monkeypatch)
    monkeypatch.setattr(aacs, "fetch_persona", lambda _c: None)
    assert aacs.run() == aacs.RC_PERSONA_FAILED


def test_run_happy_path_writes_attribution_and_publishes_handoff(
    monkeypatch: pytest.MonkeyPatch,
):
    """Mock every subsystem; assert insert_attribution + classify_and_save +
    _publish_handoff all fire with the right args, and exit code is 0."""
    _seed_env(monkeypatch)
    monkeypatch.setattr(aacs, "fetch_persona", lambda _c: ("ATLAS_PROMPT", 500))
    monkeypatch.setattr(aacs, "call_anthropic", lambda *_a, **_kw: ("REPLY", 100, 200, 0))

    insert_calls: list[dict] = []

    def fake_insert(**kwargs):
        insert_calls.append(kwargs)

    monkeypatch.setattr(aacs, "insert_attribution", fake_insert)

    # Mock classify_and_save (lazy import inside run()).
    async def fake_classify(conversation, customer_id, **_kw):
        assert customer_id == 1
        assert conversation[0]["role"] == "user" and conversation[0]["content"] == "do the thing"
        assert conversation[1]["role"] == "assistant" and conversation[1]["content"] == "REPLY"
        return types.SimpleNamespace(atom_ids=["atom-A", "atom-B"])

    fake_ec = types.ModuleType("src.keiracom_system.chat.exit_cycle")
    fake_ec.classify_and_save = fake_classify
    monkeypatch.setitem(sys.modules, "src.keiracom_system.chat.exit_cycle", fake_ec)

    # Mock _publish_handoff (lazy import inside run()).
    handoff_calls: list[dict] = []

    def fake_handoff(*, task_id, atom_id, to_callsign=""):
        handoff_calls.append({"task_id": task_id, "atom_id": atom_id, "to_callsign": to_callsign})
        return True

    fake_acs_mod = types.ModuleType("src.keiracom_system.vault.agent_cold_start")
    fake_acs_mod._publish_handoff = fake_handoff
    fake_acs_mod._connect = lambda: MagicMock()
    monkeypatch.setitem(sys.modules, "src.keiracom_system.vault.agent_cold_start", fake_acs_mod)

    rc = aacs.run()
    assert rc == 0

    assert len(insert_calls) == 1
    row = insert_calls[0]
    assert row["callsign"] == "atlas"
    assert row["chain_id"] == "chain-1"
    assert row["task_id"] == "task-1"
    assert row["chain_step"] == "atlas_safety"
    assert row["input_tokens"] == 100 and row["output_tokens"] == 200
    assert row["cost_usd"] == pytest.approx((100 * 3 + 200 * 15) / 1_000_000)
    assert row["cost_aud"] == pytest.approx(row["cost_usd"] * 1.55)
    assert row["latency_ms"] >= 0.0

    # One handoff per atom — both should fire.
    assert len(handoff_calls) == 2
    assert {c["atom_id"] for c in handoff_calls} == {"atom-A", "atom-B"}
    assert all(c["task_id"] == "task-1" for c in handoff_calls)


def test_run_no_atoms_still_fires_one_empty_handoff(monkeypatch: pytest.MonkeyPatch):
    """If classify_and_save produces no atoms, fire ONE handoff with empty
    atom_id so the chain consumer still advances (no stall)."""
    _seed_env(monkeypatch)
    monkeypatch.setattr(aacs, "fetch_persona", lambda _c: ("PROMPT", 500))
    monkeypatch.setattr(aacs, "call_anthropic", lambda *_a, **_kw: ("REPLY", 0, 0, 0))
    monkeypatch.setattr(aacs, "insert_attribution", lambda **_kw: None)

    async def fake_classify(*_a, **_kw):
        return types.SimpleNamespace(atom_ids=[])

    fake_ec = types.ModuleType("src.keiracom_system.chat.exit_cycle")
    fake_ec.classify_and_save = fake_classify
    monkeypatch.setitem(sys.modules, "src.keiracom_system.chat.exit_cycle", fake_ec)

    handoff_calls: list[dict] = []

    def fake_handoff(*, task_id, atom_id, to_callsign=""):
        handoff_calls.append({"task_id": task_id, "atom_id": atom_id})
        return True

    fake_acs_mod = types.ModuleType("src.keiracom_system.vault.agent_cold_start")
    fake_acs_mod._publish_handoff = fake_handoff
    fake_acs_mod._connect = lambda: MagicMock()
    monkeypatch.setitem(sys.modules, "src.keiracom_system.vault.agent_cold_start", fake_acs_mod)

    assert aacs.run() == 0
    # Exactly one handoff with empty atom_id — chain MUST advance.
    assert len(handoff_calls) == 1
    assert handoff_calls[0]["atom_id"] == ""


# ---------------------------------------------------------------------------
# V1-battery Gate 2 — 429 / 529 retry (Elliot dispatch 2026-05-30 ~11:35 AEST)
# ---------------------------------------------------------------------------


def _install_fake_anthropic_with_statuses(
    monkeypatch: pytest.MonkeyPatch,
    statuses: list[int | None],
    *,
    retry_after_header: str | None = None,
) -> dict:
    """Build a fake anthropic module whose messages.create raises an
    APIStatusError-shaped exception for each non-None status in `statuses`,
    then on the first None entry returns a normal response.

    Returns a dict with attempt counts so the test can assert how many calls
    landed before success / exhaustion.
    """
    state = {"attempts": 0, "captured_sleeps": []}

    class _FakeContent:
        def __init__(self, text):
            self.text = text

    class _FakeUsage:
        input_tokens = 10
        output_tokens = 20

    class _FakeResponse:
        content = [_FakeContent("OK")]
        usage = _FakeUsage()

    class _FakeAnthropicError(Exception):
        pass

    class _FakeAPIError(_FakeAnthropicError):
        pass

    class _FakeAPIStatusError(_FakeAPIError):
        def __init__(self, status_code: int, headers: dict | None = None):
            super().__init__(f"http {status_code}")
            self.status_code = status_code
            self.response = types.SimpleNamespace(status_code=status_code, headers=headers or {})

    class _FakeRateLimitError(_FakeAPIStatusError):
        pass

    class _FakeClient:
        def __init__(self, *, api_key):
            self.messages = self

        def create(self, **_kwargs):
            idx = state["attempts"]
            state["attempts"] += 1
            if idx >= len(statuses) or statuses[idx] is None:
                return _FakeResponse()
            status = statuses[idx]
            headers = {"retry-after": retry_after_header} if retry_after_header else {}
            if status == 429:
                raise _FakeRateLimitError(429, headers)
            raise _FakeAPIStatusError(status, headers)

    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = _FakeClient
    fake_anthropic.AnthropicError = _FakeAnthropicError
    fake_anthropic.APIError = _FakeAPIError
    fake_anthropic.APIStatusError = _FakeAPIStatusError
    fake_anthropic.RateLimitError = _FakeRateLimitError
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    # Patch time.sleep so the retry waits don't actually block the test, and
    # capture the backoff intervals for assertion.
    def _fake_sleep(secs: float) -> None:
        state["captured_sleeps"].append(secs)

    monkeypatch.setattr(aacs.time, "sleep", _fake_sleep)
    return state


def test_call_anthropic_retries_on_429_then_succeeds(monkeypatch: pytest.MonkeyPatch):
    """One 429 then success → returns retries=1, exponential backoff started at 1s."""
    state = _install_fake_anthropic_with_statuses(monkeypatch, [429, None])
    text, in_t, out_t, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")
    assert text == "OK"
    assert in_t == 10 and out_t == 20
    assert retries == 1
    assert state["attempts"] == 2
    # First retry backoff = 1.0s (base * 2**0 = 1.0).
    assert state["captured_sleeps"] == [pytest.approx(1.0)]


def test_call_anthropic_retries_on_529_overloaded(monkeypatch: pytest.MonkeyPatch):
    """529 (overloaded) is in the retriable set — same path as 429."""
    state = _install_fake_anthropic_with_statuses(monkeypatch, [529, 529, None])
    _, _, _, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")
    assert retries == 2
    assert state["attempts"] == 3
    # Exponential: 1s, 2s.
    assert state["captured_sleeps"] == [pytest.approx(1.0), pytest.approx(2.0)]


def test_call_anthropic_respects_retry_after_header(monkeypatch: pytest.MonkeyPatch):
    """Retry-After: 7 → backoff = 7s (overrides computed exponential)."""
    state = _install_fake_anthropic_with_statuses(monkeypatch, [429, None], retry_after_header="7")
    _, _, _, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")
    assert retries == 1
    assert state["captured_sleeps"] == [pytest.approx(7.0)]


def test_call_anthropic_backoff_caps_at_60s(monkeypatch: pytest.MonkeyPatch):
    """Computed backoff cap is 60s — verifies the max-cap guard against runaway exponential."""
    # 4 attempts with statuses [429, 429, 429, None]: backoffs would be 1, 2, 4
    # (last attempt has no sleep). Cap doesn't bite here, but we can validate
    # the cap kicks in by patching the base to a large value and re-running.
    monkeypatch.setattr(aacs, "_RATE_LIMIT_BASE_BACKOFF_S", 100.0)
    state = _install_fake_anthropic_with_statuses(monkeypatch, [429, 429, 429, None])
    _, _, _, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")
    assert retries == 3
    # All 3 backoffs should be capped at 60s.
    assert all(s == pytest.approx(60.0) for s in state["captured_sleeps"])


def test_call_anthropic_exhausts_publishes_ops_failure(monkeypatch: pytest.MonkeyPatch):
    """4 consecutive 429s → publish_rate_limit_exhaust fires; APIStatusError re-raised."""
    state = _install_fake_anthropic_with_statuses(monkeypatch, [429, 429, 429, 429])
    published: list[dict] = []

    def fake_publish(task_id: str, callsign: str, retries: int) -> None:
        published.append({"task_id": task_id, "callsign": callsign, "retries": retries})

    monkeypatch.setattr(aacs, "_publish_rate_limit_exhaust", fake_publish)

    with pytest.raises(Exception) as excinfo:
        aacs.call_anthropic("KEY", "SYS", "BRIEF", task_id="t-x", callsign="atlas")
    assert getattr(excinfo.value, "status_code", None) == 429
    assert state["attempts"] == aacs._RATE_LIMIT_MAX_ATTEMPTS == 4
    assert len(published) == 1
    assert published[0] == {"task_id": "t-x", "callsign": "atlas", "retries": 3}


def test_build_system_param_caches_when_over_threshold():
    """persona_token_count >= 1024 → list-of-blocks with cache_control: ephemeral."""
    result = aacs._build_system_param("PERSONA_TEXT", 1024)
    assert isinstance(result, list)
    assert result == [
        {
            "type": "text",
            "text": "PERSONA_TEXT",
            "cache_control": {"type": "ephemeral"},
        }
    ]
    # 2576-token aiden persona (over threshold) — also caches.
    big = aacs._build_system_param("PERSONA_TEXT", 2576)
    assert isinstance(big, list)
    assert big[0]["cache_control"] == {"type": "ephemeral"}


def test_build_system_param_passthrough_when_under_threshold():
    """persona_token_count < 1024 → plain string (cacheable threshold not met)."""
    # Nova at 104 tokens — way under.
    result = aacs._build_system_param("PERSONA_TEXT", 104)
    assert result == "PERSONA_TEXT"
    # Atlas at 202 tokens — also under.
    result = aacs._build_system_param("ATLAS_TEXT", 202)
    assert result == "ATLAS_TEXT"
    # Edge: 1023 → still under.
    edge = aacs._build_system_param("EDGE", 1023)
    assert edge == "EDGE"


def test_call_anthropic_uses_cached_system_when_persona_over_threshold(
    monkeypatch: pytest.MonkeyPatch,
):
    """End-to-end: call_anthropic with persona_token_count=1024 → SDK call sees
    the list-form system param with cache_control set."""
    captured: dict = {}

    class _FakeContent:
        def __init__(self, text):
            self.text = text

    class _FakeUsage:
        input_tokens = 50
        output_tokens = 10

    class _FakeResponse:
        content = [_FakeContent("OK")]
        usage = _FakeUsage()

    class _FakeClient:
        def __init__(self, *, api_key):
            self.messages = self

        def create(self, **kwargs):
            captured["system"] = kwargs.get("system")
            return _FakeResponse()

    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = _FakeClient
    fake_anthropic.APIStatusError = Exception
    fake_anthropic.RateLimitError = Exception
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    aacs.call_anthropic("KEY", "BIG_PERSONA", "BRIEF", persona_token_count=1500)
    assert isinstance(captured["system"], list)
    assert captured["system"][0]["cache_control"] == {"type": "ephemeral"}

    # And the converse — small persona stays as str.
    captured.clear()
    aacs.call_anthropic("KEY", "SMALL_PERSONA", "BRIEF", persona_token_count=100)
    assert captured["system"] == "SMALL_PERSONA"


def test_call_anthropic_does_not_retry_non_retriable_400(monkeypatch: pytest.MonkeyPatch):
    """400 (bad request) is not in the retriable set — immediate raise, no publish."""
    state = _install_fake_anthropic_with_statuses(monkeypatch, [400])
    published: list[dict] = []
    monkeypatch.setattr(
        aacs,
        "_publish_rate_limit_exhaust",
        lambda **kw: published.append(kw),
    )
    with pytest.raises(Exception) as excinfo:
        aacs.call_anthropic("KEY", "SYS", "BRIEF")
    assert getattr(excinfo.value, "status_code", None) == 400
    assert state["attempts"] == 1
    assert state["captured_sleeps"] == []
    assert published == []  # exhaust path NOT taken
