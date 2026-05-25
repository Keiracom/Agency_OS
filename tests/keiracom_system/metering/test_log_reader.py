"""Tests for src/keiracom_system/metering/log_reader.py — Phase 2 wave 2 item 3.

Negative-path discipline per feedback_negative_path_test_before_approve:
the reader's job is to filter out malformed/non-billable lines without
raising. Each filter branch needs explicit negative coverage on a
synthetic offender.

16 cases total — 4 happy paths + 12 negative/edge paths.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.metering.log_reader import (  # noqa: E402
    DEFAULT_FIELD_MAP,
    LLM_CALL_EVENT_TYPES,
    LogReader,
    MeteringEvent,
)


def _line(**kw) -> str:
    """Build a Hindsight-shaped JSON log line."""
    base = {
        "event": "llm_call",
        "tenant": "tenant-A",
        "model": "gpt-4o-mini",
        "usage": {"input_tokens": 100, "output_tokens": 50},
        "ts": "2026-05-25T10:00:00Z",
    }
    base.update(kw)
    return json.dumps(base)


def _stream(*lines: str) -> io.StringIO:
    return io.StringIO("\n".join(lines) + "\n")


def test_read_events_single_valid_line_emits_event():
    """(1) one well-formed llm_call line → one MeteringEvent."""
    events = list(LogReader(_stream(_line())).read_events())
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, MeteringEvent)
    assert ev.tenant_id == "tenant-A"
    assert ev.model == "gpt-4o-mini"
    assert ev.input_tokens == 100
    assert ev.output_tokens == 50
    assert ev.date_utc == "2026-05-25"


def test_read_events_multiple_valid_lines_emit_in_order():
    """(2) 3 well-formed lines → 3 events, insertion-order preserved."""
    lines = [
        _line(tenant="t1"),
        _line(tenant="t2"),
        _line(tenant="t3"),
    ]
    events = list(LogReader(_stream(*lines)).read_events())
    assert [e.tenant_id for e in events] == ["t1", "t2", "t3"]


def test_read_events_unix_epoch_timestamp_parses():
    """(3) Hindsight may emit numeric epoch — parses to UTC datetime.

    2026-05-25T10:00:00Z == 1779703200 unix epoch
    (verified: datetime(2026,5,25,10,0,0,tzinfo=UTC).timestamp()).
    """
    events = list(LogReader(_stream(_line(ts=1779703200))).read_events())
    assert len(events) == 1
    assert events[0].date_utc == "2026-05-25"


def test_read_events_field_map_override_handles_alt_schema():
    """(4) injected field_map absorbs Hindsight schema drift without code change."""
    alt = json.dumps(
        {
            "kind": "llm_call",
            "tenant_uuid": "alt-tenant",
            "llm_model": "claude-opus",
            "tokens_in": 5,
            "tokens_out": 10,
            "timestamp": "2026-05-25T10:00:00Z",
        }
    )
    field_map = {
        "tenant_id": "tenant_uuid",
        "model": "llm_model",
        "input_tokens": "tokens_in",
        "output_tokens": "tokens_out",
        "timestamp": "timestamp",
        "event_type": "kind",
    }
    events = list(LogReader(_stream(alt), field_map=field_map).read_events())
    assert len(events) == 1
    assert events[0].tenant_id == "alt-tenant"
    assert events[0].model == "claude-opus"
    assert events[0].input_tokens == 5
    assert events[0].output_tokens == 10


def test_read_events_empty_lines_skipped():
    """(5) blank / whitespace-only lines silently skipped."""
    events = list(LogReader(_stream("", "   ", _line())).read_events())
    assert len(events) == 1  # only the real line emitted


def test_read_events_malformed_json_skipped_not_raised():
    """(6) one bad-JSON line + one valid → reader yields the valid one only."""
    events = list(LogReader(_stream("{not-json}", _line())).read_events())
    assert len(events) == 1
    assert events[0].tenant_id == "tenant-A"


def test_read_events_non_dict_json_skipped():
    """(7) a JSON array/scalar line is not a log object — skipped."""
    events = list(LogReader(_stream("[1, 2, 3]", '"just a string"', _line())).read_events())
    assert len(events) == 1


def test_read_events_non_llm_event_types_filtered_out():
    """(8) retain/recall/healthcheck lines never reach the aggregator."""
    lines = [
        _line(event="retain"),
        _line(event="recall"),
        _line(event="healthcheck"),
        _line(event="llm_call"),  # only this one is billable
    ]
    events = list(LogReader(_stream(*lines)).read_events())
    assert len(events) == 1
    assert events[0].tenant_id == "tenant-A"


def test_read_events_all_llm_event_types_accepted():
    """(9) all three known LLM event types (llm_call, reflect, synthesize) emit events."""
    lines = [_line(event=et) for et in LLM_CALL_EVENT_TYPES]
    events = list(LogReader(_stream(*lines)).read_events())
    assert len(events) == len(LLM_CALL_EVENT_TYPES)


def test_read_events_missing_tenant_skipped():
    """(10) line lacking the tenant field → skipped (logged at WARN)."""
    bad = json.dumps({"event": "llm_call", "model": "x", "ts": "2026-05-25T10:00:00Z"})
    events = list(LogReader(_stream(bad)).read_events())
    assert events == []


def test_read_events_missing_model_skipped():
    """(11) line lacking the model field → skipped."""
    bad = json.dumps({"event": "llm_call", "tenant": "t1", "ts": "2026-05-25T10:00:00Z"})
    events = list(LogReader(_stream(bad)).read_events())
    assert events == []


def test_read_events_missing_timestamp_skipped():
    """(12) line lacking the timestamp field → skipped (cannot bucket)."""
    bad = json.dumps({"event": "llm_call", "tenant": "t1", "model": "x"})
    events = list(LogReader(_stream(bad)).read_events())
    assert events == []


def test_read_events_bad_timestamp_string_skipped():
    """(13) unparseable timestamp string → skipped, no exception."""
    events = list(LogReader(_stream(_line(ts="not-a-date"))).read_events())
    assert events == []


def test_read_events_unsupported_timestamp_type_skipped():
    """(14) timestamp of dict/list type → skipped (not a stringy or numeric ts)."""
    events = list(LogReader(_stream(_line(ts={"year": 2026}))).read_events())
    assert events == []


def test_read_events_missing_token_counts_default_to_zero():
    """(15) usage block absent or partial → tokens default to 0 (no skip).

    Some Hindsight log events legitimately omit usage when the LLM provider
    didn't return token counts. Treat as 0 rather than dropping the request
    entirely — we still want to count the request_count.
    """
    no_usage = json.dumps(
        {"event": "llm_call", "tenant": "t1", "model": "x", "ts": "2026-05-25T10:00:00Z"}
    )
    events = list(LogReader(_stream(no_usage)).read_events())
    assert len(events) == 1
    assert events[0].input_tokens == 0
    assert events[0].output_tokens == 0


def test_read_events_default_field_map_matches_documented_keys():
    """(16) DEFAULT_FIELD_MAP is the documented Hindsight schema mapping.

    Regression guard: future edits to the DEFAULT_FIELD_MAP need to preserve
    the documented key names (or update PR #1128 §5 in lockstep). Locks the
    contract surface so downstream readers know which env to override.
    """
    assert DEFAULT_FIELD_MAP["tenant_id"] == "tenant"
    assert DEFAULT_FIELD_MAP["event_type"] == "event"
    assert DEFAULT_FIELD_MAP["timestamp"] == "ts"
    assert DEFAULT_FIELD_MAP["input_tokens"] == "usage.input_tokens"


@pytest.mark.parametrize(
    "ts_input,expected_date",
    [
        ("2026-05-25T10:00:00Z", "2026-05-25"),
        ("2026-05-25T23:59:59+00:00", "2026-05-25"),
        ("2026-05-26T00:00:01+00:00", "2026-05-26"),
    ],
)
def test_read_events_date_utc_derives_from_timestamp(ts_input, expected_date):
    """(17a/b/c) UTC date-bucket derives correctly across day boundaries."""
    events = list(LogReader(_stream(_line(ts=ts_input))).read_events())
    assert events[0].date_utc == expected_date
