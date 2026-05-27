"""Unit tests for scripts/cache_hit_rate_ingest.py (Agency_OS-if0r).

Covers the pure-function surface (no Supabase):
- _extract_usage parses well-formed assistant-message rows + rejects malformed
- aggregate_callsign walks dirs + groups by date + counts distinct session UUIDs
- aggregate_all multi-callsign coalesces correctly
- write_jsonl_log emits the expected per-row shape

End-to-end DB upsert path is exercised via psycopg mock in a separate
integration suite (not here) — upsert_aggregates is a thin wrapper over
psycopg.connect.executemany.

bd: Agency_OS-if0r
"""

from __future__ import annotations

import importlib
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

_mod = importlib.import_module("cache_hit_rate_ingest")


# ---------------------------------------------------------------------------
# _extract_usage
# ---------------------------------------------------------------------------


def test_extract_usage_returns_date_and_token_dict_on_well_formed_row():
    line = json.dumps(
        {
            "timestamp": "2026-05-27T03:15:00Z",
            "message": {
                "usage": {
                    "input_tokens": 6,
                    "cache_creation_input_tokens": 47392,
                    "cache_read_input_tokens": 20742,
                    "output_tokens": 137,
                }
            },
        }
    )
    result = _mod._extract_usage(line)
    assert result is not None
    rollup, usage = result
    assert rollup == date(2026, 5, 27)
    assert usage["cache_read_input_tokens"] == 20742
    assert usage["cache_creation_input_tokens"] == 47392
    assert usage["input_tokens"] == 6
    assert usage["output_tokens"] == 137


def test_extract_usage_handles_iso_plus_zero_zero_format():
    line = json.dumps(
        {
            "timestamp": "2026-05-27T03:15:00+00:00",
            "message": {
                "usage": {
                    "input_tokens": 1,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 1,
                }
            },
        }
    )
    result = _mod._extract_usage(line)
    assert result is not None
    rollup, _ = result
    assert rollup == date(2026, 5, 27)


def test_extract_usage_skips_lines_without_message():
    line = json.dumps({"type": "file-history-snapshot", "messageId": "abc"})
    assert _mod._extract_usage(line) is None


def test_extract_usage_skips_lines_with_no_usage_object():
    line = json.dumps({"timestamp": "2026-05-27T03:15:00Z", "message": {"role": "user"}})
    assert _mod._extract_usage(line) is None


def test_extract_usage_skips_malformed_json():
    assert _mod._extract_usage("{not json{") is None


def test_extract_usage_skips_lines_missing_timestamp():
    line = json.dumps(
        {
            "message": {
                "usage": {
                    "input_tokens": 1,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 1,
                }
            }
        }
    )
    assert _mod._extract_usage(line) is None


def test_extract_usage_skips_unparseable_timestamp():
    line = json.dumps(
        {
            "timestamp": "not-a-timestamp",
            "message": {
                "usage": {
                    "input_tokens": 1,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 1,
                }
            },
        }
    )
    assert _mod._extract_usage(line) is None


def test_extract_usage_coerces_null_token_fields_to_zero():
    line = json.dumps(
        {
            "timestamp": "2026-05-27T03:15:00Z",
            "message": {
                "usage": {
                    "input_tokens": None,
                    "cache_creation_input_tokens": None,
                    "cache_read_input_tokens": 42,
                    "output_tokens": 5,
                }
            },
        }
    )
    result = _mod._extract_usage(line)
    assert result is not None
    _, usage = result
    assert usage["input_tokens"] == 0
    assert usage["cache_creation_input_tokens"] == 0
    assert usage["cache_read_input_tokens"] == 42


# ---------------------------------------------------------------------------
# projects_dir_for + aggregate_callsign
# ---------------------------------------------------------------------------


def test_projects_dir_for_elliot_has_no_suffix():
    p = _mod.projects_dir_for("elliot")
    assert p.name == "-home-elliotbot-clawd-Agency-OS"


def test_projects_dir_for_clone_has_callsign_suffix():
    assert _mod.projects_dir_for("scout").name == "-home-elliotbot-clawd-Agency-OS-scout"
    assert _mod.projects_dir_for("atlas").name == "-home-elliotbot-clawd-Agency-OS-atlas"


def _build_session_jsonl(tmp_dir: Path, session_uuid: str, lines: list[dict]) -> Path:
    """Helper: write a session JSONL into a fake projects dir."""
    path = tmp_dir / f"{session_uuid}.jsonl"
    with path.open("w") as fh:
        for d in lines:
            fh.write(json.dumps(d) + "\n")
    return path


def test_aggregate_callsign_returns_empty_when_dir_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path)
    out = _mod.aggregate_callsign("scout", date(2026, 5, 20))
    assert out == {}


def test_aggregate_callsign_groups_by_date_and_counts_distinct_sessions(monkeypatch, tmp_path):
    callsign_dir = tmp_path / "-home-elliotbot-clawd-Agency-OS-scout"
    callsign_dir.mkdir(parents=True)
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path)

    _build_session_jsonl(
        callsign_dir,
        "sess-A",
        [
            {
                "timestamp": "2026-05-27T03:00:00Z",
                "message": {
                    "usage": {
                        "input_tokens": 10,
                        "cache_read_input_tokens": 100,
                        "cache_creation_input_tokens": 50,
                        "output_tokens": 5,
                    }
                },
            },
            {
                "timestamp": "2026-05-27T04:00:00Z",
                "message": {
                    "usage": {
                        "input_tokens": 20,
                        "cache_read_input_tokens": 200,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 10,
                    }
                },
            },
        ],
    )
    _build_session_jsonl(
        callsign_dir,
        "sess-B",
        [
            {
                "timestamp": "2026-05-27T05:00:00Z",
                "message": {
                    "usage": {
                        "input_tokens": 30,
                        "cache_read_input_tokens": 300,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 15,
                    }
                },
            },
        ],
    )

    out = _mod.aggregate_callsign("scout", date(2026, 5, 27))
    assert date(2026, 5, 27) in out
    agg = out[date(2026, 5, 27)]
    assert agg["spawn_count"] == 2  # sess-A + sess-B
    assert agg["message_count"] == 3
    assert agg["cache_read_input_tokens"] == 600
    assert agg["input_tokens"] == 60
    assert agg["cache_creation_input_tokens"] == 50
    assert agg["output_tokens"] == 30


def test_aggregate_callsign_splits_across_days(monkeypatch, tmp_path):
    callsign_dir = tmp_path / "-home-elliotbot-clawd-Agency-OS-scout"
    callsign_dir.mkdir(parents=True)
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path)

    _build_session_jsonl(
        callsign_dir,
        "sess-day-spanner",
        [
            {
                "timestamp": "2026-05-26T23:30:00Z",
                "message": {
                    "usage": {
                        "input_tokens": 10,
                        "cache_read_input_tokens": 100,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 5,
                    }
                },
            },
            {
                "timestamp": "2026-05-27T00:30:00Z",
                "message": {
                    "usage": {
                        "input_tokens": 20,
                        "cache_read_input_tokens": 200,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 10,
                    }
                },
            },
        ],
    )

    out = _mod.aggregate_callsign("scout", date(2026, 5, 26))
    assert out[date(2026, 5, 26)]["cache_read_input_tokens"] == 100
    assert out[date(2026, 5, 27)]["cache_read_input_tokens"] == 200
    # Same session_uuid across both days → spawn_count=1 per day.
    assert out[date(2026, 5, 26)]["spawn_count"] == 1
    assert out[date(2026, 5, 27)]["spawn_count"] == 1


def test_aggregate_callsign_filters_below_since(monkeypatch, tmp_path):
    """Rows older than `since` are dropped (not aggregated)."""
    callsign_dir = tmp_path / "-home-elliotbot-clawd-Agency-OS-scout"
    callsign_dir.mkdir(parents=True)
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path)

    _build_session_jsonl(
        callsign_dir,
        "sess-old",
        [
            {
                "timestamp": "2026-04-01T03:00:00Z",
                "message": {
                    "usage": {
                        "input_tokens": 10,
                        "cache_read_input_tokens": 100,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 5,
                    }
                },
            },
            {
                "timestamp": "2026-05-27T03:00:00Z",
                "message": {
                    "usage": {
                        "input_tokens": 5,
                        "cache_read_input_tokens": 50,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 2,
                    }
                },
            },
        ],
    )

    out = _mod.aggregate_callsign("scout", date(2026, 5, 27))
    # Only the May 27 row survives.
    assert date(2026, 4, 1) not in out
    assert out[date(2026, 5, 27)]["cache_read_input_tokens"] == 50


# ---------------------------------------------------------------------------
# write_jsonl_log
# ---------------------------------------------------------------------------


def test_write_jsonl_log_emits_one_line_per_bucket_with_hit_rate(tmp_path):
    aggregates = {
        (date(2026, 5, 27), "scout"): {
            "spawn_count": 1,
            "message_count": 2,
            "cache_read_input_tokens": 950,
            "cache_creation_input_tokens": 100,
            "input_tokens": 50,
            "output_tokens": 10,
        },
    }
    log_path = tmp_path / "out.jsonl"
    _mod.write_jsonl_log(aggregates, log_path)
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["rollup_date"] == "2026-05-27"
    assert row["callsign"] == "scout"
    # hit_rate = 950 / (950 + 50) = 95.0
    assert row["hit_rate_percent"] == 95.0
    assert row["spawn_count"] == 1
    assert row["assistant_message_count"] == 2


def test_write_jsonl_log_handles_zero_input_with_null_hit_rate(tmp_path):
    aggregates = {
        (date(2026, 5, 27), "elliot"): {
            "spawn_count": 0,
            "message_count": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        },
    }
    log_path = tmp_path / "empty.jsonl"
    _mod.write_jsonl_log(aggregates, log_path)
    row = json.loads(log_path.read_text().strip())
    assert row["hit_rate_percent"] is None
