"""tests for scripts/wave1_retire_mem0.py — Wave 1 Item 3 mem0 retirement.

mem0 SDK + asyncpg mocked. Filesystem isolated. No live calls.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "wave1_retire_mem0.py"


@pytest.fixture(scope="module")
def retire_mod():
    spec = importlib.util.spec_from_file_location("wave1_retire_mem0", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wave1_retire_mem0"] = mod
    spec.loader.exec_module(mod)
    return mod


# infer_callsign ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "content,expected",
    [
        ("Elliot ran the deploy", "elliot"),
        ("Aiden wrote the test", "aiden"),
        ("Max merged the PR", "max"),
        ("Atlas did the install", "atlas"),
        ("ORION is offline", "orion"),
        ("Scout researched X", "scout"),
        ("no known names here", "unknown"),
    ],
)
def test_infer_callsign_matches_known(retire_mod, content, expected) -> None:
    assert retire_mod.infer_callsign(content) == expected


def test_infer_callsign_falls_back_to_provided(retire_mod) -> None:
    assert retire_mod.infer_callsign("nothing", fallback="custom") == "custom"


def test_infer_callsign_empty_content(retire_mod) -> None:
    assert retire_mod.infer_callsign("", fallback="x") == "x"


def test_infer_callsign_lowercases(retire_mod) -> None:
    assert retire_mod.infer_callsign("ELLIOT did it") == "elliot"


# build_agent_memory_row ─────────────────────────────────────────────────────


def test_build_row_uses_memory_field(retire_mod) -> None:
    mem0_row = {"id": "m1", "user_id": "abc", "memory": "Elliot fixed it"}
    row = retire_mod.build_agent_memory_row(mem0_row)
    assert row is not None
    assert row["callsign"] == "elliot"
    assert row["content"] == "Elliot fixed it"
    assert row["source_type"] == "rescued_from_mem0"
    assert row["typed_metadata"]["node_set"] == ["rescued", "mem0_migration"]
    assert row["typed_metadata"]["mem0_original_user_id"] == "abc"
    assert row["typed_metadata"]["mem0_id"] == "m1"
    assert row["state"] == "confirmed"


def test_build_row_falls_back_to_text_field(retire_mod) -> None:
    mem0_row = {"id": "m2", "user_id": "u", "text": "Aiden testing"}
    row = retire_mod.build_agent_memory_row(mem0_row)
    assert row is not None
    assert row["content"] == "Aiden testing"


def test_build_row_returns_none_on_empty_content(retire_mod) -> None:
    assert retire_mod.build_agent_memory_row({"id": "m3", "user_id": "x"}) is None
    assert retire_mod.build_agent_memory_row({"id": "m4", "memory": ""}) is None


def test_build_row_no_known_callsign_falls_back_to_mem0_user_id(retire_mod) -> None:
    mem0_row = {"id": "m5", "user_id": "custom_user", "memory": "no callsign here"}
    row = retire_mod.build_agent_memory_row(mem0_row)
    assert row["callsign"] == "custom_user"


# fetch_mem0_memories ────────────────────────────────────────────────────────


def test_fetch_no_api_key(retire_mod, monkeypatch) -> None:
    monkeypatch.delenv("MEM0_API_KEY", raising=False)
    # Stub the SDK so the ImportError path isn't reached
    fake_module = MagicMock()
    monkeypatch.setitem(sys.modules, "mem0", fake_module)
    assert retire_mod.fetch_mem0_memories() == []


def test_fetch_paginates_per_user_id_and_dedupes(retire_mod, monkeypatch) -> None:
    """fetch_mem0_memories iterates MEM0_FILTER_USER_IDS, dedupes by id, stops
    on short batch per filter."""
    monkeypatch.setenv("MEM0_API_KEY", "test-key")
    fake_client = MagicMock()

    def get_all(filters, page, page_size):
        user_id = filters.get("user_id")
        if user_id == "elliot" and page == 1:
            return [{"id": "shared_1", "memory": "x"}, {"id": "el_only", "memory": "x"}]
        if user_id == "max" and page == 1:
            # shared_1 should be deduped; max_only is new
            return [{"id": "shared_1", "memory": "x"}, {"id": "max_only", "memory": "x"}]
        # All other user_ids return empty (short batch → break)
        return []

    fake_client.get_all.side_effect = get_all
    fake_module = MagicMock()
    fake_module.MemoryClient.return_value = fake_client
    monkeypatch.setitem(sys.modules, "mem0", fake_module)

    rows = retire_mod.fetch_mem0_memories(page_size=100)
    ids = [r["id"] for r in rows]
    assert ids == ["shared_1", "el_only", "max_only"]  # deduped + insertion-ordered


def test_fetch_respects_limit(retire_mod, monkeypatch) -> None:
    monkeypatch.setenv("MEM0_API_KEY", "k")
    fake_client = MagicMock()
    fake_client.get_all.return_value = [{"id": f"m{i}", "memory": "x"} for i in range(100)]
    fake_module = MagicMock()
    fake_module.MemoryClient.return_value = fake_client
    monkeypatch.setitem(sys.modules, "mem0", fake_module)

    rows = retire_mod.fetch_mem0_memories(page_size=100, limit=5)
    assert len(rows) == 5


def test_fetch_swallows_sdk_errors(retire_mod, monkeypatch) -> None:
    monkeypatch.setenv("MEM0_API_KEY", "k")
    fake_client = MagicMock()
    fake_client.get_all.side_effect = RuntimeError("network blip")
    fake_module = MagicMock()
    fake_module.MemoryClient.return_value = fake_client
    monkeypatch.setitem(sys.modules, "mem0", fake_module)

    assert retire_mod.fetch_mem0_memories() == []


# main CLI ──────────────────────────────────────────────────────────────────


def test_main_dry_run_default(retire_mod, monkeypatch) -> None:
    """Default invocation is dry-run; never reaches DB."""
    monkeypatch.setenv("MEM0_API_KEY", "k")
    fake_module = MagicMock()
    fake_client = MagicMock()
    fake_client.get_all.return_value = [{"id": "a", "memory": "Aiden", "user_id": "old"}]
    fake_module.MemoryClient.return_value = fake_client
    monkeypatch.setitem(sys.modules, "mem0", fake_module)

    result = retire_mod.main([])
    assert result == 0


def test_main_execute_requires_database_url(retire_mod, monkeypatch) -> None:
    """--execute without DSN returns 1 (all fail) but doesn't crash."""
    monkeypatch.setenv("MEM0_API_KEY", "k")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    fake_module = MagicMock()
    fake_client = MagicMock()
    fake_client.get_all.return_value = [{"id": "a", "memory": "Aiden", "user_id": "u"}]
    fake_module.MemoryClient.return_value = fake_client
    monkeypatch.setitem(sys.modules, "mem0", fake_module)

    result = retire_mod.main(["--execute"])
    assert result == 1


def test_main_empty_mem0_dry_run_returns_zero(retire_mod, monkeypatch) -> None:
    """Empty mem0 → no payloads → dry-run still returns 0."""
    monkeypatch.setenv("MEM0_API_KEY", "k")
    fake_module = MagicMock()
    fake_client = MagicMock()
    fake_client.get_all.return_value = []
    fake_module.MemoryClient.return_value = fake_client
    monkeypatch.setitem(sys.modules, "mem0", fake_module)

    assert retire_mod.main([]) == 0
