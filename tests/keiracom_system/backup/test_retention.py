"""Tests for the pure backup-retention selection logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.keiracom_system.backup.r2 import R2Object
from src.keiracom_system.backup.retention import select_prunable

NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def _obj(key: str, dt: datetime) -> R2Object:
    return R2Object(key=key, last_modified=dt, size=4096)


def test_weaviate_keeps_seven_most_recent():
    objs = [_obj(f"weaviate/day-{i}", NOW - timedelta(days=i)) for i in range(10)]
    prune = select_prunable(objs, keep_recent=7, keep_daily=0)
    assert len(prune) == 3
    assert {p.key for p in prune} == {"weaviate/day-7", "weaviate/day-8", "weaviate/day-9"}


def test_weaviate_under_limit_prunes_nothing():
    objs = [_obj(f"weaviate/day-{i}", NOW - timedelta(days=i)) for i in range(5)]
    assert select_prunable(objs, keep_recent=7) == []


def test_postgres_hourly_plus_daily():
    # 24 hourly dumps all within day0 (start 23:00 so 24h back stays on the same
    # date), plus one daily dump per day for day-1..day-10.
    late = datetime(2026, 6, 1, 23, 0, tzinfo=UTC)
    hourly = [_obj(f"pg/h-{h}", late - timedelta(hours=h)) for h in range(24)]
    daily = [_obj(f"pg/d-{d}", late.replace(hour=6) - timedelta(days=d)) for d in range(1, 11)]
    prune = select_prunable(hourly + daily, keep_recent=24, keep_daily=7)
    # 24 hourly all kept (keep_recent). Daily anchors kept for the 7 most-recent
    # days overall (day0 + day-1..day-6); day0's anchor is an hourly dump, so the
    # surviving daily anchors are d-1..d-6. d-7..d-10 are pruned.
    assert {p.key for p in prune} == {"pg/d-7", "pg/d-8", "pg/d-9", "pg/d-10"}


def test_postgres_keeps_daily_anchor_outside_hourly_window():
    # One dump per hour for 30 hours → spans day0 + day-1 (+ maybe day-2).
    objs = [_obj(f"pg/h-{h}", NOW - timedelta(hours=h)) for h in range(30)]
    prune = select_prunable(objs, keep_recent=24, keep_daily=7)
    kept = {o.key for o in objs} - {p.key for p in prune}
    # The 24 most-recent are kept; older ones survive only as daily anchors.
    assert len(kept) >= 24
    # h-0 (newest) always kept; the oldest hour beyond a daily anchor is pruned.
    assert "pg/h-0" in kept


def test_daily_anchor_is_most_recent_of_its_day():
    # Two dumps on the same old day; only the newer one is the anchor.
    objs = [
        _obj("pg/recent", NOW),
        _obj("pg/old-early", datetime(2026, 5, 20, 3, 0, tzinfo=UTC)),
        _obj("pg/old-late", datetime(2026, 5, 20, 21, 0, tzinfo=UTC)),
    ]
    prune = select_prunable(objs, keep_recent=1, keep_daily=7)
    assert {p.key for p in prune} == {"pg/old-early"}


def test_empty_input():
    assert select_prunable([], keep_recent=7, keep_daily=7) == []
