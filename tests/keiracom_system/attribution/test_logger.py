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
    COMPLETION_STATUSES,
    SOURCE_TYPES,
    TASK_TYPES,
    SpawnAttributionEntry,
    aggregate_by_completion_status,
    load_attribution_last_24h,
    log_spawn_attribution,
)
from src.keiracom_system.attribution.logger import (
    SpawnAttributionError,
    aggregate_by_callsign,
    aggregate_by_source_type,
    aggregate_by_task_type,
)

# ---------- SOURCE_TYPES / TASK_TYPES ----------


def test_source_types_enumerated_to_six():
    """Six canonical source_types — v1_chain added 2026-05-30 for V1 chain
    attribution writes (companion migration:
    20260530_keiracom_spawn_attribution_v1_chain_source_type.sql)."""
    assert {"slack", "pr", "cron", "inbox", "unknown", "v1_chain"} == SOURCE_TYPES


def test_task_types_enumerated_to_six():
    """Cutover Blocker 7 / Cat 21 lever 23 — workload-class enum locked."""
    assert {"pr_review", "deliberation", "build", "chat", "dispatch_mgmt", "unknown"} == TASK_TYPES


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


# ---------- task_type (Cutover Blocker 7) ----------


def test_log_spawn_attribution_persists_task_type(tmp_path: Path):
    log = tmp_path / "attr.jsonl"
    entry = log_spawn_attribution(
        source_type="slack",
        source_id="ts-1",
        task_type="pr_review",
        callsign="atlas",
        model="claude-opus-4-7",
        log_path=log,
    )
    assert entry.task_type == "pr_review"
    raw = json.loads(log.read_text(encoding="utf-8").strip())
    assert raw["task_type"] == "pr_review"


def test_log_spawn_attribution_defaults_task_type_to_unknown(tmp_path: Path):
    """task_type defaults to 'unknown' when caller omits — explicit unknown
    is honest, lets dispatcher integration land in stages."""
    log = tmp_path / "attr.jsonl"
    entry = log_spawn_attribution(
        source_type="slack",
        source_id="ts-1",
        callsign="atlas",
        model="claude-opus-4-7",
        log_path=log,
    )
    assert entry.task_type == "unknown"


def test_log_spawn_attribution_rejects_unknown_task_type(tmp_path: Path):
    """Same discipline as source_type — silent default to a real task_type
    is a BUG; explicit 'unknown' is allowed; invalid values rejected."""
    with pytest.raises(SpawnAttributionError) as exc:
        log_spawn_attribution(
            source_type="slack",
            source_id="ts-1",
            task_type="data_migration",  # not in TASK_TYPES
            callsign="atlas",
            model="claude-opus-4-7",
            log_path=tmp_path / "attr.jsonl",
        )
    assert "data_migration" in str(exc.value)


def test_aggregate_by_task_type_sums_cost_and_counts_spawns():
    entries = [
        {"task_type": "pr_review", "callsign": "atlas", "cost_usd": 0.5},
        {"task_type": "pr_review", "callsign": "max", "cost_usd": 0.3},
        {"task_type": "build", "callsign": "atlas", "cost_usd": 2.0},
        {"task_type": "deliberation", "callsign": "elliot", "cost_usd": 1.0},
    ]
    out = aggregate_by_task_type(entries)
    assert out["pr_review"]["cost_usd_sum"] == 0.8
    assert out["pr_review"]["spawn_count"] == 2
    assert out["build"]["cost_usd_sum"] == 2.0
    assert out["build"]["spawn_count"] == 1
    assert out["deliberation"]["cost_usd_sum"] == 1.0


def test_aggregate_by_task_type_handles_missing_fields():
    entries = [{"source_type": "slack", "callsign": "atlas"}]  # no task_type
    out = aggregate_by_task_type(entries)
    assert "unknown" in out
    assert out["unknown"]["spawn_count"] == 1


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


# ---------- completion_status (Phase 1 cutover-gate, Agency_OS-vq7k) ----------


def test_completion_statuses_enumerated_to_five():
    """Phase 1 cutover-gate dispatch — outcome enum locked."""
    assert {"success", "fail", "timeout", "interrupted", "unknown"} == COMPLETION_STATUSES


def test_log_spawn_attribution_persists_completion_status(tmp_path: Path):
    log = tmp_path / "attr.jsonl"
    entry = log_spawn_attribution(
        source_type="cron",
        source_id="some-timer",
        callsign="scout",
        model="claude-opus-4-7",
        completion_status="success",
        log_path=log,
    )
    assert entry.completion_status == "success"
    raw = json.loads(log.read_text().strip())
    assert raw["completion_status"] == "success"


def test_log_spawn_attribution_defaults_completion_status_to_unknown(tmp_path: Path):
    """completion_status defaults to 'unknown' when caller omits — explicit
    unknown tag lets dispatch-time writers land before completion-classification
    logic is wired."""
    log = tmp_path / "attr.jsonl"
    entry = log_spawn_attribution(
        source_type="inbox",
        source_id="/tmp/telegram-relay-scout/inbox/x.json",
        callsign="scout",
        model="claude-opus-4-7",
        log_path=log,
    )
    assert entry.completion_status == "unknown"


def test_log_spawn_attribution_rejects_unknown_completion_status(tmp_path: Path):
    """Same discipline as source_type + task_type — silent default to a real
    completion_status is a BUG. Unknown enum value MUST raise."""
    log = tmp_path / "attr.jsonl"
    with pytest.raises(SpawnAttributionError) as excinfo:
        log_spawn_attribution(
            source_type="cron",
            source_id="some-timer",
            callsign="scout",
            model="claude-opus-4-7",
            completion_status="partial",  # not in COMPLETION_STATUSES
            log_path=log,
        )
    assert "completion_status" in str(excinfo.value)
    # Failed call must not have written anything.
    assert not log.exists() or log.read_text() == ""


def test_log_spawn_attribution_accepts_all_completion_statuses(tmp_path: Path):
    """All five enum values land cleanly."""
    log = tmp_path / "attr.jsonl"
    for status in sorted(COMPLETION_STATUSES):
        log_spawn_attribution(
            source_type="cron",
            source_id="t",
            callsign="scout",
            model="claude-opus-4-7",
            completion_status=status,
            log_path=log,
        )
    lines = log.read_text().strip().splitlines()
    statuses_written = {json.loads(line)["completion_status"] for line in lines}
    assert statuses_written == COMPLETION_STATUSES


def test_aggregate_by_completion_status_sums_cost_and_counts_spawns():
    entries = [
        {"completion_status": "success", "callsign": "atlas", "cost_usd": 0.5},
        {"completion_status": "success", "callsign": "max", "cost_usd": 0.3},
        {"completion_status": "fail", "callsign": "atlas", "cost_usd": 2.0},
        {"completion_status": "timeout", "callsign": "elliot", "cost_usd": 1.0},
        {"completion_status": "interrupted", "callsign": "scout", "cost_usd": 0.1},
    ]
    out = aggregate_by_completion_status(entries)
    assert out["success"]["cost_usd_sum"] == 0.8
    assert out["success"]["spawn_count"] == 2
    assert out["fail"]["cost_usd_sum"] == 2.0
    assert out["fail"]["spawn_count"] == 1
    assert out["timeout"]["cost_usd_sum"] == 1.0
    assert out["interrupted"]["cost_usd_sum"] == 0.1


def test_aggregate_by_completion_status_handles_missing_fields():
    """Missing completion_status defaults to 'unknown' in aggregation —
    mirrors task_type / source_type behaviour."""
    entries = [{"source_type": "slack", "callsign": "atlas", "cost_usd": 0.5}]
    out = aggregate_by_completion_status(entries)
    assert "unknown" in out
    assert out["unknown"]["spawn_count"] == 1
    assert out["unknown"]["cost_usd_sum"] == 0.5
