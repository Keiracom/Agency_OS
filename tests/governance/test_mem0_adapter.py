"""
tests/governance/test_mem0_adapter.py — hermetic unit tests for Mem0Adapter.

All tests mock the mem0 SDK via sys.modules — no live API calls, no install needed.
"""

import importlib
import json
import os
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stub_mem0_module(mock_client_instance: MagicMock) -> ModuleType:
    """Return a fake 'mem0' module with MemoryClient returning mock_client_instance."""
    stub = ModuleType("mem0")
    stub.MemoryClient = MagicMock(return_value=mock_client_instance)
    return stub


def _load_mod_with_mock_client(log_path: str):
    """Reload src.governance.mem0_adapter with mem0 stubbed out.

    Returns (module, mock_client_instance).
    """
    mock_client = MagicMock()
    mock_client.add.return_value = {"id": "mem-abc123", "status": "ok"}
    mock_client.search.return_value = [
        {"id": "mem-xyz", "memory": "test memory content", "score": 0.91}
    ]
    mock_client.delete.return_value = {"deleted": True}
    mock_client.update.return_value = {"updated": True}

    stub_module = _stub_mem0_module(mock_client)

    # Inject stub before import
    sys.modules["mem0"] = stub_module

    # Force reload so the module picks up our env + stub
    if "src.governance.mem0_adapter" in sys.modules:
        del sys.modules["src.governance.mem0_adapter"]

    mod = importlib.import_module("src.governance.mem0_adapter")
    mod.MEM0_USAGE_LOG = log_path  # redirect log to temp file
    return mod, mock_client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def cleanup_mem0_stub():
    """Remove mem0 stub from sys.modules after each test."""
    yield
    sys.modules.pop("mem0", None)
    sys.modules.pop("src.governance.mem0_adapter", None)


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "mem0-usage.jsonl")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_add_writes_to_mem0_and_logs(log_path, monkeypatch):
    """add() calls client.add and appends an 'add' entry to usage log."""
    monkeypatch.setenv("MEM0_API_KEY", "test-key-12345")
    mod, mock_client = _load_mod_with_mock_client(log_path)

    adapter = mod.Mem0Adapter()

    result = adapter.add("test content", {"key": "val"}, callsign="aiden", source_type="decision")

    mock_client.add.assert_called_once()
    call_args = mock_client.add.call_args
    assert call_args[0][0] == [{"role": "user", "content": "test content"}]
    assert call_args[1]["user_id"] == "aiden"
    assert call_args[1]["metadata"]["source_type"] == "decision"

    with open(log_path) as fh:
        entries = [json.loads(line) for line in fh if line.strip()]
    add_entries = [e for e in entries if e["op"] == "add"]
    assert len(add_entries) >= 1
    assert add_entries[-1]["callsign"] == "aiden"
    assert add_entries[-1]["count"] == 1


def test_search_queries_mem0_and_logs(log_path, monkeypatch):
    """search() calls client.search and appends a 'search' entry to usage log."""
    monkeypatch.setenv("MEM0_API_KEY", "test-key-12345")
    mod, mock_client = _load_mod_with_mock_client(log_path)

    adapter = mod.Mem0Adapter()
    results = adapter.search("pipeline decision", limit=3, callsign="elliot")

    mock_client.search.assert_called_once_with("pipeline decision", filters={"user_id": "elliot"}, limit=3)
    assert isinstance(results, list)
    assert results[0]["memory"] == "test memory content"

    with open(log_path) as fh:
        entries = [json.loads(line) for line in fh if line.strip()]
    search_entries = [e for e in entries if e["op"] == "search"]
    assert len(search_entries) >= 1
    assert search_entries[-1]["callsign"] == "elliot"


def test_get_monthly_usage_reads_jsonl(log_path, monkeypatch):
    """get_monthly_usage() sums adds and searches for the current month."""
    monkeypatch.setenv("MEM0_API_KEY", "test-key-12345")
    mod, _ = _load_mod_with_mock_client(log_path)

    period = "2026-05"
    sample_entries = [
        {"ts": "2026-05-01T10:00:00+00:00", "op": "add", "callsign": "aiden", "count": 1},
        {"ts": "2026-05-01T10:01:00+00:00", "op": "add", "callsign": "elliot", "count": 1},
        {"ts": "2026-05-01T10:02:00+00:00", "op": "search", "callsign": "aiden", "count": 1},
        {"ts": "2026-04-30T23:59:00+00:00", "op": "add", "callsign": "aiden", "count": 1},  # prior month
    ]
    with open(log_path, "w") as fh:
        for e in sample_entries:
            fh.write(json.dumps(e) + "\n")

    usage = mod.get_monthly_usage(period=period)
    assert usage["adds"] == 2
    assert usage["searches"] == 1
    assert usage["period"] == period


def test_cap_warning_fires_at_80_percent_add(log_path, monkeypatch, caplog):
    """Cap warning logged when monthly adds reach 8000."""
    monkeypatch.setenv("MEM0_API_KEY", "test-key-12345")
    mod, _ = _load_mod_with_mock_client(log_path)

    period = "2026-05"
    with open(log_path, "w") as fh:
        fh.write(json.dumps(
            {"ts": f"{period}-01T00:00:00+00:00", "op": "add", "callsign": "aiden", "count": 8000}
        ) + "\n")

    import logging
    with caplog.at_level(logging.WARNING, logger="src.governance.mem0_adapter"):
        mod._check_caps("add")

    assert any("CAP WARNING" in r.message for r in caplog.records)


def test_cap_warning_fires_at_80_percent_search(log_path, monkeypatch, caplog):
    """Cap warning logged when monthly searches reach 800."""
    monkeypatch.setenv("MEM0_API_KEY", "test-key-12345")
    mod, _ = _load_mod_with_mock_client(log_path)

    period = "2026-05"
    with open(log_path, "w") as fh:
        fh.write(json.dumps(
            {"ts": f"{period}-01T00:00:00+00:00", "op": "search", "callsign": "elliot", "count": 800}
        ) + "\n")

    import logging
    with caplog.at_level(logging.WARNING, logger="src.governance.mem0_adapter"):
        mod._check_caps("search")

    assert any("CAP WARNING" in r.message for r in caplog.records)


def test_missing_api_key_raises(monkeypatch):
    """Mem0Adapter raises EnvironmentError when MEM0_API_KEY is not set."""
    monkeypatch.delenv("MEM0_API_KEY", raising=False)

    sys.modules.pop("src.governance.mem0_adapter", None)
    mod = importlib.import_module("src.governance.mem0_adapter")

    with pytest.raises(EnvironmentError, match="MEM0_API_KEY"):
        mod.Mem0Adapter()
