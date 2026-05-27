"""Tests for src/keiracom_system/attribution/logger.py.

Covers: SOURCE_TYPES enum lock; log_spawn_attribution write + reject
unknown source_type; load_attribution_last_24h window filter +
malformed-line tolerance; aggregate_by_source_type + aggregate_by_callsign.

bd: Agency_OS-90ho
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.keiracom_system.attribution import (
    SOURCE_TYPES,
    SpawnAttributionEntry,
    load_attribution_last_24h,
    log_spawn_attribution,
)
from src.keiracom_system.attribution.logger import (
    SpawnAttributionError,
    aggregate_by_callsign,
    aggregate_by_source_type,
)

# ---------- SOURCE_TYPES ----------


def test_source_types_enumerated_to_five():
    assert {"slack", "pr", "cron", "inbox", "unknown"} == SOURCE_TYPES


# ---------- log_spawn_attribution ----------


def test_log_spawn_attribution_writes_jsonl_row(tmp_path: Path):
    log = tmp_path / "attr.jsonl"
    entry = log_spawn_attribution(
        source_type="slack",
        source_id="1779843644",
        callsign="atlas",
        model="claude-opus-4-7",
        input_tokens=7,
        output_tokens=163,
        cache_read_tokens=74268,
        cache_write_tokens=74529,
        cost_usd=0.50705,
        log_path=log,
    )
    assert isinstance(entry, SpawnAttributionEntry)
    assert entry.source_type == "slack"
    assert entry.cost_usd == 0.50705
    raw = json.loads(log.read_text(encoding="utf-8").strip())
    assert raw["source_type"] == "slack"
    assert raw["source_id"] == "1779843644"
    assert raw["callsign"] == "atlas"
    assert raw["model"] == "claude-opus-4-7"
    assert raw["cost_usd"] == 0.50705


def test_log_spawn_attribution_rejects_unknown_source_type(tmp_path: Path):
    with pytest.raises(SpawnAttributionError) as exc:
        log_spawn_attribution(
            source_type="github_webhook",  # not in SOURCE_TYPES
            source_id="x",
            callsign="atlas",
            model="claude-opus-4-7",
            log_path=tmp_path / "attr.jsonl",
        )
    assert "github_webhook" in str(exc.value)


def test_log_spawn_attribution_accepts_unknown_explicit_tag(tmp_path: Path):
    """Explicit 'unknown' tag is accepted — silent fallback is the bug;
    explicit unknown is honest."""
    entry = log_spawn_attribution(
        source_type="unknown",
        source_id="some-unidentified-dispatch",
        callsign="atlas",
        model="claude-opus-4-7",
        log_path=tmp_path / "attr.jsonl",
    )
    assert entry.source_type == "unknown"


def test_log_spawn_attribution_appends_not_overwrites(tmp_path: Path):
    log = tmp_path / "attr.jsonl"
    log_spawn_attribution(
        source_type="slack",
        source_id="ts1",
        callsign="atlas",
        model="claude-opus-4-7",
        log_path=log,
    )
    log_spawn_attribution(
        source_type="pr",
        source_id="PR-1202",
        callsign="atlas",
        model="claude-opus-4-7",
        log_path=log,
    )
    lines = log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2


def test_log_spawn_attribution_creates_parent_dir(tmp_path: Path):
    log = tmp_path / "deeply" / "nested" / "attr.jsonl"
    log_spawn_attribution(
        source_type="cron",
        source_id="agency-cost-rollup.timer",
        callsign="elliot",
        model="claude-opus-4-7",
        log_path=log,
    )
    assert log.exists()


# ---------- load_attribution_last_24h ----------


def test_load_attribution_filters_by_window(tmp_path: Path):
    log = tmp_path / "attr.jsonl"
    now = datetime.now(UTC)
    old = now - timedelta(hours=48)
    log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": now.isoformat(),
                        "source_type": "slack",
                        "callsign": "atlas",
                        "cost_usd": 0.50,
                    }
                ),
                json.dumps(
                    {
                        "ts": old.isoformat(),
                        "source_type": "pr",
                        "callsign": "atlas",
                        "cost_usd": 99.0,
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    out = load_attribution_last_24h(log_path=log)
    assert len(out) == 1
    assert out[0]["source_type"] == "slack"


def test_load_attribution_missing_log_returns_empty(tmp_path: Path):
    assert load_attribution_last_24h(log_path=tmp_path / "no.jsonl") == []


def test_load_attribution_skips_malformed_lines(tmp_path: Path):
    log = tmp_path / "attr.jsonl"
    now_iso = datetime.now(UTC).isoformat()
    log.write_text(
        f"{json.dumps({'ts': now_iso, 'source_type': 'slack', 'callsign': 'atlas', 'cost_usd': 0.1})}\n"
        "not-json\n"
        f"{json.dumps({'ts': now_iso, 'source_type': 'pr', 'callsign': 'orion', 'cost_usd': 0.2})}\n",
        encoding="utf-8",
    )
    out = load_attribution_last_24h(log_path=log)
    assert len(out) == 2


# ---------- aggregate_by_source_type ----------


def test_aggregate_by_source_type_sums_cost_and_counts_spawns():
    entries = [
        {"source_type": "slack", "callsign": "atlas", "cost_usd": 0.5},
        {"source_type": "slack", "callsign": "atlas", "cost_usd": 0.3},
        {"source_type": "pr", "callsign": "orion", "cost_usd": 1.0},
    ]
    out = aggregate_by_source_type(entries)
    assert out["slack"]["cost_usd_sum"] == 0.8
    assert out["slack"]["spawn_count"] == 2
    assert out["pr"]["cost_usd_sum"] == 1.0
    assert out["pr"]["spawn_count"] == 1


def test_aggregate_by_source_type_handles_missing_fields():
    entries = [{}]
    out = aggregate_by_source_type(entries)
    assert "unknown" in out
    assert out["unknown"]["cost_usd_sum"] == 0.0
    assert out["unknown"]["spawn_count"] == 1


# ---------- aggregate_by_callsign ----------


def test_aggregate_by_callsign_sums_cost_and_counts_spawns():
    entries = [
        {"source_type": "slack", "callsign": "atlas", "cost_usd": 0.5},
        {"source_type": "pr", "callsign": "atlas", "cost_usd": 0.3},
        {"source_type": "cron", "callsign": "elliot", "cost_usd": 0.1},
    ]
    out = aggregate_by_callsign(entries)
    assert out["atlas"]["cost_usd_sum"] == 0.8
    assert out["atlas"]["spawn_count"] == 2
    assert out["elliot"]["cost_usd_sum"] == 0.1
