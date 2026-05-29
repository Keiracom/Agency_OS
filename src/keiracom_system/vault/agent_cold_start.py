"""agent_cold_start.py — ephemeral work-loop agent entrypoint (Agency_OS-yhm8 / 87ei).

The command the dispatcher runs (DISPATCHER_AGENT_COMMAND) INSIDE a scrubbed
``env -i`` tmux session: only VAULT_ADDR + VAULT_TOKEN + AGENT_* metadata are
inherited — no .env credentials (P10). Flow:

  1. resolve_into_env() — pull every fleet credential from Vault KV into os.environ
     (DATABASE_URL, ANTHROPIC_*, … are in SECRET_MANIFEST). The scrubbed env had
     none of these; this is the cold-start bootstrap.
  2. Resolve the task: AGENT_TASK_ID (or argv[1]) → fetch the public.tasks row.
  3. Claim it (available→active, auto_loop), compose a task-centric prompt, and
     spawn a FRESH headless ``claude`` subprocess (fresh-per-task V1, per
     docs/architecture/ephemeral_agent_system_scoping.md §4). Output flows to the
     tmux pane; the agent does the work and exits.
  4. Finalize the task lifecycle, then exit with the agent's return code.

Design decisions (Elliot-confirmed D1–D4, 2026-05-29):
  D1  self-composed task-centric prompt (NOT the callsign spawn_composer, which is
      inbox/callsign-centric and has no slot for a work-loop task brief).
  D2  headless ``claude -p <prompt> --dangerously-skip-permissions`` subprocess.
  D3  this entrypoint owns the public.tasks lifecycle (the consumer admits via a
      Valkey counter only and never touches status). rc 0 → 'done'.
  D4  a task_verifications row is ALWAYS inserted before 'done' — the
      require_verification_before_done trigger fires on every done transition and
      raises unless evidence exists, regardless of acceptance_criteria (Aiden catch).

NB: tasks_status_check has no 'failed' value, so a non-zero agent rc maps to
'blocked' (valid, needs-attention, not auto-retried) rather than 'failed'.

All external seams (resolve / fetch / claim / agent / finalize) are injectable so
the orchestration is unit-testable without Vault, a DB, or a real ``claude``.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from collections.abc import Callable
from typing import Any

from src.keiracom_system.vault.kv_resolver import resolve_into_env

logger = logging.getLogger(__name__)

AGENT_WORKDIR = os.environ.get("DISPATCHER_AGENT_WORKDIR", "/home/elliotbot/clawd/Agency_OS")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
_TASK_COLS = ("id", "title", "description", "task_type", "priority", "acceptance_criteria")

# Exit codes (distinct from a claude rc so the loop can tell apart cold-start
# failures from agent failures): 0 ok / claim-lost; 2 no task id; 3 task absent.
RC_NO_TASK_ID = 2
RC_TASK_ABSENT = 3


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_DSN")
    if not dsn:
        raise RuntimeError("agent_cold_start: DATABASE_URL absent after Vault resolve")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


def _connect() -> Any:
    import psycopg

    return psycopg.connect(_dsn(), connect_timeout=10, prepare_threshold=None, autocommit=True)


def fetch_task(task_id: str, *, conn: Any = None) -> dict | None:
    """Fetch the public.tasks row for task_id. None if absent."""
    own = conn is None
    conn = conn or _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, description, task_type, priority, acceptance_criteria "
                "FROM public.tasks WHERE id = %s",
                (task_id,),
            )
            row = cur.fetchone()
        return dict(zip(_TASK_COLS, row, strict=True)) if row else None
    finally:
        if own:
            conn.close()


def claim_task(task_id: str, callsign: str | None, *, conn: Any = None) -> bool:
    """Atomic available→active claim. True iff this agent won the claim."""
    own = conn is None
    conn = conn or _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.tasks SET status='active', claimed_at=now(), "
                "claim_source='auto_loop', claimed_by=COALESCE(%s, claimed_by) "
                "WHERE id=%s AND status='available'",
                (callsign, task_id),
            )
            return cur.rowcount == 1
    finally:
        if own:
            conn.close()


def compose_prompt(task: dict) -> str:
    """Task-centric initial prompt for the ephemeral worker (D1)."""
    parts = [
        "You are an ephemeral Keiracom worker agent. Do exactly this one task, "
        "then stop — do not wait for further input.",
        f"Task ID: {task['id']}",
        f"Title: {task.get('title') or '(none)'}",
        f"Type: {task.get('task_type') or 'build'}",
    ]
    if task.get("description"):
        parts.append(f"Description:\n{task['description']}")
    if task.get("acceptance_criteria"):
        parts.append(f"Acceptance criteria (must be met):\n{task['acceptance_criteria']}")
    parts.append("Complete the task end to end, then exit.")
    return "\n\n".join(parts)


def run_agent(prompt: str, *, popen: Callable[..., Any] = subprocess.Popen) -> int:
    """Spawn a fresh headless ``claude`` subprocess for this task (D2). Returns its rc."""
    cmd = [CLAUDE_BIN, "-p", prompt, "--dangerously-skip-permissions"]
    proc = popen(cmd, cwd=AGENT_WORKDIR)
    return proc.wait()


def finalize_task(
    task_id: str, rc: int, acceptance_criteria: str | None, *, conn: Any = None
) -> None:
    """rc 0 → 'done'; rc != 0 → 'blocked' (no 'failed' in tasks_status_check).

    On 'done', ALWAYS insert a task_verifications row first: the
    require_verification_before_done trigger fires on every done transition and
    raises unless evidence exists — acceptance_criteria NULL/empty does NOT bypass
    the gate (Aiden catch). Without this, a NULL-acceptance task crashes on the
    UPDATE and stays stuck 'active'.
    """
    own = conn is None
    conn = conn or _connect()
    status = "done" if rc == 0 else "blocked"
    try:
        with conn.cursor() as cur:
            if status == "done":
                test_output = (
                    f"claude rc=0 (acceptance: {acceptance_criteria[:300]})"
                    if acceptance_criteria
                    else "claude rc=0 (task ran to completion; no acceptance criteria)"
                )
                cur.execute(
                    "INSERT INTO public.task_verifications "
                    "(task_id, verified_by, behavioral_test, test_output) VALUES (%s,%s,%s,%s)",
                    (task_id, "agent_cold_start", "ephemeral agent ran to completion", test_output),
                )
            cur.execute("UPDATE public.tasks SET status=%s WHERE id=%s", (status, task_id))
    finally:
        if own:
            conn.close()


def run(
    *,
    resolve: Callable[..., Any] = resolve_into_env,
    fetch: Callable[..., dict | None] = fetch_task,
    claim: Callable[..., bool] = claim_task,
    agent: Callable[..., int] = run_agent,
    finalize: Callable[..., None] = finalize_task,
) -> int:
    """Cold-start orchestration. Returns the process exit code."""
    logging.basicConfig(level=logging.INFO)
    resolve()  # Vault bootstrap → fleet creds in os.environ
    task_id = os.environ.get("AGENT_TASK_ID") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not task_id:
        logger.error("agent_cold_start: no AGENT_TASK_ID in env/argv")
        return RC_NO_TASK_ID
    task = fetch(task_id)
    if task is None:
        logger.error("agent_cold_start: task %s not found", task_id)
        return RC_TASK_ABSENT
    if not claim(task_id, os.environ.get("AGENT_CALLSIGN")):
        logger.warning(
            "agent_cold_start: task %s not claimable (already taken) — exiting clean", task_id
        )
        return 0  # another agent owns it; not our failure
    rc = agent(compose_prompt(task))
    finalize(task_id, rc, task.get("acceptance_criteria"))
    logger.info("agent_cold_start: task %s finished, agent rc=%d", task_id, rc)
    return rc


def main() -> int:  # pragma: no cover — process entrypoint
    return run()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
