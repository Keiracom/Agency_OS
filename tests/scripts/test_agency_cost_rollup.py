"""Tests for agency_cost_rollup.py — daily 3-provider cost rollup.

Covers: cost_for_usage pricing math; callsign_from_project_dir mapping;
load_anthropic_session_cost JSONL walk + last-N-hours filter; load_openai_cost
filter; load_vultr_cost auth + parse paths; aggregate per-provider +
per-callsign; format_ceo_post plain-English shape; post_to_ceo subprocess
wrapper; write_daily_log JSONL append.

bd: Agency_OS-j12p
"""

from __future__ import annotations

import importlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

_mod = importlib.import_module("agency_cost_rollup")


# ---------- pricing math ----------


def test_cost_for_usage_opus_simple_input_output():
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    cost = _mod.cost_for_usage(usage, "claude-opus-4-7")
    # 1M input × $15 + 1M output × $75 = $90.00
    assert abs(cost - 90.0) < 1e-6


def test_cost_for_usage_includes_cache_read():
    usage = {"cache_read_input_tokens": 1_000_000}
    cost = _mod.cost_for_usage(usage, "claude-opus-4-7")
    # 1M cache_read × $1.50 = $1.50
    assert abs(cost - 1.50) < 1e-6


def test_cost_for_usage_includes_cache_write_ephemeral_5m_and_1h():
    usage = {
        "cache_creation": {
            "ephemeral_5m_input_tokens": 1_000_000,
            "ephemeral_1h_input_tokens": 1_000_000,
        }
    }
    cost = _mod.cost_for_usage(usage, "claude-opus-4-7")
    # 5m: $18.75 + 1h: $30 = $48.75
    assert abs(cost - 48.75) < 1e-6


def test_cost_for_usage_falls_back_to_legacy_cache_creation_input_tokens():
    usage = {"cache_creation_input_tokens": 1_000_000}
    cost = _mod.cost_for_usage(usage, "claude-opus-4-7")
    # Legacy fallback treats as 5m: $18.75
    assert abs(cost - 18.75) < 1e-6


def test_cost_for_usage_strips_one_million_context_suffix():
    """claude-opus-4-7[1m] resolves to base claude-opus-4-7 pricing."""
    cost = _mod.cost_for_usage({"input_tokens": 1_000_000}, "claude-opus-4-7[1m]")
    assert abs(cost - 15.0) < 1e-6


def test_cost_for_usage_unknown_model_returns_zero():
    cost = _mod.cost_for_usage({"input_tokens": 1_000_000}, "claude-pluto-9-9")
    assert cost == 0.0


def test_cost_for_usage_sonnet_pricing():
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    cost = _mod.cost_for_usage(usage, "claude-sonnet-4-6")
    # 1M × $3 + 1M × $15 = $18
    assert abs(cost - 18.0) < 1e-6


def test_cost_for_usage_haiku_pricing():
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    cost = _mod.cost_for_usage(usage, "claude-haiku-4-5")
    # 1M × $1 + 1M × $5 = $6
    assert abs(cost - 6.0) < 1e-6


# ---------- callsign mapping ----------


def test_callsign_from_project_dir_named_clones():
    assert _mod.callsign_from_project_dir("-home-elliotbot-clawd-Agency-OS-atlas") == "atlas"
    assert _mod.callsign_from_project_dir("-home-elliotbot-clawd-Agency-OS-orion") == "orion"
    assert _mod.callsign_from_project_dir("-home-elliotbot-clawd-Agency-OS-nova") == "nova"


def test_callsign_from_project_dir_main_worktree_is_elliot():
    assert _mod.callsign_from_project_dir("-home-elliotbot-clawd-Agency-OS") == "elliot"


# ---------- anthropic session jsonl walk ----------


def test_load_anthropic_session_cost_last_24h(tmp_path: Path):
    root = tmp_path / "projects"
    cs_dir = root / "-home-elliotbot-clawd-Agency-OS-atlas"
    cs_dir.mkdir(parents=True)
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    old_iso = (datetime.now(UTC) - timedelta(hours=48)).isoformat().replace("+00:00", "Z")
    session_path = cs_dir / "s1.jsonl"
    session_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "timestamp": now_iso,
                        "message": {
                            "model": "claude-opus-4-7",
                            "usage": {"input_tokens": 1_000_000},
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "timestamp": now_iso,
                        "message": {
                            "model": "claude-sonnet-4-6",
                            "usage": {"output_tokens": 1_000_000},
                        },
                    }
                ),
                # outside window
                json.dumps(
                    {
                        "type": "assistant",
                        "timestamp": old_iso,
                        "message": {
                            "model": "claude-opus-4-7",
                            "usage": {"input_tokens": 1_000_000},
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    out = _mod.load_anthropic_session_cost(hours=24, projects_root=root)
    # atlas: $15 (Opus 1M input) + $15 (Sonnet 1M output) = $30
    assert "atlas" in out
    assert abs(out["atlas"] - 30.0) < 1e-3


def test_load_anthropic_session_cost_skips_old_files(tmp_path: Path):
    root = tmp_path / "projects"
    cs_dir = root / "-home-elliotbot-clawd-Agency-OS-atlas"
    cs_dir.mkdir(parents=True)
    session = cs_dir / "old.jsonl"
    session.write_text("{}", encoding="utf-8")
    # Backdate the mtime
    import os

    old_ts = (datetime.now(UTC) - timedelta(hours=72)).timestamp()
    os.utime(session, (old_ts, old_ts))
    out = _mod.load_anthropic_session_cost(hours=24, projects_root=root)
    assert out == {}


# ---------- openai cost log ----------


def test_load_openai_cost_filters_by_window(tmp_path: Path):
    log = tmp_path / "openai.jsonl"
    now_ts = datetime.now(UTC).isoformat()
    old_ts = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    log.write_text(
        "\n".join(
            [
                json.dumps({"ts": now_ts, "callsign": "atlas", "estimated_cost_usd": 0.10}),
                json.dumps({"ts": now_ts, "callsign": "orion", "estimated_cost_usd": 0.05}),
                json.dumps({"ts": old_ts, "callsign": "atlas", "estimated_cost_usd": 99.0}),
            ]
        ),
        encoding="utf-8",
    )
    out = _mod.load_openai_cost(hours=24, log_path=log)
    assert out == {"atlas": 0.10, "orion": 0.05}


def test_load_openai_cost_missing_log_returns_empty(tmp_path):
    assert _mod.load_openai_cost(hours=24, log_path=tmp_path / "no.jsonl") == {}


# ---------- vultr ----------


def test_load_vultr_cost_no_api_key_returns_skip_note():
    total, note = _mod.load_vultr_cost(hours=24, api_key="")
    assert total == 0.0
    assert "missing" in note.lower()


# ---------- aggregate ----------


def test_aggregate_combines_three_providers():
    summary = _mod.aggregate(
        anthropic={"atlas": 10.0, "orion": 5.0},
        openai={"atlas": 1.0},
        vultr_usd=2.0,
    )
    assert summary["by_provider_usd"] == {"anthropic": 15.0, "openai": 1.0, "vultr": 2.0}
    assert summary["by_callsign_usd"]["atlas"] == 11.0
    assert summary["by_callsign_usd"]["orion"] == 5.0
    assert summary["by_callsign_usd"]["fleet"] == 2.0
    assert summary["total_usd"] == 18.0
    assert abs(summary["total_aud"] - 27.90) < 0.001  # 18 × 1.55


def test_aggregate_includes_date_field():
    summary = _mod.aggregate({}, {}, 0.0)
    assert "date" in summary
    # ISO YYYY-MM-DD shape
    assert len(summary["date"]) == 10


# ---------- format_ceo_post ----------


def test_format_ceo_post_lead_line_carries_aud_total():
    summary = _mod.aggregate({"atlas": 10}, {"atlas": 1}, 2)
    post = _mod.format_ceo_post(summary, "Vultr API OK")
    lines = post.split("\n")
    assert lines[0].startswith("[ELLIOT] Daily cost:")
    assert "$" in lines[0]
    assert "AUD" in lines[0]


def test_format_ceo_post_carries_provider_and_callsign_lines():
    summary = _mod.aggregate({"atlas": 10}, {"atlas": 1}, 2)
    post = _mod.format_ceo_post(summary, "Vultr API OK")
    assert "Anthropic" in post
    assert "OpenAI" in post
    assert "Vultr" in post
    assert "atlas" in post
    assert "fleet" in post


def test_format_ceo_post_flags_vultr_skip_note():
    summary = _mod.aggregate({"atlas": 10}, {}, 0)
    post = _mod.format_ceo_post(summary, "VULTR_API_KEY missing — Vultr line skipped")
    assert "missing" in post


# ---------- post_to_ceo ----------


def test_post_to_ceo_invokes_tg_c_ceo_subprocess():
    calls = []

    class _FakeResult:
        returncode = 0

    def _fake_runner(*args, **kwargs):
        calls.append((args, kwargs))
        return _FakeResult()

    rc = _mod.post_to_ceo("daily summary line", runner=_fake_runner)
    assert rc == 0
    assert calls[0][0][0][:3] == ["tg", "-c", "ceo"]
    assert calls[0][0][0][3] == "daily summary line"


def test_post_to_ceo_handles_tg_not_found():
    def _raises(*args, **kwargs):
        raise FileNotFoundError("no tg")

    assert _mod.post_to_ceo("x", runner=_raises) == 2


# ---------- write_daily_log ----------


def test_write_daily_log_appends_jsonl(tmp_path: Path):
    log = tmp_path / "agency_daily.jsonl"
    _mod.write_daily_log({"date": "2026-05-27", "total_usd": 1.0}, log_path=log)
    _mod.write_daily_log({"date": "2026-05-28", "total_usd": 2.0}, log_path=log)
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["total_usd"] == 1.0
    assert json.loads(lines[1])["total_usd"] == 2.0
