"""retention.py — pure backup-retention selection.

Two policies, one function:
  * Weaviate daily: keep the N most-recent snapshots (keep_recent=7, keep_daily=0).
  * Postgres hourly+daily: keep the 24 most-recent dumps AND a daily anchor (the
    most-recent dump of each day) for the 7 most-recent days
    (keep_recent=24, keep_daily=7).

`select_prunable` returns the objects to delete. Pure — no I/O — so the prune
math is unit-tested without touching R2.
"""

from __future__ import annotations

from datetime import UTC


def select_prunable(
    objects: list,
    *,
    keep_recent: int,
    keep_daily: int = 0,
) -> list:
    """Return objects to prune given a most-recent window + optional daily anchors.

    Keeps the `keep_recent` newest objects; additionally keeps one anchor per day
    (the newest object of that day) for the `keep_daily` most-recent days.
    Everything else is returned for deletion.
    """
    newest_first = sorted(objects, key=lambda o: o.last_modified, reverse=True)
    keep_keys = {o.key for o in newest_first[:keep_recent]}

    if keep_daily > 0:
        anchor_by_day: dict = {}
        for obj in newest_first:  # newest-first → first seen per day is the anchor
            day = obj.last_modified.astimezone(UTC).date()
            anchor_by_day.setdefault(day, obj)
        for day in sorted(anchor_by_day, reverse=True)[:keep_daily]:
            keep_keys.add(anchor_by_day[day].key)

    return [o for o in newest_first if o.key not in keep_keys]
