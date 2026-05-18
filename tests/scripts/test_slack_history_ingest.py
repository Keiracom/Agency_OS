"""Tests for slack_history_ingest — KEI-201 noise filter + classifier + builder.

Parser-only tests; no live Slack or Weaviate dependency. Covers:
  - 7 message_type patterns each classify correctly
  - Noise filter drops [READY:] heartbeats + fleet-status mirrors
  - slack_to_message returns None for noise, populated SlackMessage otherwise
  - build_object schema shape
  - Deterministic UUID per (channel, ts)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "slack_history_ingest.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("slack_history_ingest", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["slack_history_ingest"] = m
    spec.loader.exec_module(m)
    return m


# ─── Noise filter ────────────────────────────────────────────────────────────


def test_noise_filter_drops_ready_heartbeat(mod):
    assert mod.is_noise("[READY:scout]")
    assert mod.is_noise("[READY:max] ")
    assert mod.is_noise("[ready:atlas]")  # case-insensitive


def test_noise_filter_drops_fleet_status(mod):
    assert mod.is_noise("[FLEET-STATUS:supervisor] 6/6 agents alive")
    assert mod.is_noise("[SUPERVISOR] fleet cycle 5min complete")


def test_noise_filter_drops_empty(mod):
    assert mod.is_noise("")
    assert mod.is_noise("   \n\t  ")


def test_noise_filter_keeps_real_content(mod):
    assert not mod.is_noise("Dave directive: ship the PR")
    assert not mod.is_noise("[CONCUR:max] approve PR #993")
    assert not mod.is_noise("Building KEI-201 now")


def test_noise_filter_drops_bare_callsign_ping(mod):
    """Bare-bracket pings like '[ATLAS]' alone are pure protocol noise."""
    assert mod.is_noise("[ATLAS]")
    assert mod.is_noise("[scout]")
    assert mod.is_noise("  [ORION]  ")
    assert mod.is_noise("[NOVA]")


def test_noise_filter_keeps_callsign_with_payload(mod):
    """Bracketed callsign with content after MUST be kept (it's a real ping with body)."""
    assert not mod.is_noise("[ATLAS] please claim KEI-99")
    assert not mod.is_noise("[SCOUT] dispatch received")


def test_noise_filter_drops_vercel_ratelimit(mod):
    assert mod.is_noise("Vercel rate limit hit on deploy")
    assert mod.is_noise("429 too many requests from vercel API")
    assert mod.is_noise("VERCEL: rate-limit retry after 60s")


def test_noise_filter_keeps_vercel_non_ratelimit(mod):
    """Vercel mentioned in non-ratelimit context (e.g. deploy success) must NOT be noise."""
    assert not mod.is_noise("Vercel deploy succeeded for PR #1024")
    assert not mod.is_noise("checking vercel logs for the build failure")


def test_noise_filter_regex_precedence_supervisor_midstring(mod):
    """S5850 regression: `[SUPERVISOR] fleet` mid-string must NOT be flagged as noise.

    Pre-fix regex `^\\s*\\[FLEET...\\]|\\[SUPERVISOR\\]\\s+(fleet|cycle)` had `|`
    splitting the anchor — second branch matched anywhere. With `.match()` that's
    latent (anchored at pos 0), but the explicit non-capturing group documents intent
    and is safe under `.search()` if ever swapped.
    """
    assert not mod.is_noise("Dave said [SUPERVISOR] fleet status looks good")
    assert not mod.is_noise("we should review [SUPERVISOR] cycle metrics")
    assert not mod.is_noise("note: [FLEET-STATUS:supervisor] was mentioned")


# ─── Message-type classifier ─────────────────────────────────────────────────


def test_classify_ceo_directive(mod):
    assert mod.classify_message("[CEO] AUTHORIZED — ship it") == "ceo_directive"
    assert mod.classify_message("Dave directive ts 1778626300") == "ceo_directive"
    assert mod.classify_message("[DIRECTIVE 244] proceed") == "ceo_directive"


def test_classify_agent_escalation(mod):
    assert mod.classify_message("[BLOCKED] need Dave for top-up") == "agent_escalation"
    assert mod.classify_message("BLOCKER: cannot proceed without auth") == "agent_escalation"
    assert mod.classify_message("[ESCALATE] need elliot for review") == "agent_escalation"


def test_classify_architectural_decision(mod):
    assert mod.classify_message("[ARCHITECTURE] use postgres not mongo") == "architectural_decision"
    assert mod.classify_message("3-way concur on design") == "architectural_decision"
    assert mod.classify_message("3-way ratified") == "architectural_decision"


def test_classify_supervisor_observation(mod):
    assert (
        mod.classify_message("[SUPERVISOR] auto-claimed KEI-191 for max")
        == "supervisor_observation"
    )
    assert mod.classify_message("DRIFT-RELEASE: KEI-201 back to queue") == "supervisor_observation"
    assert mod.classify_message("fleet supervisor cycle complete") == "supervisor_observation"


def test_classify_completion_report(mod):
    assert mod.classify_message("[SHIPPED:scout] PR #997 merged") == "completion_report"
    assert mod.classify_message("[MERGED:elliot] at f6bb8d2f") == "completion_report"
    assert mod.classify_message("PR #942 merged into main") == "completion_report"


def test_classify_debug_session(mod):
    assert mod.classify_message("[DIAGNOSIS:scout] root cause found") == "debug_session"
    assert mod.classify_message("verbatim grep returned 0 matches") == "debug_session"
    assert mod.classify_message("empirical probe confirms hypothesis") == "debug_session"


def test_classify_governance_event(mod):
    assert mod.classify_message("[CONCUR:aiden] APPROVE PR #993") == "governance_event"
    assert mod.classify_message("[REVIEW:HOLD:scout] Sonar 7") == "governance_event"
    assert mod.classify_message("CONCUR-LOCK on prior HOLD") == "governance_event"


def test_classify_fallback(mod):
    """Plain chatter that matches none of the patterns gets the fallback type."""
    assert mod.classify_message("just doing some thinking out loud") == "agent_chatter"
    assert mod.classify_message("random thought") == "agent_chatter"


# ─── slack_to_message conversion ─────────────────────────────────────────────


def test_slack_to_message_drops_noise(mod):
    raw = {"text": "[READY:scout]", "ts": "1779065531.123", "user": "U001"}
    assert mod.slack_to_message("execution", raw) is None


def test_slack_to_message_populates_fields(mod):
    raw = {
        "text": "[SHIPPED:scout] PR #997 merged",
        "ts": "1779065531.123",
        "user": "U042",
        "thread_ts": "1779065530.000",
    }
    msg = mod.slack_to_message("execution", raw)
    assert msg is not None
    assert msg.channel == "execution"
    assert msg.ts == "1779065531.123"
    assert msg.user == "U042"
    assert msg.thread_ts == "1779065530.000"
    assert msg.message_type == "completion_report"


def test_slack_to_message_handles_missing_ts(mod):
    raw = {"text": "real content", "user": "U001"}  # no ts
    assert mod.slack_to_message("ceo", raw) is None


def test_slack_to_message_handles_missing_user(mod):
    raw = {"text": "real content", "ts": "1779065531.123", "bot_id": "B001"}
    msg = mod.slack_to_message("ceo", raw)
    assert msg is not None
    assert msg.user == "B001"  # falls back to bot_id


# ─── build_object + deterministic id ─────────────────────────────────────────


def test_build_object_schema_shape(mod):
    msg = mod.SlackMessage(
        channel="ceo",
        ts="1779065531.123456",
        text="Dave directive",
        user="U-DAVE",
        thread_ts="",
        message_type="ceo_directive",
    )
    obj = mod.build_object(msg)
    assert obj["class"] == "Slack_history"
    assert "id" in obj
    props = obj["properties"]
    assert props["raw_text"] == "Dave directive"
    assert props["channel"] == "ceo"
    assert props["message_type"] == "ceo_directive"
    assert props["agent"] == "U-DAVE"
    assert props["kei"] == "KEI-201"
    assert props["ts"] == "1779065531.123456"
    # created_at is parsed from ts → ISO 8601
    assert props["created_at"].startswith("2026-")


def test_deterministic_id_stable_across_calls(mod):
    msg = mod.SlackMessage(
        channel="ceo",
        ts="1779065531.123",
        text="any",
        user="U",
        thread_ts="",
        message_type="ceo_directive",
    )
    assert msg.deterministic_id() == msg.deterministic_id()


def test_deterministic_id_differs_across_channels(mod):
    base = {
        "ts": "1779065531.123",
        "text": "x",
        "user": "U",
        "thread_ts": "",
        "message_type": "ceo_directive",
    }
    a = mod.SlackMessage(channel="ceo", **base).deterministic_id()
    b = mod.SlackMessage(channel="execution", **base).deterministic_id()
    assert a != b


def test_deterministic_id_differs_across_ts(mod):
    base = {
        "channel": "ceo",
        "text": "x",
        "user": "U",
        "thread_ts": "",
        "message_type": "ceo_directive",
    }
    a = mod.SlackMessage(ts="1779065531.123", **base).deterministic_id()
    b = mod.SlackMessage(ts="1779065531.124", **base).deterministic_id()
    assert a != b


# ─── Schema ─────────────────────────────────────────────────────────────────


def test_schema_uses_text2vec_google_ai_studio(mod):
    """Dave Option A (KEI-196 swap) + KEI-201 empirical fix:
    vectorizer=text2vec-google, AI Studio endpoint (no projectId), modelId
    gemini-embedding-001 (NOT text-embedding-004 — that's the Vertex name
    and 404s on AI Studio v1beta).
    """
    assert mod.CORPUS_SCHEMA["vectorizer"] == "text2vec-google"
    mc = mod.CORPUS_SCHEMA["moduleConfig"]["text2vec-google"]
    assert mc["apiEndpoint"] == "generativelanguage.googleapis.com"
    assert mc["modelId"] == "gemini-embedding-001"
    assert mc["vectorizeClassName"] is False


def test_schema_has_required_properties(mod):
    props = {p["name"] for p in mod.CORPUS_SCHEMA["properties"]}
    # 5 standard + 4 corpus-specific
    assert {"raw_text", "environment_hash", "created_at", "agent", "kei"} <= props
    assert {"channel", "message_type", "ts", "thread_ts"} <= props
