"""GOV-PHASE2 Auditor — phoenix_export_loop tests."""
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import scripts.phoenix_export_loop as loop


@pytest.fixture
def tmp_watermark(tmp_path, monkeypatch):
    p = tmp_path / "phoenix_watermark.txt"
    monkeypatch.setattr(loop, "WATERMARK_PATH", p)
    return p


def test_read_watermark_default_when_missing(tmp_watermark):
    ts = loop.read_watermark()
    delta = datetime.now(UTC) - ts
    assert 3300 < delta.total_seconds() < 3700  # ~1h ago


def test_read_watermark_round_trip(tmp_watermark):
    sample = datetime(2026, 5, 1, 13, 0, 0, tzinfo=UTC)
    loop.write_watermark(sample)
    assert tmp_watermark.exists()
    assert loop.read_watermark() == sample


def test_read_watermark_handles_garbage(tmp_watermark):
    tmp_watermark.write_text("not-a-timestamp", encoding="utf-8")
    ts = loop.read_watermark()
    assert (datetime.now(UTC) - ts).total_seconds() > 3000


@pytest.mark.asyncio
async def test_run_one_cycle_no_dsn(tmp_watermark, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    tracer = MagicMock()
    exported = await loop.run_one_cycle(tracer)
    assert exported == 0


@pytest.mark.asyncio
async def test_run_one_cycle_exports_and_advances_watermark(tmp_watermark, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    fake_events = [
        {"event_type": "tool_call", "callsign": "aiden",
         "timestamp": datetime(2026, 5, 1, 13, 0, 0, tzinfo=UTC),
         "event_data": {}, "tool_name": "Bash", "file_path": "",
         "directive_id": ""},
        {"event_type": "tool_call", "callsign": "aiden",
         "timestamp": datetime(2026, 5, 1, 13, 5, 0, tzinfo=UTC),
         "event_data": {}, "tool_name": "Read", "file_path": "",
         "directive_id": ""},
    ]
    tracer = MagicMock()
    with patch.object(loop, "fetch_events", new=AsyncMock(return_value=fake_events)), \
         patch("src.observability.phoenix_client.export_event", return_value=True) as mock_export:
        exported = await loop.run_one_cycle(tracer)
    assert exported == 2
    assert mock_export.call_count == 2
    assert loop.read_watermark() == datetime(2026, 5, 1, 13, 5, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_run_one_cycle_no_events_does_not_advance(tmp_watermark, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    initial = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    loop.write_watermark(initial)
    with patch.object(loop, "fetch_events", new=AsyncMock(return_value=[])):
        await loop.run_one_cycle(MagicMock())
    assert loop.read_watermark() == initial
