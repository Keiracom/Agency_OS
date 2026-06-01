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

    text, in_t, out_t, cache_r, cache_w, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")

    assert text == "Atlas safety-review verdict: looks OK."
    # Cache fields absent on the fake usage → getattr defaults to 0.
    assert cache_r == 0 and cache_w == 0
    assert in_t == 42 and out_t == 137
    assert retries == 0  # happy path → no rate-limit retries
    assert captured["api_key"] == "KEY"
    kw = captured["create_kwargs"]
    assert kw["model"] == aacs._MODEL
    assert kw["max_tokens"] == aacs._MAX_TOKENS
    assert kw["system"] == "SYS"
    assert kw["messages"] == [{"role": "user", "content": "BRIEF"}]


def test_call_anthropic_extracts_cache_tokens_from_usage(monkeypatch: pytest.MonkeyPatch):
    """When the Anthropic response.usage exposes cache_creation_input_tokens +
    cache_read_input_tokens, call_anthropic returns them positionally (5th + 4th
    slots of the return tuple). This is the V1-battery cache-attribution fix —
    previously these were dropped, so cache_hit_pct showed 0% in the harness.
    """

    class _FakeUsage:
        input_tokens = 11
        output_tokens = 22
        cache_creation_input_tokens = 2544
        cache_read_input_tokens = 1024

    class _FakeContent:
        def __init__(self, text):
            self.text = text

    class _FakeResponse:
        content = [_FakeContent("ok")]
        usage = _FakeUsage()

    class _FakeClient:
        def __init__(self, *, api_key):
            self.messages = self

        def create(self, **_kwargs):
            return _FakeResponse()

    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = _FakeClient
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    text, in_t, out_t, cache_r, cache_w, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")
    assert text == "ok"
    assert in_t == 11 and out_t == 22
    assert cache_r == 1024
    assert cache_w == 2544
    assert retries == 0


def test_insert_attribution_writes_cache_token_columns():
    """V1-battery fix — cache_read_tokens + cache_write_tokens kwargs land in
    the INSERT params (no longer hardcoded zeros)."""
    conn, cur = _fake_conn()
    aacs.insert_attribution(
        callsign="aiden",
        chain_id="c-cache",
        task_id="t-cache",
        chain_step="aiden_plan",
        input_tokens=11,
        output_tokens=22,
        cost_usd=0.0,
        cost_aud=0.0,
        latency_ms=1.0,
        cache_read_tokens=1024,
        cache_write_tokens=2544,
        conn=conn,
    )
    params = cur.execute.call_args[0][1]
    assert 1024 in params
    assert 2544 in params


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
    monkeypatch.setattr(aacs, "call_anthropic", lambda *_a, **_kw: ("REPLY", 100, 200, 0, 0, 0))

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
    monkeypatch.setattr(aacs, "call_anthropic", lambda *_a, **_kw: ("REPLY", 0, 0, 0, 0, 0))
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
    text, in_t, out_t, cache_r, cache_w, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")
    assert text == "OK"
    assert in_t == 10 and out_t == 20
    assert retries == 1
    assert state["attempts"] == 2
    # First retry backoff = 1.0s (base * 2**0 = 1.0).
    assert state["captured_sleeps"] == [pytest.approx(1.0)]


def test_call_anthropic_retries_on_529_overloaded(monkeypatch: pytest.MonkeyPatch):
    """529 (overloaded) is in the retriable set — same path as 429."""
    state = _install_fake_anthropic_with_statuses(monkeypatch, [529, 529, None])
    _, _, _, _, _, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")
    assert retries == 2
    assert state["attempts"] == 3
    # Exponential: 1s, 2s.
    assert state["captured_sleeps"] == [pytest.approx(1.0), pytest.approx(2.0)]


def test_call_anthropic_respects_retry_after_header(monkeypatch: pytest.MonkeyPatch):
    """Retry-After: 7 → backoff = 7s (overrides computed exponential)."""
    state = _install_fake_anthropic_with_statuses(monkeypatch, [429, None], retry_after_header="7")
    _, _, _, _, _, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")
    assert retries == 1
    assert state["captured_sleeps"] == [pytest.approx(7.0)]


def test_call_anthropic_backoff_caps_at_60s(monkeypatch: pytest.MonkeyPatch):
    """Computed backoff cap is 60s — verifies the max-cap guard against runaway exponential."""
    # 4 attempts with statuses [429, 429, 429, None]: backoffs would be 1, 2, 4
    # (last attempt has no sleep). Cap doesn't bite here, but we can validate
    # the cap kicks in by patching the base to a large value and re-running.
    monkeypatch.setattr(aacs, "_RATE_LIMIT_BASE_BACKOFF_S", 100.0)
    state = _install_fake_anthropic_with_statuses(monkeypatch, [429, 429, 429, None])
    _, _, _, _, _, retries = aacs.call_anthropic("KEY", "SYS", "BRIEF")
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


# ---------------------------------------------------------------------------
# spawn_recall wiring (Gap 1 — fleet_decisions L2 injection)
# ---------------------------------------------------------------------------


def test_build_recall_block_delegates_to_spawn_recall(monkeypatch: pytest.MonkeyPatch):
    """_build_recall_block calls spawn_recall.build_spawn_context_block with
    (task_type, task_brief) and returns its output verbatim."""
    captured: dict = {}

    def fake_build(*, task_type: str, task_brief: str) -> str:
        captured["task_type"] = task_type
        captured["task_brief"] = task_brief
        return "Prior context from memory:\n- [fleet_decisions · ...] excerpt"

    fake_mod = types.ModuleType("src.retrieval.spawn_recall")
    fake_mod.build_spawn_context_block = fake_build
    monkeypatch.setitem(sys.modules, "src.retrieval.spawn_recall", fake_mod)

    result = aacs._build_recall_block(task_type="deliberation", brief="plan the migration")
    assert result.startswith("Prior context from memory:")
    assert captured == {"task_type": "deliberation", "task_brief": "plan the migration"}


def test_build_recall_block_failopen_on_spawn_recall_exception(monkeypatch: pytest.MonkeyPatch):
    """Any exception in build_spawn_context_block (retrieval outage, Weaviate
    down, missing dep) → return "" so the chain hop proceeds without recall.
    A recall outage MUST NEVER block a spawn."""

    def fake_build(*, task_type: str, task_brief: str) -> str:
        raise RuntimeError("Weaviate unreachable")

    fake_mod = types.ModuleType("src.retrieval.spawn_recall")
    fake_mod.build_spawn_context_block = fake_build
    monkeypatch.setitem(sys.modules, "src.retrieval.spawn_recall", fake_mod)

    assert aacs._build_recall_block(task_type="build", brief="anything") == ""


def test_build_recall_block_failopen_on_import_error(monkeypatch: pytest.MonkeyPatch):
    """spawn_recall import failure (module missing in test env) → return ""."""
    monkeypatch.setitem(sys.modules, "src.retrieval.spawn_recall", None)
    # Setting to None makes the import attempt raise ImportError.
    assert aacs._build_recall_block(task_type="build", brief="anything") == ""


def test_build_messages_param_small_recall_skips_cache_control():
    """Non-empty recall_block under the 1,024-token Anthropic minimum-cacheable-
    prefix floor (estimated at ~4 chars/token) → list-of-blocks user content with
    NO cache_control breakpoint. This is the production case today: spawn_recall
    KEI-55-caps the block at 500 tokens (~2,000 chars), well below the floor —
    setting cache_control would be a no-op the SDK silently ignores."""
    result = aacs._build_messages_param("the brief", "RECALL_TEXT")
    assert len(result) == 1
    assert result[0]["role"] == "user"
    content = result[0]["content"]
    assert isinstance(content, list)
    # Recall block present as a structured text block — but WITHOUT cache_control.
    assert content[0] == {"type": "text", "text": "RECALL_TEXT"}
    assert "cache_control" not in content[0]
    assert content[1] == {"type": "text", "text": "the brief"}


def test_build_messages_param_over_floor_recall_gets_cache_control():
    """When recall_block exceeds the 1,024-token cacheable-prefix floor (≥4,096
    chars at ~4 chars/token) the cache_control: ephemeral breakpoint is applied.
    This guards the forward-compat case where the KEI-55 budget ceiling grows
    past 1,024 tokens — the code switches caching on without further changes."""
    big_recall = "x" * (aacs._PROMPT_CACHE_MIN_TOKENS * 4)  # exactly at the floor
    result = aacs._build_messages_param("the brief", big_recall)
    content = result[0]["content"]
    assert content[0]["text"] == big_recall
    assert content[0]["cache_control"] == {"type": "ephemeral"}
    # Brief block is the second block, still uncached.
    assert content[1] == {"type": "text", "text": "the brief"}
    # And one char under the floor → no breakpoint (sanity check on the boundary).
    edge = "x" * (aacs._PROMPT_CACHE_MIN_TOKENS * 4 - 1)
    edge_content = aacs._build_messages_param("the brief", edge)[0]["content"]
    assert "cache_control" not in edge_content[0]


def test_build_messages_param_without_recall_returns_plain_string():
    """Empty recall_block → plain string content (no wire-format change vs the
    pre-recall baseline; preserves byte-identical legacy behaviour)."""
    assert aacs._build_messages_param("the brief", "") == [{"role": "user", "content": "the brief"}]


def test_call_anthropic_threads_recall_block_into_messages(monkeypatch: pytest.MonkeyPatch):
    """End-to-end: call_anthropic(recall_block='...') → SDK call sees the
    structured user content with the recall block as a separate text block.
    Under-floor recall → no cache_control on the block (production case today)."""
    captured: dict = {}

    class _FakeContent:
        def __init__(self, text):
            self.text = text

    class _FakeUsage:
        input_tokens = 5
        output_tokens = 3
        cache_creation_input_tokens = 0
        cache_read_input_tokens = 0

    class _FakeResponse:
        content = [_FakeContent("OK")]
        usage = _FakeUsage()

    class _FakeClient:
        def __init__(self, *, api_key):
            self.messages = self

        def create(self, **kwargs):
            captured["messages"] = kwargs.get("messages")
            return _FakeResponse()

    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = _FakeClient
    fake_anthropic.APIStatusError = Exception
    fake_anthropic.RateLimitError = Exception
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    aacs.call_anthropic("KEY", "SYS", "BRIEF", recall_block="RECALL_TEXT")
    msgs = captured["messages"]
    assert isinstance(msgs[0]["content"], list)
    assert msgs[0]["content"][0]["text"] == "RECALL_TEXT"
    assert "cache_control" not in msgs[0]["content"][0]
    assert msgs[0]["content"][1]["text"] == "BRIEF"


def test_call_anthropic_no_recall_block_preserves_plain_messages(monkeypatch: pytest.MonkeyPatch):
    """Backwards-compat: no recall_block (or empty string) → plain string content
    matching the pre-recall behaviour the rest of the test suite asserts on."""
    captured: dict = {}

    class _FakeUsage:
        input_tokens = 1
        output_tokens = 1

    class _FakeResponse:
        content = [types.SimpleNamespace(text="OK")]
        usage = _FakeUsage()

    class _FakeClient:
        def __init__(self, *, api_key):
            self.messages = self

        def create(self, **kwargs):
            captured["messages"] = kwargs.get("messages")
            return _FakeResponse()

    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = _FakeClient
    fake_anthropic.APIStatusError = Exception
    fake_anthropic.RateLimitError = Exception
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    aacs.call_anthropic("KEY", "SYS", "BRIEF")
    assert captured["messages"] == [{"role": "user", "content": "BRIEF"}]


def test_run_builds_recall_block_and_passes_to_call_anthropic(monkeypatch: pytest.MonkeyPatch):
    """The whole reason for this PR: run() must call _build_recall_block with the
    chain_step → task_type mapping AND thread the resulting recall_block through
    to call_anthropic. Without this wiring, fleet_decisions is never queried and
    cache_hit_pct stays at 0 because there is nothing shared to cache between
    cold and warm runs.
    """
    _seed_env(monkeypatch, CHAIN_STEP="aiden_plan")
    monkeypatch.setattr(aacs, "fetch_persona", lambda _c: ("PROMPT", 500))

    # Build a recall block keyed on (task_type, brief).
    recall_calls: list[dict] = []

    def fake_build_recall(*, task_type: str, brief: str) -> str:
        recall_calls.append({"task_type": task_type, "brief": brief})
        return "RECALL_FROM_FLEET_DECISIONS"

    monkeypatch.setattr(aacs, "_build_recall_block", fake_build_recall)

    # Capture what call_anthropic received as recall_block.
    capture: dict = {}

    def fake_call(api_key, persona, brief, **kwargs):
        capture["recall_block"] = kwargs.get("recall_block")
        capture["callsign"] = kwargs.get("callsign")
        return ("REPLY", 10, 20, 0, 0, 0)

    monkeypatch.setattr(aacs, "call_anthropic", fake_call)
    monkeypatch.setattr(aacs, "insert_attribution", lambda **_kw: None)

    # Mock classify_and_save + handoff so run() reaches return 0.
    async def fake_classify(*_a, **_kw):
        return types.SimpleNamespace(atom_ids=[])

    fake_ec = types.ModuleType("src.keiracom_system.chat.exit_cycle")
    fake_ec.classify_and_save = fake_classify
    monkeypatch.setitem(sys.modules, "src.keiracom_system.chat.exit_cycle", fake_ec)

    fake_acs_mod = types.ModuleType("src.keiracom_system.vault.agent_cold_start")
    fake_acs_mod._publish_handoff = lambda **_kw: True
    fake_acs_mod._connect = lambda: MagicMock()
    monkeypatch.setitem(sys.modules, "src.keiracom_system.vault.agent_cold_start", fake_acs_mod)

    assert aacs.run() == 0
    # _build_recall_block called exactly once with the chain_step's mapped
    # task_type ("aiden_plan" → "deliberation") and the env's AGENT_BRIEF.
    assert recall_calls == [{"task_type": "deliberation", "brief": "do the thing"}]
    # And the resulting block was threaded into call_anthropic.
    assert capture["recall_block"] == "RECALL_FROM_FLEET_DECISIONS"


def test_resolve_task_type_maps_known_steps_and_falls_back_to_unknown():
    """Single source of truth for chain_step → task_type. Shared by run()
    (recall query) AND insert_attribution (DB write) — both callers MUST see
    the same value or attribution + recall drift (Max review HOLD #1383)."""
    assert aacs._resolve_task_type("aiden_plan") == "deliberation"
    assert aacs._resolve_task_type("max_challenge") == "deliberation"
    assert aacs._resolve_task_type("nova_build") == "build"
    assert aacs._resolve_task_type("orion_spec") == "pr_review"
    assert aacs._resolve_task_type("atlas_safety") == "pr_review"
    # Absent / unknown → "unknown" (matches DB CHECK enum and the prior
    # insert_attribution fallback). The recall path now also gets "unknown"
    # instead of the old "build" — consistent across both callers.
    assert aacs._resolve_task_type("") == "unknown"
    assert aacs._resolve_task_type("nonexistent_step") == "unknown"


def test_run_absent_chain_step_uses_unknown_for_recall_and_attribution(
    monkeypatch: pytest.MonkeyPatch,
):
    """When CHAIN_STEP is absent, BOTH _build_recall_block and insert_attribution
    must see task_type='unknown'. Previously run() defaulted recall to 'build'
    while insert_attribution defaulted to 'unknown' — Max review HOLD #1383."""
    _seed_env(monkeypatch, CHAIN_STEP="")
    monkeypatch.setattr(aacs, "fetch_persona", lambda _c: ("PROMPT", 500))

    recall_task_type: dict = {}

    def fake_build_recall(*, task_type: str, brief: str) -> str:
        recall_task_type["value"] = task_type
        return ""

    monkeypatch.setattr(aacs, "_build_recall_block", fake_build_recall)
    monkeypatch.setattr(aacs, "call_anthropic", lambda *_a, **_kw: ("OK", 0, 0, 0, 0, 0))

    insert_calls: list[dict] = []
    monkeypatch.setattr(aacs, "insert_attribution", lambda **kw: insert_calls.append(kw))

    async def fake_classify(*_a, **_kw):
        return types.SimpleNamespace(atom_ids=[])

    fake_ec = types.ModuleType("src.keiracom_system.chat.exit_cycle")
    fake_ec.classify_and_save = fake_classify
    monkeypatch.setitem(sys.modules, "src.keiracom_system.chat.exit_cycle", fake_ec)

    fake_acs_mod = types.ModuleType("src.keiracom_system.vault.agent_cold_start")
    fake_acs_mod._publish_handoff = lambda **_kw: True
    fake_acs_mod._connect = lambda: MagicMock()
    monkeypatch.setitem(sys.modules, "src.keiracom_system.vault.agent_cold_start", fake_acs_mod)

    assert aacs.run() == 0
    assert recall_task_type["value"] == "unknown"
    # insert_attribution receives chain_step="" — but _resolve_task_type
    # inside it also yields "unknown", so DB sees the same value as recall.
    assert insert_calls[0]["chain_step"] == "?"  # absent CHAIN_STEP → "?" placeholder
    # Sanity: confirm the resolver agrees on the actual chain_step value
    # passed to insert_attribution (the "?" placeholder).
    assert aacs._resolve_task_type(insert_calls[0]["chain_step"]) == "unknown"


def test_run_empty_recall_block_still_proceeds(monkeypatch: pytest.MonkeyPatch):
    """Fail-open path: when _build_recall_block returns "" (retrieval outage,
    empty corpus), run() still calls call_anthropic with recall_block="" and
    completes normally. A recall outage MUST NEVER block the chain hop."""
    _seed_env(monkeypatch, CHAIN_STEP="nova_build")
    monkeypatch.setattr(aacs, "fetch_persona", lambda _c: ("PROMPT", 500))
    monkeypatch.setattr(aacs, "_build_recall_block", lambda **_kw: "")

    capture: dict = {}

    def fake_call(api_key, persona, brief, **kwargs):
        capture["recall_block"] = kwargs.get("recall_block")
        return ("REPLY", 10, 20, 0, 0, 0)

    monkeypatch.setattr(aacs, "call_anthropic", fake_call)
    monkeypatch.setattr(aacs, "insert_attribution", lambda **_kw: None)

    async def fake_classify(*_a, **_kw):
        return types.SimpleNamespace(atom_ids=[])

    fake_ec = types.ModuleType("src.keiracom_system.chat.exit_cycle")
    fake_ec.classify_and_save = fake_classify
    monkeypatch.setitem(sys.modules, "src.keiracom_system.chat.exit_cycle", fake_ec)

    fake_acs_mod = types.ModuleType("src.keiracom_system.vault.agent_cold_start")
    fake_acs_mod._publish_handoff = lambda **_kw: True
    fake_acs_mod._connect = lambda: MagicMock()
    monkeypatch.setitem(sys.modules, "src.keiracom_system.vault.agent_cold_start", fake_acs_mod)

    assert aacs.run() == 0
    assert capture["recall_block"] == ""


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
