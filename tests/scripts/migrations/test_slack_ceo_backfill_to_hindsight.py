"""Tests for Phase A5 piece 4 — Slack #ceo archive backfill.

Covers:
- load_messages_from_jsonl (JSONL parsing + malformed-line tolerance)
- detect_viktor_gaps (3 gap shapes per Viktor 2026-05-25)
- format_content + build_metadata
- ingest_message happy / error / exception
- run() refuses on missing/empty input, dry-run vs execute, rc=1 on
  failure, skip-on-rerun, missing-ts handling

bd: Agency_OS-ygxz
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "migrations"))

_mod = importlib.import_module("slack_ceo_backfill_to_hindsight")


class _SpyWrapper:
    def __init__(self, *, fail_ids: set[str] | None = None) -> None:
        self.calls: list[dict] = []
        self.fail_ids = fail_ids or set()

    def ingest(self, **kwargs):
        self.calls.append(kwargs)
        meta = kwargs.get("metadata") or {}
        if meta.get("external_id", "") in self.fail_ids:
            return {"error": "simulated"}
        return {"id": f"hs-{len(self.calls)}"}


def _write_msgs(tmp_path: Path, name: str, msgs: list[dict]) -> Path:
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(m) for m in msgs) + "\n", encoding="utf-8")
    return p


def test_load_messages_skips_malformed_lines(tmp_path: Path):
    p = tmp_path / "m.jsonl"
    p.write_text('{"ts": "1.1"}\nnot-json\n{"ts": "2.2"}\n', encoding="utf-8")
    out = _mod.load_messages_from_jsonl(p)
    assert len(out) == 2
    assert out[0]["ts"] == "1.1"
    assert out[1]["ts"] == "2.2"


def test_detect_viktor_gaps_missing_user():
    gaps = _mod.detect_viktor_gaps({"ts": "1.1", "text": "hi", "user": ""})
    assert "missing_user" in gaps
    assert "missing_text" not in gaps
    assert "missing_ts" not in gaps


def test_detect_viktor_gaps_missing_text():
    gaps = _mod.detect_viktor_gaps({"ts": "1.1", "user": "U1"})
    assert gaps == ["missing_text"]


def test_detect_viktor_gaps_missing_ts():
    gaps = _mod.detect_viktor_gaps({"user": "U1", "text": "hi"})
    assert gaps == ["missing_ts"]


def test_detect_viktor_gaps_all_missing():
    gaps = _mod.detect_viktor_gaps({})
    assert set(gaps) == {"missing_user", "missing_text", "missing_ts"}


def test_format_content_user_and_text():
    assert _mod.format_content({"user": "U1", "text": "hello world"}) == "[U1] hello world"


def test_format_content_missing_user_uses_question_mark():
    assert _mod.format_content({"text": "hello"}) == "[?] hello"


def test_format_content_missing_text_keeps_user_prefix():
    out = _mod.format_content({"user": "U1"})
    assert out == "[U1]"  # rstrip drops the trailing space


def test_build_metadata_carries_slack_fields_and_external_id():
    msg = {"ts": "1779747400.123", "user": "U_DAVE", "text": "ok", "channel": "ceo"}
    meta = _mod.build_metadata(msg, Path("/tmp/m.jsonl"))
    assert meta["source"] == "a5_piece_4_slack_ceo_backfill"
    assert meta["source_file"] == "/tmp/m.jsonl"
    assert meta["slack_ts"] == "1779747400.123"
    assert meta["slack_user"] == "U_DAVE"
    assert meta["slack_channel"] == "ceo"
    assert meta["external_id"] == "slack-ceo:1779747400.123"
    assert meta["viktor_gaps"] == ""  # no gaps


def test_build_metadata_carries_viktor_gaps_string():
    msg = {"ts": "1.1"}  # missing user + text
    meta = _mod.build_metadata(msg, Path("/tmp/m.jsonl"))
    gaps = meta["viktor_gaps"].split(",")
    assert "missing_user" in gaps
    assert "missing_text" in gaps


def test_ingest_message_happy_path():
    wrapper = _SpyWrapper()
    msg = {"ts": "1.1", "user": "U1", "text": "hello"}
    ok, info = _mod.ingest_message(msg, Path("/tmp/m.jsonl"), taskcontext_wrapper=wrapper)
    assert ok is True
    assert "hs-1" in info
    call = wrapper.calls[0]
    assert call["tenant_id"] == _mod.FLEET_TENANT_ID
    assert call["content"] == "[U1] hello"
    assert call["metadata"]["external_id"] == "slack-ceo:1.1"


def test_ingest_message_returns_false_on_dict_error():
    wrapper = _SpyWrapper(fail_ids={"slack-ceo:1.1"})
    msg = {"ts": "1.1", "user": "U1", "text": "x"}
    ok, info = _mod.ingest_message(msg, Path("/tmp/m.jsonl"), taskcontext_wrapper=wrapper)
    assert ok is False
    assert "hindsight_error" in info


def test_ingest_message_returns_false_on_exception():
    class _Bad:
        def ingest(self, **kwargs):
            raise ConnectionError("boom")

    msg = {"ts": "1.1", "user": "U1", "text": "x"}
    ok, info = _mod.ingest_message(msg, Path("/tmp/m.jsonl"), taskcontext_wrapper=_Bad())
    assert ok is False
    assert "ConnectionError" in info


def test_state_roundtrip(tmp_path: Path):
    state = tmp_path / "s.jsonl"
    _mod.append_state(state, {"external_id": "slack-ceo:1.1", "ok": True})
    _mod.append_state(state, {"external_id": "slack-ceo:1.2", "ok": False})
    assert _mod.load_state(state) == {"slack-ceo:1.1"}


def test_run_aborts_on_empty_input(tmp_path: Path):
    rc = _mod.run(input_files=[], execute=True, state_path=tmp_path / "s.jsonl")
    assert rc == 2


def test_run_aborts_on_missing_file(tmp_path: Path):
    rc = _mod.run(
        input_files=[tmp_path / "missing.jsonl"],
        execute=True,
        state_path=tmp_path / "s.jsonl",
    )
    assert rc == 2


def test_run_dry_run_does_not_call_wrapper(tmp_path: Path):
    f = _write_msgs(tmp_path, "m.jsonl", [{"ts": "1.1", "user": "U", "text": "x"}])
    wrapper = _SpyWrapper()
    rc = _mod.run(
        input_files=[f],
        execute=False,
        state_path=tmp_path / "s.jsonl",
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert wrapper.calls == []


def test_run_execute_ingests_each_message_and_writes_state(tmp_path: Path):
    f = _write_msgs(
        tmp_path,
        "m.jsonl",
        [
            {"ts": "1.1", "user": "U1", "text": "msg-a"},
            {"ts": "1.2", "user": "U2", "text": "msg-b"},
        ],
    )
    wrapper = _SpyWrapper()
    state = tmp_path / "s.jsonl"
    rc = _mod.run(
        input_files=[f],
        execute=True,
        state_path=state,
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert len(wrapper.calls) == 2
    assert _mod.load_state(state) == {"slack-ceo:1.1", "slack-ceo:1.2"}


def test_run_returns_one_when_message_missing_ts(tmp_path: Path):
    """Per docstring: messages without ts cannot be idempotency-keyed → fail."""
    f = _write_msgs(tmp_path, "m.jsonl", [{"user": "U1", "text": "no-ts"}])
    wrapper = _SpyWrapper()
    rc = _mod.run(
        input_files=[f],
        execute=True,
        state_path=tmp_path / "s.jsonl",
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 1
    assert wrapper.calls == []  # never reached ingest


def test_run_returns_one_on_ingest_failure(tmp_path: Path):
    f = _write_msgs(tmp_path, "m.jsonl", [{"ts": "1.1", "user": "U", "text": "x"}])
    wrapper = _SpyWrapper(fail_ids={"slack-ceo:1.1"})
    rc = _mod.run(
        input_files=[f],
        execute=True,
        state_path=tmp_path / "s.jsonl",
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 1


def test_run_skips_already_completed_external_ids(tmp_path: Path):
    f = _write_msgs(
        tmp_path,
        "m.jsonl",
        [
            {"ts": "1.1", "user": "U1", "text": "msg-a"},
            {"ts": "1.2", "user": "U2", "text": "msg-b"},
        ],
    )
    state = tmp_path / "s.jsonl"
    _mod.append_state(state, {"external_id": "slack-ceo:1.1", "ok": True})
    wrapper = _SpyWrapper()
    rc = _mod.run(
        input_files=[f],
        execute=True,
        state_path=state,
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert len(wrapper.calls) == 1
    assert wrapper.calls[0]["metadata"]["external_id"] == "slack-ceo:1.2"


def test_run_handles_multiple_input_files(tmp_path: Path):
    f1 = _write_msgs(tmp_path, "f1.jsonl", [{"ts": "1.1", "user": "U", "text": "a"}])
    f2 = _write_msgs(tmp_path, "f2.jsonl", [{"ts": "2.2", "user": "U", "text": "b"}])
    wrapper = _SpyWrapper()
    rc = _mod.run(
        input_files=[f1, f2],
        execute=True,
        state_path=tmp_path / "s.jsonl",
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert len(wrapper.calls) == 2
