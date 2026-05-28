"""Tests for scripts/ceo_capture_listener.py (Agency_OS-yku8).

Exercises the classification pipeline, the rate-limit gate, the injection-safe
spawn-payload builder, and the end-to-end handle_event decision — all without
slack_sdk / google.genai / redis installed (the listener lazy-imports those, so
the logic layer is importable + testable in hermetic CI).

The dispatch's smoke ("post a test message in #ceo, verify spawn triggered or
correctly skipped") is realised deterministically via handle_event on synthetic
#ceo events — no live Slack post (Scout must not post to the Dave-facing #ceo).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "ceo_capture_listener.py"


def _load():
    spec = importlib.util.spec_from_file_location("_ceo_capture_listener", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load()
CEO = m.CEO_CHANNEL


def _event(text, *, bot_id=None, subtype=None, channel=CEO, etype="message"):
    e = {"type": etype, "channel": channel, "text": text}
    if bot_id:
        e["bot_id"] = bot_id
    if subtype:
        e["subtype"] = subtype
    return e


# ─── Stage 1 heuristic ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "This is now ratified — go ahead.",
        "Decision: we will use Hindsight as the engine.",
        "the architecture is a layered system prompt design",
        "The rule is: never do X.",
    ],
)
def test_stage1_passes_on_signals(text):
    assert m.stage1_heuristic(text) is True


def test_stage1_skips_plain_chatter():
    assert m.stage1_heuristic("thanks, looks good, talk later") is False
    assert m.stage1_heuristic("") is False


# ─── classify pipeline (stage2 mocked) ────────────────────────────────────────


def test_classify_skips_stage2_when_stage1_fails(monkeypatch):
    monkeypatch.setattr(m, "stage2_classify", lambda t: pytest.fail("stage2 must not run"))
    should, label, conf = m.classify("just chatter, nothing here")
    assert should is False and label == "STAGE1_SKIP" and conf == 0.0


def test_classify_spawns_on_high_confidence_decision(monkeypatch):
    monkeypatch.setattr(m, "stage2_classify", lambda t: ("DECISION", 0.91))
    should, label, conf = m.classify("Decision: we will use X. ratified.")
    assert should is True and label == "DECISION"


def test_classify_skips_noise_even_if_confident(monkeypatch):
    monkeypatch.setattr(m, "stage2_classify", lambda t: ("NOISE", 0.99))
    should, _, _ = m.classify("the rule is be nice")
    assert should is False


def test_classify_skips_below_threshold(monkeypatch):
    monkeypatch.setattr(m, "stage2_classify", lambda t: ("DECISION", 0.70))  # == threshold, not >
    should, _, _ = m.classify("Decision: maybe we use X")
    assert should is False


# ─── _parse_classification ────────────────────────────────────────────────────


def test_parse_handles_code_fenced_json():
    label, conf = m._parse_classification('```json\n{"label":"ARCHITECTURE","confidence":0.8}\n```')
    assert label == "ARCHITECTURE" and conf == pytest.approx(0.8)


def test_parse_clamps_and_defaults_invalid_label():
    label, conf = m._parse_classification('{"label":"WAT","confidence":1.7}')
    assert label == "NOISE" and conf == 1.0


# ─── rate limit ───────────────────────────────────────────────────────────────


def test_rate_limit_disabled_when_no_store(monkeypatch):
    monkeypatch.setattr(m, "_redis_client", lambda: None)
    assert m.within_rate_limit() is True


def test_rate_limit_allows_under_cap(monkeypatch):
    class _C:
        def get(self, k):
            return b"2"

    monkeypatch.setattr(m, "_redis_client", lambda: _C())
    assert m.within_rate_limit() is True


def test_rate_limit_blocks_at_cap(monkeypatch):
    class _C:
        def get(self, k):
            return str(m.MAX_SPAWNS_PER_HOUR).encode()

    monkeypatch.setattr(m, "_redis_client", lambda: _C())
    assert m.within_rate_limit() is False


def test_rate_limit_fails_closed_on_store_error(monkeypatch):
    def _boom():
        raise RuntimeError("redis down")

    monkeypatch.setattr(m, "_redis_client", _boom)
    assert m.within_rate_limit() is False  # protect the cost cap


# ─── spawn payload (injection safety) ─────────────────────────────────────────


def test_build_spawn_request_shape():
    p = m.build_spawn_request("the rule is X")
    assert p["backend"] == "tmux"
    assert p["key"].startswith("ceo-capture-")
    assert p["spawn_kwargs"]["callsign"] == "john"
    assert "the rule is X" in p["spawn_kwargs"]["brief"]


def test_build_spawn_request_is_injection_safe():
    """Untrusted message with shell metacharacters must live ONLY in env, never in
    the command string."""
    nasty = 'ratified"; rm -rf / #'
    p = m.build_spawn_request(nasty)
    sk = p["spawn_kwargs"]
    assert sk["env"]["CEO_CAPTURE_MESSAGE"] == nasty  # carried via env
    assert nasty not in sk["command"]  # NOT interpolated into the shell command
    assert "rm -rf" not in sk["command"]


# ─── post_spawn (fail-open) ───────────────────────────────────────────────────


def test_post_spawn_true_on_2xx(monkeypatch):
    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(m.urllib.request, "urlopen", lambda *a, **k: _Resp())
    assert m.post_spawn({"key": "k"}) is True


def test_post_spawn_fails_open_when_dispatcher_down(monkeypatch):
    def _boom(*a, **k):
        raise m.urllib.error.URLError("connection refused")

    monkeypatch.setattr(m.urllib.request, "urlopen", _boom)
    assert m.post_spawn({"key": "k"}) is False  # logged, not raised


# ─── is_capture_candidate ─────────────────────────────────────────────────────


def test_candidate_rejects_bot_subtype_wrongchannel_empty():
    assert m.is_capture_candidate(_event("hi", bot_id="B123")) is False
    assert m.is_capture_candidate(_event("hi", subtype="message_changed")) is False
    assert m.is_capture_candidate(_event("hi", channel="C_OTHER")) is False
    assert m.is_capture_candidate(_event("   ")) is False
    assert m.is_capture_candidate(_event("real human message")) is True


# ─── handle_event — the deterministic smoke ───────────────────────────────────


def test_smoke_capture_worthy_message_spawns(monkeypatch):
    monkeypatch.setattr(m, "stage2_classify", lambda t: ("DECISION", 0.92))
    monkeypatch.setattr(m, "within_rate_limit", lambda: True)
    spawned = {}
    monkeypatch.setattr(m, "post_spawn", lambda payload: spawned.update(payload) or True)
    monkeypatch.setattr(m, "record_spawn", lambda: None)
    action = m.handle_event(_event("Decision: we will use Hindsight. This is ratified."))
    assert action == "spawned"
    assert spawned["spawn_kwargs"]["callsign"] == "john"


def test_smoke_noise_message_skips_without_gemini(monkeypatch):
    # No stage-1 signal → stage2 never runs → skip (free path).
    monkeypatch.setattr(m, "stage2_classify", lambda t: pytest.fail("stage2 must not run"))
    action = m.handle_event(_event("thanks team, great work today"))
    assert action == "skip_stage1_skip"


def test_handle_event_skips_when_rate_limited(monkeypatch):
    monkeypatch.setattr(m, "stage2_classify", lambda t: ("DECISION", 0.95))
    monkeypatch.setattr(m, "within_rate_limit", lambda: False)
    monkeypatch.setattr(m, "post_spawn", lambda p: pytest.fail("must not spawn when rate-limited"))
    action = m.handle_event(_event("Decision: ratified, we will use X"))
    assert action == "skip_rate_limit"


def test_handle_event_skips_bot_message(monkeypatch):
    monkeypatch.setattr(m, "stage2_classify", lambda t: pytest.fail("must not classify a bot msg"))
    action = m.handle_event(_event("Decision: ratified", bot_id="B0B2W7VL7T4"))
    assert action == "skip_not_candidate"
