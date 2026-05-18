"""Tests for slack_history_indexer — KEI-201 Phase 2 incremental daemon.

Covers checkpoint round-trip, oldest= filter wiring, bootstrap-now ts shape,
atomic write, and the index_channel walk against a stubbed paginate_history.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "slack_history_indexer.py"


@pytest.fixture(scope="module")
def indexer():
    spec = importlib.util.spec_from_file_location("slack_history_indexer", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["slack_history_indexer"] = m
    spec.loader.exec_module(m)
    return m


# ─── checkpoint_path resolution ──────────────────────────────────────────────


def test_checkpoint_path_default(indexer, monkeypatch, tmp_path):
    monkeypatch.delenv("SLACK_HISTORY_CHECKPOINT", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    p = indexer.checkpoint_path()
    assert p == tmp_path / ".local" / "state" / "agency-os" / "slack_history_checkpoint.json"


def test_checkpoint_path_xdg_state_home_wins(indexer, monkeypatch, tmp_path):
    monkeypatch.delenv("SLACK_HISTORY_CHECKPOINT", raising=False)
    state = tmp_path / "xdg-state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    p = indexer.checkpoint_path()
    assert p == state / "agency-os" / "slack_history_checkpoint.json"


def test_checkpoint_path_env_override_wins(indexer, monkeypatch, tmp_path):
    override = tmp_path / "custom.json"
    monkeypatch.setenv("SLACK_HISTORY_CHECKPOINT", str(override))
    # XDG override here is also under tmp_path (safe). The S2083 rejection of
    # arbitrary outside-safe-roots paths is exercised in the tests below.
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-ignored"))
    assert indexer.checkpoint_path() == override.resolve()


# ─── Sonar S2083 — Path Traversal guard ──────────────────────────────────────


def test_checkpoint_path_rejects_dotdot_override(indexer, monkeypatch, tmp_path):
    """Override containing '..' segment is ignored; default is used."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SLACK_HISTORY_CHECKPOINT", str(tmp_path / ".." / "escape.json"))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    p = indexer.checkpoint_path()
    assert p == tmp_path / ".local" / "state" / "agency-os" / "slack_history_checkpoint.json"


def test_checkpoint_path_rejects_relative_override(indexer, monkeypatch, tmp_path):
    """Relative override is ignored; default is used."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SLACK_HISTORY_CHECKPOINT", "relative/cp.json")
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    p = indexer.checkpoint_path()
    assert p == tmp_path / ".local" / "state" / "agency-os" / "slack_history_checkpoint.json"


def test_checkpoint_path_rejects_outside_safe_roots(indexer, monkeypatch, tmp_path):
    """Absolute override outside $HOME / /var/lib / /tmp is ignored."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SLACK_HISTORY_CHECKPOINT", "/etc/passwd")
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    p = indexer.checkpoint_path()
    assert p == tmp_path / ".local" / "state" / "agency-os" / "slack_history_checkpoint.json"


def test_checkpoint_path_rejects_outside_safe_roots_xdg(indexer, monkeypatch, tmp_path):
    """XDG_STATE_HOME override outside safe roots is ignored; default is used."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SLACK_HISTORY_CHECKPOINT", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", "/etc")
    p = indexer.checkpoint_path()
    assert p == tmp_path / ".local" / "state" / "agency-os" / "slack_history_checkpoint.json"


# ─── load/save round-trip ────────────────────────────────────────────────────


def test_load_checkpoint_cold_start_returns_empty(indexer, tmp_path):
    assert indexer.load_checkpoint(tmp_path / "nope.json") == {}


def test_load_checkpoint_malformed_returns_empty(indexer, tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    assert indexer.load_checkpoint(p) == {}


def test_save_then_load_round_trip(indexer, tmp_path):
    p = tmp_path / "cp.json"
    data = {"ceo": "1779065531.123", "execution": "1779065532.456"}
    indexer.save_checkpoint(p, data)
    assert indexer.load_checkpoint(p) == data


def test_save_checkpoint_creates_parent_dir(indexer, tmp_path):
    p = tmp_path / "nested" / "deeper" / "cp.json"
    indexer.save_checkpoint(p, {"ceo": "1.1"})
    assert p.exists()
    assert json.loads(p.read_text()) == {"ceo": "1.1"}


def test_save_checkpoint_atomic_via_tmp_rename(indexer, tmp_path):
    """Write goes through .tmp + rename → no partial file under target name."""
    p = tmp_path / "cp.json"
    indexer.save_checkpoint(p, {"ceo": "1.1"})
    # No leftover .tmp after success
    assert not (tmp_path / "cp.json.tmp").exists()
    assert p.exists()


# ─── bootstrap_now_ts shape ──────────────────────────────────────────────────


def test_bootstrap_now_ts_shape(indexer):
    """Slack ts format: 'unix_seconds.microseconds_padded' — must be float-parseable."""
    ts = indexer.bootstrap_now_ts()
    assert "." in ts
    parsed = float(ts)
    assert parsed > 1_700_000_000  # after 2023-11
    assert parsed < 2_000_000_000  # before 2033


# ─── index_channel walk ──────────────────────────────────────────────────────


def test_index_channel_advances_max_ts(indexer):
    """new_last_ts must be max(ts) seen across kept messages."""
    raws = [
        {"text": "real content one", "ts": "1779065531.100", "user": "U1"},
        {"text": "[READY:scout]", "ts": "1779065532.200", "user": "U2"},  # noise
        {"text": "real content two", "ts": "1779065533.300", "user": "U3"},
    ]
    by_type: dict[str, int] = {}
    with (
        patch.object(indexer.ingest, "paginate_history", return_value=iter(raws)),
        patch.object(indexer.ingest, "post_object", return_value=True),
    ):
        kept, posted, failed, new_ts = indexer.index_channel(
            "ceo", "C-CEO", oldest="1779065530.000", by_type=by_type
        )
    assert kept == 2
    assert posted == 2
    assert failed == 0
    assert new_ts == "1779065533.300"


def test_index_channel_no_new_messages_holds_oldest(indexer):
    """Empty page → checkpoint stays at oldest (no regression)."""
    by_type: dict[str, int] = {}
    with patch.object(indexer.ingest, "paginate_history", return_value=iter([])):
        kept, posted, failed, new_ts = indexer.index_channel(
            "ceo", "C-CEO", oldest="1779065530.000", by_type=by_type
        )
    assert kept == 0
    assert posted == 0
    assert failed == 0
    assert new_ts == "1779065530.000"


def test_index_channel_post_failure_counts(indexer):
    """post_object False → counted as failed, NOT posted."""
    raws = [{"text": "real content", "ts": "1779065531.100", "user": "U1"}]
    by_type: dict[str, int] = {}
    with (
        patch.object(indexer.ingest, "paginate_history", return_value=iter(raws)),
        patch.object(indexer.ingest, "post_object", return_value=False),
    ):
        kept, posted, failed, _new_ts = indexer.index_channel(
            "ceo", "C-CEO", oldest="0", by_type=by_type
        )
    assert kept == 1
    assert posted == 0
    assert failed == 1


def test_index_channel_idempotent_on_redelivery(indexer):
    """post_object returns True on 422-already-exists per ingest.post_object — counted as posted."""
    raws = [
        {"text": "real content one", "ts": "1779065531.100", "user": "U1"},
        {"text": "real content one repeat", "ts": "1779065531.100", "user": "U1"},
    ]
    by_type: dict[str, int] = {}
    with (
        patch.object(indexer.ingest, "paginate_history", return_value=iter(raws)),
        patch.object(indexer.ingest, "post_object", return_value=True),
    ):
        kept, posted, failed, _new_ts = indexer.index_channel(
            "ceo", "C-CEO", oldest="0", by_type=by_type
        )
    assert kept == 2
    assert posted == 2
    assert failed == 0


def test_index_channel_by_type_accumulates_across_calls(indexer):
    """by_type dict is the running counter — verifies the caller-owned mutation contract."""
    by_type: dict[str, int] = {"ceo_directive": 5}
    raws = [
        {"text": "Dave directive: ship it", "ts": "1779065531.100", "user": "U1"},
        {"text": "[SHIPPED] PR #999 merged", "ts": "1779065532.200", "user": "U2"},
    ]
    with (
        patch.object(indexer.ingest, "paginate_history", return_value=iter(raws)),
        patch.object(indexer.ingest, "post_object", return_value=True),
    ):
        indexer.index_channel("ceo", "C-CEO", oldest="0", by_type=by_type)
    assert by_type["ceo_directive"] == 6  # pre-existing 5 + 1 new
    assert by_type["completion_report"] == 1


# ─── paginate_history wiring ─────────────────────────────────────────────────


def test_paginate_history_passes_oldest_to_slack(indexer):
    """The indexer's incremental contract: oldest= must end up in the Slack API params."""
    captured = {}

    def fake_slack_get(method: str, params: dict) -> dict:
        captured["method"] = method
        captured["params"] = params
        return {"messages": [], "response_metadata": {}}

    with patch.object(indexer.ingest, "_slack_get", side_effect=fake_slack_get):
        list(indexer.ingest.paginate_history("C-CEO", oldest="1779065530.000"))
    assert captured["method"] == "conversations.history"
    assert captured["params"]["channel"] == "C-CEO"
    assert captured["params"]["oldest"] == "1779065530.000"


def test_paginate_history_omits_oldest_when_empty(indexer):
    """Bulk extractor compatibility: paginate_history with no oldest must not send the param."""
    captured = {}

    def fake_slack_get(method: str, params: dict) -> dict:
        captured["params"] = params
        return {"messages": [], "response_metadata": {}}

    with patch.object(indexer.ingest, "_slack_get", side_effect=fake_slack_get):
        list(indexer.ingest.paginate_history("C-CEO"))
    assert "oldest" not in captured["params"]
