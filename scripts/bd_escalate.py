#!/usr/bin/env python3
"""bd_escalate.py — KEI-79 CLI for escalating a task to Dave via #ceo.

Two-write transaction: INSERT ceo_decisions row, UPDATE tasks SET status=
'escalated'. Then call direct_post.post_to_ceo with the escalation body.
On success, UPDATE ceo_decisions.slack_ts = response.ts. On Slack outage,
the direct_post helper enqueues a retry row in completion_sync_queue.

Rate limit: >=4 escalations from one callsign in 24h get
rate_limit_flagged=TRUE and a [RATE-LIMIT-EXCEEDED] prefix on the post
(soft cap per Max R1.1 — Dave sees the meta-signal).

KEI-72 Step-0 gate exemption: posts an [ESCALATION-INITIATED:<callsign>
:<task_id>] sentinel via slack_relay BEFORE the direct-post call so the
gate's allowlist recognizes the escalation as a Step-0 surrogate.

Usage:
    bd escalate <description> [--options A,B,C] [--task KEI-X] [--force]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess

RATE_LIMIT_PER_24H = 3


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def _callsign() -> str:
    return os.environ.get("CALLSIGN") or os.environ.get("TASKS_CALLSIGN") or "unknown"


def _resolve_task(cur, explicit: str | None, callsign: str) -> str:
    if explicit:
        return explicit
    cur.execute(
        "SELECT id FROM public.tasks WHERE claimed_by=%s AND status='active'",
        (callsign,),
    )
    rows = cur.fetchall()
    if len(rows) != 1:
        raise SystemExit(
            f"ERROR: cannot infer task — {len(rows)} active claim(s) for {callsign}; "
            "use --task KEI-X"
        )
    return rows[0][0]


def _rate_limit_check(cur, callsign: str, force: bool) -> bool:
    if force:
        return False
    cur.execute(
        "SELECT COUNT(*) FROM public.ceo_decisions "
        "WHERE escalated_by=%s AND requested_at > NOW() - INTERVAL '24 hours'",
        (callsign,),
    )
    return cur.fetchone()[0] >= RATE_LIMIT_PER_24H


def _emit_sentinel(callsign: str, task_id: str) -> None:
    relay = os.path.join(
        os.environ.get("AGENCY_OS_REPO", "/home/elliotbot/clawd/Agency_OS"),
        "scripts",
        "slack_relay.py",
    )
    if not os.path.isfile(relay):
        return
    text = f"[ESCALATION-INITIATED:{callsign}:{task_id}]"
    with contextlib.suppress(subprocess.TimeoutExpired, OSError):
        subprocess.run(
            ["python3", relay, "-g", text],
            env={**os.environ, "CALLSIGN": callsign},
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )


def _build_text(
    callsign: str, task_id: str, description: str, options: list[str] | None, flagged: bool
) -> str:
    prefix = "[RATE-LIMIT-EXCEEDED] " if flagged else ""
    head = f"{prefix}[ESCALATION:{callsign}] {task_id} — {description}"
    if options:
        opts = "\n".join(f"  {chr(65 + i)}) {o.strip()}" for i, o in enumerate(options))
        return f"{head}\nOptions:\n{opts}\nReply with letter (A/B/C…) or free-form."
    return f"{head}\nReply with decision text."


def _format_options(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [o.strip() for o in raw.split(",") if o.strip()]


def escalate(args: argparse.Namespace) -> int:
    import psycopg

    callsign = _callsign()
    options = _format_options(args.options)
    with psycopg.connect(_dsn(), prepare_threshold=None, autocommit=False) as conn:
        with conn.cursor() as cur:
            task_id = _resolve_task(cur, args.task, callsign)
            flagged = _rate_limit_check(cur, callsign, args.force)
            cur.execute(
                "INSERT INTO public.ceo_decisions "
                "(task_id, escalated_by, description, options, rate_limit_flagged) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (task_id, callsign, args.description, options, flagged),
            )
            decision_id = str(cur.fetchone()[0])
            cur.execute(
                "UPDATE public.tasks SET status='escalated', updated_at=NOW() WHERE id=%s",
                (task_id,),
            )
        conn.commit()

    _emit_sentinel(callsign, task_id)

    from src.slack_bot.direct_post import post_to_ceo

    text = _build_text(callsign, task_id, args.description, options, flagged)
    result = post_to_ceo(text, ceo_decision_id=decision_id)

    if result["ok"] and result.get("ts"):
        with (
            psycopg.connect(_dsn(), prepare_threshold=None, autocommit=True) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                "UPDATE public.ceo_decisions SET slack_ts=%s, updated_at=NOW() WHERE id=%s",
                (result["ts"], decision_id),
            )

    print(
        json.dumps(
            {
                "decision_id": decision_id,
                "task_id": task_id,
                "post_status": result["status"],
                "rate_limit_flagged": flagged,
            }
        )
    )
    return 0 if result["ok"] or result["status"] == "queued_retry" else 1


def main() -> int:
    p = argparse.ArgumentParser(prog="bd escalate")
    p.add_argument("description", help="one-line escalation context (<=200 chars)")
    p.add_argument("--options", help="comma-separated options (A,B,C)")
    p.add_argument("--task", help="explicit task id; defaults to active claim")
    p.add_argument("--force", action="store_true", help="bypass rate limit")
    args = p.parse_args()
    return escalate(args)


if __name__ == "__main__":
    raise SystemExit(main())
