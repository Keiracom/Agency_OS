"""discovery_log.py — KEI-63 deprecation primitive over discovery_log.jsonl.

Provides the load / append / deprecate operations over the jsonl discovery
store at ~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/
discovery_log.jsonl. KEI-50 module documents this as the interim canonical
store until KEI-46+47 ship the Weaviate retrieval pipeline.

Once KEI-46+47 land, the deprecated field stays on each row; migration to
Weaviate is row-wise (preserving the field). Per Elliot's KEI-63 dispatch
note 2026-05-14: keep deprecation composable with the future Weaviate store.

Acceptance criterion (KEI-63 verbatim from tasks-table):
    bd deprecate on an existing discovery marks it invalid. It no longer
    surfaces in bd claim injections.

Public API:
    load_all_discoveries() -> list[dict]      # raw all rows including deprecated
    load_active_discoveries() -> list[dict]   # filter out deprecated=True
    append_discovery(entry: dict) -> None     # write a new row
    mark_deprecated(kei: str, reason: str, by: str) -> dict  # mutate row
    compute_freshness(row, now=None) -> dict  # KEI-58 — fresh|stale|expired + reason
    load_fresh_discoveries() -> list[dict]    # KEI-58 — active AND not expired
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from scripts.orchestrator.context_version import context_drift, current_context_version

STALE_AGE = timedelta(days=30)
EXPIRED_AGE = timedelta(days=90)

DEFAULT_DISCOVERY_LOG = Path(
    os.environ.get(
        "AGENCY_OS_DISCOVERY_LOG",
        os.path.expanduser(
            "~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/discovery_log.jsonl"
        ),
    )
)


class DiscoveryLogError(RuntimeError):
    """Raised on read/write/deprecation failure or when the target row is missing."""


def _utcnow_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_all_discoveries(path: Path | None = None) -> list[dict[str, Any]]:
    """Return every row in the jsonl, deprecated or not. Empty list if file missing."""
    path = path or DEFAULT_DISCOVERY_LOG
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                raise DiscoveryLogError(f"malformed jsonl at {path}:{lineno}: {exc}") from exc
    return rows


def load_active_discoveries(path: Path | None = None) -> list[dict[str, Any]]:
    """Subset excluding rows with deprecated=True. Caller for bd claim injection."""
    return [r for r in load_all_discoveries(path) if not r.get("deprecated", False)]


def append_discovery(entry: dict[str, Any], path: Path | None = None) -> None:
    """Append one entry to the jsonl. Creates the file + parent dir if missing.

    Does not validate schema beyond requiring `kei` to be a non-empty string —
    the v2 format check belongs upstream in bd discover (KEI-50 build phase).
    """
    if not entry.get("kei"):
        raise DiscoveryLogError(f"entry missing required 'kei' field: {entry!r}")
    path = path or DEFAULT_DISCOVERY_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def mark_deprecated(
    kei: str,
    reason: str,
    by: str,
    path: Path | None = None,
    *,
    now: str | None = None,
) -> dict[str, Any]:
    """Mark the most recent row with this kei as deprecated. Idempotent re-mark
    updates reason+timestamp; raises DiscoveryLogError if no row matches.

    Returns the deprecated row dict (post-mutation). One-way operation —
    there is no un-deprecate verb. To revert, the operator manually edits
    the jsonl or appends a new non-deprecated discovery.
    """
    if not kei:
        raise DiscoveryLogError("kei must be a non-empty string")
    if not reason:
        raise DiscoveryLogError("reason must be a non-empty string")
    path = path or DEFAULT_DISCOVERY_LOG
    rows = load_all_discoveries(path)
    if not rows:
        raise DiscoveryLogError(f"discovery_log empty or missing: {path}")

    target_idx: int | None = None
    for i in range(len(rows) - 1, -1, -1):
        if rows[i].get("kei") == kei:
            target_idx = i
            break
    if target_idx is None:
        raise DiscoveryLogError(f"no discovery row with kei={kei!r} found")

    rows[target_idx]["deprecated"] = True
    rows[target_idx]["deprecated_reason"] = reason
    rows[target_idx]["deprecated_by"] = by
    rows[target_idx]["deprecated_at"] = now or _utcnow_iso()

    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    tmp.replace(path)
    return rows[target_idx]


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def compute_freshness(
    row: dict[str, Any],
    now: datetime | None = None,
    *,
    current_version: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a discovery row's freshness. Returns {verdict, reason, age_days, drift}.

    Rule (KEI-58, 30/90 ratified by Elliot ts ~1778899332):
      EXPIRED if age > 90d (regardless of context drift — old lessons rot).
      STALE   if age > 30d OR any context_version field differs from current.
      FRESH   otherwise.
    Verdict precedence: EXPIRED beats STALE beats FRESH.
    """
    now = now or datetime.now(UTC)
    current_version = current_version if current_version is not None else current_context_version()
    written_at = _parse_iso(row.get("created_at") or row.get("written_at") or "")
    age = now - written_at if written_at else timedelta.max
    age_days = age.days if age != timedelta.max else None
    drift = context_drift(row.get("context_version"), current_version)
    if age >= EXPIRED_AGE:
        return {"verdict": "expired", "reason": f"age {age_days}d >= 90d", "age_days": age_days, "drift": drift}
    if age >= STALE_AGE:
        return {"verdict": "stale", "reason": f"age {age_days}d >= 30d", "age_days": age_days, "drift": drift}
    if drift:
        return {"verdict": "stale", "reason": f"context drift on {drift}", "age_days": age_days, "drift": drift}
    return {"verdict": "fresh", "reason": "within 30d and context unchanged", "age_days": age_days, "drift": []}


def load_fresh_discoveries(path: Path | None = None) -> list[dict[str, Any]]:
    """Active rows minus EXPIRED. STALE retained but tagged via `_freshness` key.

    Caller for bd recall + future bd claim auto-injection (KEI-51): exclude
    EXPIRED entirely; surface STALE with the freshness tag so the UI can badge.
    """
    current = current_context_version()
    out: list[dict[str, Any]] = []
    for row in load_active_discoveries(path):
        f = compute_freshness(row, current_version=current)
        if f["verdict"] == "expired":
            continue
        row["_freshness"] = f
        out.append(row)
    return out
