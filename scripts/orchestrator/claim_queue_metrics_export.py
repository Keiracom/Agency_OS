"""claim_queue_metrics_export.py — KEI-136 Better Stack heartbeat exporter.

Reads `public.claim_queue_metrics_v` and pings the Better Stack heartbeat URL
when the queue is healthy. Skipping the heartbeat is the alert signal: Better
Stack fires when no heartbeat arrives within `period + grace` (configured on
the BS side at heartbeat creation — see HEARTBEATS in betterstack_setup.py).

Run via systemd timer every 60 seconds:
    systemd/claim_queue_metrics.service + .timer
    scripts/install_claim_queue_metrics.sh

Stall criteria (any one ⇒ skip heartbeat ⇒ BS alert fires after grace):
    available_count > 0 AND oldest_available_age_sec > STALL_THRESHOLD_SEC
        — work waiting unclaimed past the SLA.
    max_idle_seconds NOT NULL AND max_idle_seconds > STALL_THRESHOLD_SEC
        — an active task hasn't heartbeated in over SLA.

NULL `max_idle_seconds` (no heartbeat data on any active row) is fail-open —
NOT treated as stall — because `tasks.heartbeat_at` is currently unpopulated
in production; turning that into an alert would page on baseline state.

Env contract:
    CLAIM_QUEUE_HEARTBEAT_URL — Better Stack heartbeat URL. If unset, the
        exporter logs a warning and exits cleanly (no fail-loud).
    DATABASE_URL / SUPABASE_DB_URL — Postgres DSN (psycopg3, +asyncpg stripped).
    CLAIM_QUEUE_STALL_THRESHOLD_SEC — override default 300s if needed.
"""

from __future__ import annotations

import logging
import os
import urllib.request

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DEFAULT_STALL_THRESHOLD_SEC = 300


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def fetch_metrics() -> dict:
    """Read one row from claim_queue_metrics_v. Returns dict with named columns."""
    import psycopg

    with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT available_count, active_count, blocked_count,
                   oldest_available_age_sec, oldest_active_age_sec,
                   max_idle_seconds
              FROM public.claim_queue_metrics_v
            """
        )
        row = cur.fetchone()
    if row is None:
        return {}
    return {
        "available_count": row[0] or 0,
        "active_count": row[1] or 0,
        "blocked_count": row[2] or 0,
        "oldest_available_age_sec": row[3],
        "oldest_active_age_sec": row[4],
        "max_idle_seconds": row[5],
    }


def is_stalled(metrics: dict, threshold_sec: int) -> tuple[bool, str]:
    """Return (stalled, reason). Reason is empty when healthy."""
    available = metrics.get("available_count", 0) or 0
    oldest_avail = metrics.get("oldest_available_age_sec")
    max_idle = metrics.get("max_idle_seconds")

    if available > 0 and oldest_avail is not None and oldest_avail > threshold_sec:
        return True, (
            f"available work aging past SLA: oldest_available_age_sec={oldest_avail} "
            f"> threshold={threshold_sec}"
        )
    if max_idle is not None and max_idle > threshold_sec:
        return (
            True,
            f"active task idle past SLA: max_idle_seconds={max_idle} > threshold={threshold_sec}",
        )
    return False, ""


def post_heartbeat(url: str) -> bool:
    """GET the BS heartbeat URL. Returns True on 2xx, False otherwise.

    BS heartbeats accept GET or POST; GET is the documented norm. We treat any
    non-2xx as failure but do not raise — exporter logs and continues so the
    timer keeps firing.
    """
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except OSError as exc:
        logger.warning("heartbeat POST failed: %s", exc)
        return False


def main() -> None:
    heartbeat_url = os.environ.get("CLAIM_QUEUE_HEARTBEAT_URL", "")
    if not heartbeat_url:
        logger.warning(
            "CLAIM_QUEUE_HEARTBEAT_URL unset — exporter exiting clean. "
            "Set it after Better Stack heartbeat creation (see runbook)."
        )
        return

    threshold = int(
        os.environ.get("CLAIM_QUEUE_STALL_THRESHOLD_SEC", str(DEFAULT_STALL_THRESHOLD_SEC))
    )

    try:
        metrics = fetch_metrics()
    except Exception as exc:
        logger.warning("fetch_metrics failed (skipping heartbeat — DB unreachable): %s", exc)
        return

    stalled, reason = is_stalled(metrics, threshold)
    if stalled:
        logger.warning(
            "queue stalled — SKIPPING heartbeat (BS will alert after grace). %s. metrics=%s",
            reason,
            metrics,
        )
        return

    ok = post_heartbeat(heartbeat_url)
    logger.info(
        "heartbeat %s — metrics=%s",
        "ok" if ok else "failed",
        metrics,
    )


if __name__ == "__main__":
    main()
