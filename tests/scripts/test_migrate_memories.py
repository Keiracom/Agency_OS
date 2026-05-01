"""
Tests for scripts/migrate_memories.py.

Pure mocks — no database connections. Verifies:
  - dry-run makes no execute() calls
  - deduplication skips rows whose content already exists
  - field mapping: type→source_type, metadata→typed_metadata
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "migrate_memories.py"
_spec = importlib.util.spec_from_file_location("migrate_memories", _SCRIPT)
migrate = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["migrate_memories"] = migrate
_spec.loader.exec_module(migrate)


# ── helpers ────────────────────────────────────────────────────────────────

def _legacy_row(**kwargs) -> dict:
    defaults = {
        "id": "abc123",
        "type": "daily_log",
        "content": "Session ended ok.",
        "metadata": {"key": "val"},
        "created_at": None,
    }
    return {**defaults, **kwargs}


# ── test_dry_run_no_writes ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dry_run_no_writes():
    """In dry-run mode _insert_row must never be called."""
    rows = [_legacy_row(content="row one"), _legacy_row(content="row two")]

    async def fake_fetch_legacy(_conn):
        return rows

    async def fake_fetch_existing(_conn):
        return set()  # nothing pre-exists → would migrate both

    insert_calls = []

    async def fake_insert(_conn, mapped):
        insert_calls.append(mapped)

    with (
        patch.object(migrate, "_fetch_legacy", fake_fetch_legacy),
        patch.object(migrate, "_fetch_existing_contents", fake_fetch_existing),
        patch.object(migrate, "_insert_row", fake_insert),
        patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect,
    ):
        fake_conn = AsyncMock()
        mock_connect.return_value = fake_conn

        counts = await migrate._migrate("postgresql://fake", execute=False)

    # dry-run: migrated counter increments but insert never fires
    assert insert_calls == [], "insert must NOT be called in dry-run"
    assert counts["migrated"] == 2
    assert counts["skipped"] == 0
    assert counts["errors"] == 0


# ── test_dedup_skips_existing ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dedup_skips_existing():
    """Rows whose content is already in agent_memories are skipped."""
    existing_content = "Already in target table."
    rows = [
        _legacy_row(content=existing_content),
        _legacy_row(content="Brand new row."),
    ]

    async def fake_fetch_legacy(_conn):
        return rows

    async def fake_fetch_existing(_conn):
        return {existing_content}

    insert_calls = []

    async def fake_insert(_conn, mapped):
        insert_calls.append(mapped["content"])

    with (
        patch.object(migrate, "_fetch_legacy", fake_fetch_legacy),
        patch.object(migrate, "_fetch_existing_contents", fake_fetch_existing),
        patch.object(migrate, "_insert_row", fake_insert),
        patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect,
    ):
        fake_conn = AsyncMock()
        mock_connect.return_value = fake_conn

        counts = await migrate._migrate("postgresql://fake", execute=True)

    assert counts["skipped"] == 1, "pre-existing row must be skipped"
    assert counts["migrated"] == 1, "new row must be migrated"
    assert insert_calls == ["Brand new row."]


# ── test_field_mapping ─────────────────────────────────────────────────────

def test_field_mapping_type_to_source_type():
    """_map_row must copy type → source_type."""
    row = _legacy_row(type="core_fact")
    mapped = migrate._map_row(row)
    assert mapped["source_type"] == "core_fact"
    assert "type" not in mapped


def test_field_mapping_metadata_to_typed_metadata():
    """_map_row must copy metadata → typed_metadata as dict."""
    row = _legacy_row(metadata={"directive": 42})
    mapped = migrate._map_row(row)
    assert mapped["typed_metadata"] == {"directive": 42}
    assert "metadata" not in mapped


def test_field_mapping_string_metadata_parsed():
    """_map_row must JSON-parse string metadata."""
    row = _legacy_row(metadata='{"foo": "bar"}')
    mapped = migrate._map_row(row)
    assert mapped["typed_metadata"] == {"foo": "bar"}


def test_field_mapping_callsign_fixed():
    """callsign must always be 'elliot' for legacy rows."""
    row = _legacy_row()
    mapped = migrate._map_row(row)
    assert mapped["callsign"] == "elliot"


def test_field_mapping_state_confirmed():
    """Migrated rows must land in 'confirmed' state."""
    mapped = migrate._map_row(_legacy_row())
    assert mapped["state"] == "confirmed"
