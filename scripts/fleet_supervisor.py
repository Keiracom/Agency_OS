"""fleet_supervisor.py — Mechanical fleet supervisor (KEI-174).

Runs every 5 minutes via systemd timer. Diagnoses and auto-resolves
every idle scenario across all 6 agents. No human decision point.

Scenarios handled per agent:
    1. No claim + queue has items → claim + inject task prompt
    2. No claim + queue empty → assign PR review or log idle
    3. Claimed + no tool_call_log activity in 15min → nudge or restart
    4. tmux session dead → restart service + claim
    5. Agent shipped PR + went idle → start next build task
    6. Stale claims (>2h, no verification) → release back to available
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any

import psycopg

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AGENTS = [
    {"callsign": "elliot", "tmux": "elliottbot:0", "service": "elliot-agent"},
    {"callsign": "aiden", "tmux": "aiden:0", "service": "aiden-agent"},
    {"callsign": "max", "tmux": "max:0", "service": "max-agent"},
    {"callsign": "atlas", "tmux": "atlas:0", "service": "atlas-agent"},
    {"callsign": "orion", "tmux": "orion:0", "service": "orion-agent"},
    {"callsign": "scout", "tmux": "scout:0", "service": "scout-agent"},
]

# tmux send-keys delay in seconds
TMUX_DELAY = "0.5"

# Maximum characters of Linear issue description to inject
DESC_TRUNCATE = 2000

# Stale claim threshold
STALE_HOURS = 2

# Inactivity threshold before nudge/restart (minutes)
INACTIVITY_MINUTES = 15

# How long to wait after systemctl restart before continuing
RESTART_WAIT_SECONDS = 15

LINEAR_API_URL = "https://api.linear.app/graphql"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _db_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn


def _connect() -> psycopg.Connection:
    return psycopg.connect(_db_dsn(), prepare_threshold=None)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AgentStatus:
    callsign: str
    tmux_session: str
    service_name: str
    active_task_id: str | None = None
    active_task_title: str | None = None
    last_tool_call: _dt.datetime | None = None
    tmux_alive: bool = True
    context_full: bool = False
    # summary line for CEO post
    summary: str = ""


@dataclass
class FleetReport:
    statuses: list[AgentStatus] = field(default_factory=list)
    queue_available: int = 0
    queue_active: int = 0
    queue_done: int = 0


# ---------------------------------------------------------------------------
# tmux helpers
# ---------------------------------------------------------------------------


def tmux_has_session(session: str) -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", session],
        capture_output=True,
    )
    return result.returncode == 0


def tmux_send(session: str, text: str) -> None:
    subprocess.run(
        ["tmux", "send-keys", "-t", session, text, "Enter"],
        check=True,
    )


def tmux_capture(session: str) -> str:
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", session, "-p"],
        capture_output=True,
        text=True,
    )
    return result.stdout


def context_is_full(session: str) -> bool:
    pane = tmux_capture(session)
    return bool(
        "context.*100%" in pane or "/clear to save" in pane or "100%" in pane and "context" in pane
    )


# ---------------------------------------------------------------------------
# Systemd helpers
# ---------------------------------------------------------------------------


def restart_service(service: str) -> None:
    subprocess.run(
        ["systemctl", "--user", "restart", f"{service}.service"],
        check=True,
    )
    time.sleep(RESTART_WAIT_SECONDS)


# ---------------------------------------------------------------------------
# Supabase / DB helpers
# ---------------------------------------------------------------------------


def get_phase_max(conn: psycopg.Connection) -> int:
    """Read current allowed phase ceiling from ceo_memory."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM public.ceo_memory WHERE key = 'ceo:phase_lock' LIMIT 1")
            row = cur.fetchone()
            if row:
                val = row[0]
                if isinstance(val, dict):
                    return int(val.get("max_phase", 99))
                return int(val)
    except Exception:
        pass
    return 99


def get_active_claim(conn: psycopg.Connection, callsign: str) -> tuple[str, str] | None:
    """Return (task_id, title) for the active claim this callsign holds, or None."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title FROM public.tasks
            WHERE status = 'active' AND claimed_by = %s
            LIMIT 1
            """,
            (callsign,),
        )
        row = cur.fetchone()
    return (row[0], row[1]) if row else None


def claim_next_task(
    conn: psycopg.Connection, callsign: str, phase_max: int
) -> tuple[str, str] | None:
    """Attempt to claim the highest-priority available task. Returns (id, title) or None."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title FROM public.tasks
            WHERE status = 'available' AND (phase IS NULL OR phase <= %s)
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """,
            (phase_max,),
        )
        row = cur.fetchone()
        if not row:
            return None
        task_id, title = row[0], row[1]
        cur.execute(
            """
            UPDATE public.tasks
            SET status = 'active', claimed_by = %s, claimed_at = NOW()
            WHERE id = %s
            """,
            (callsign, task_id),
        )
    conn.commit()
    return (task_id, title)


def release_stale_claims(conn: psycopg.Connection) -> int:
    """Scenario 6: release tasks claimed >STALE_HOURS hours with no verification."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.tasks
            SET status = 'available', claimed_by = NULL, claimed_at = NULL
            WHERE status = 'active'
              AND claimed_at < NOW() - INTERVAL '%s hours'
              AND id NOT IN (SELECT task_id FROM public.task_verifications)
            """,
            (STALE_HOURS,),
        )
        count = cur.rowcount
    conn.commit()
    return count


def get_last_tool_call(conn: psycopg.Connection, callsign: str) -> _dt.datetime | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT MAX(created_at) FROM public.tool_call_log
            WHERE callsign = %s AND created_at > NOW() - INTERVAL '20 minutes'
            """,
            (callsign,),
        )
        row = cur.fetchone()
    return row[0] if row and row[0] else None


def get_queue_counts(conn: psycopg.Connection) -> tuple[int, int, int]:
    """Return (available, active, done) task counts."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              SUM(CASE WHEN status='available' THEN 1 ELSE 0 END),
              SUM(CASE WHEN status='active' THEN 1 ELSE 0 END),
              SUM(CASE WHEN status='done' THEN 1 ELSE 0 END)
            FROM public.tasks
            """
        )
        row = cur.fetchone()
    if row:
        return (int(row[0] or 0), int(row[1] or 0), int(row[2] or 0))
    return (0, 0, 0)


def insert_review_task(
    conn: psycopg.Connection,
    callsign: str,
    pr_number: int,
    pr_title: str,
    pr_url: str,
) -> None:
    task_id = f"REVIEW-PR-{pr_number}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.tasks (id, title, status, claimed_by, claimed_at, description)
            VALUES (%s, %s, 'active', %s, NOW(), %s)
            ON CONFLICT (id) DO UPDATE
              SET status = 'active', claimed_by = EXCLUDED.claimed_by, claimed_at = NOW()
            """,
            (task_id, f"Review PR #{pr_number} — {pr_title}", callsign, pr_url),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------


def list_open_prs() -> list[dict[str, Any]]:
    """Return list of open PRs as dicts with number, title, author, url, reviews."""
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "open",
            "--json",
            "number,title,author,reviews,url",
            "--limit",
            "50",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.warning("gh pr list failed: %s", result.stderr)
        return []
    try:
        return json.loads(result.stdout) or []
    except json.JSONDecodeError:
        return []


def agent_has_reviewed(pr: dict, callsign: str) -> bool:
    """Check if callsign already posted a [REVIEW:callsign] comment on this PR."""
    reviews = pr.get("reviews") or []
    tag = f"[REVIEW:{callsign}]"
    for r in reviews:
        body = r.get("body", "") or ""
        if tag in body:
            return True
    return False


def is_authored_by_callsign(pr: dict, callsign: str) -> bool:
    """Check if the PR title starts with [CALLSIGN] prefix."""
    title = pr.get("title", "") or ""
    return title.startswith(f"[{callsign.upper()}]")


def find_pr_for_review(prs: list[dict], callsign: str) -> dict | None:
    """Find a PR this agent can review: not their own, not already reviewed."""
    for pr in prs:
        if is_authored_by_callsign(pr, callsign):
            continue
        if agent_has_reviewed(pr, callsign):
            continue
        return pr
    return None


# ---------------------------------------------------------------------------
# Linear helpers
# ---------------------------------------------------------------------------


def fetch_linear_description(kei_id: str) -> tuple[str, str]:
    """Return (title, description) for a Linear KEI ID. Returns ('', '') on failure."""
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        return ("", "")

    # Linear identifier lookup requires searching by identifier, not UUID
    # Use issueSearch approach via filter
    search_query = """
    query SearchIssue($term: String!) {
      issueSearch(term: $term, first: 1) {
        nodes {
          title
          description
          identifier
        }
      }
    }
    """
    payload = json.dumps({"query": search_query, "variables": {"term": kei_id}}).encode()
    req = urllib.request.Request(
        LINEAR_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        nodes = data.get("data", {}).get("issueSearch", {}).get("nodes", [])
        if nodes:
            node = nodes[0]
            return (node.get("title", "") or "", node.get("description", "") or "")
    except Exception as exc:
        log.warning("Linear fetch failed for %s: %s", kei_id, exc)
    return ("", "")


# ---------------------------------------------------------------------------
# Injection helpers
# ---------------------------------------------------------------------------


def build_task_prompt(task_id: str, title: str, description: str) -> str:
    desc_part = description[:DESC_TRUNCATE] if description else ""
    return (
        f"You auto-claimed {task_id}: {title}\n\n"
        f"{desc_part}\n\n"
        "Build the work, ship a PR, then bd complete with evidence. Don't ask — execute."
    )


def build_review_prompt(pr_number: int, pr_title: str, pr_url: str, callsign: str) -> str:
    return (
        f"You auto-claimed review of PR #{pr_number}: {pr_title}. "
        f"URL: {pr_url}. "
        f"Run `gh pr view {pr_number}` + check CI/Sonar, "
        f"post [REVIEW:{callsign}] APPROVE or HOLD with verbatim evidence. Don't ask — execute."
    )


def inject_task(session: str, prompt: str) -> None:
    tmux_send(session, prompt)


# ---------------------------------------------------------------------------
# Per-agent scenario runner
# ---------------------------------------------------------------------------


def process_agent(
    agent: dict,
    conn: psycopg.Connection,
    prs: list[dict],
    phase_max: int,
) -> AgentStatus:
    callsign = agent["callsign"]
    tmux_session = agent["tmux"]
    service = agent["service"]
    status = AgentStatus(
        callsign=callsign,
        tmux_session=tmux_session,
        service_name=service,
    )

    # Scenario 4: tmux session dead
    if not tmux_has_session(tmux_session):
        log.info("[%s] tmux session dead — restarting service", callsign)
        try:
            restart_service(service)
        except subprocess.CalledProcessError as exc:
            log.warning("[%s] restart failed: %s", callsign, exc)
        status.tmux_alive = False
        # After restart fall through to Scenario 1 (claim + inject)
        claim = claim_next_task(conn, callsign, phase_max)
        if claim:
            task_id, title = claim
            lin_title, description = fetch_linear_description(task_id)
            effective_title = lin_title or title
            prompt = build_task_prompt(task_id, effective_title, description)
            if tmux_has_session(tmux_session):
                inject_task(tmux_session, prompt)
            status.active_task_id = task_id
            status.active_task_title = effective_title
            status.summary = f"session dead, restarted, claimed {task_id}"
        else:
            status.summary = "session dead, restarted, queue empty"
        return status

    status.tmux_alive = True

    # Check current claim
    claim = get_active_claim(conn, callsign)

    if claim is None:
        # Scenario 1: no claim, queue has items
        new_claim = claim_next_task(conn, callsign, phase_max)
        if new_claim:
            task_id, title = new_claim
            lin_title, description = fetch_linear_description(task_id)
            effective_title = lin_title or title
            prompt = build_task_prompt(task_id, effective_title, description)
            inject_task(tmux_session, prompt)
            status.active_task_id = task_id
            status.active_task_title = effective_title
            status.summary = f"was idle, claimed {task_id}, injected task"
            log.info("[%s] Scenario 1: claimed %s", callsign, task_id)
            return status

        # Scenario 2: no claim, queue empty — look for PR review
        review_pr = find_pr_for_review(prs, callsign)
        if review_pr:
            pr_number = review_pr["number"]
            pr_title = review_pr.get("title", f"PR #{pr_number}")
            pr_url = review_pr.get("url", f"https://github.com/keiracom/Agency_OS/pull/{pr_number}")
            insert_review_task(conn, callsign, pr_number, pr_title, pr_url)
            prompt = build_review_prompt(pr_number, pr_title, pr_url, callsign)
            inject_task(tmux_session, prompt)
            status.active_task_id = f"REVIEW-PR-{pr_number}"
            status.active_task_title = f"Review PR #{pr_number}"
            status.summary = f"was idle, reviewing PR #{pr_number}"
            log.info("[%s] Scenario 2: assigned PR #%d review", callsign, pr_number)
            return status

        # Scenario 5: agent shipped PR + went idle — check for authored open PRs
        authored = [p for p in prs if is_authored_by_callsign(p, callsign)]
        if authored:
            # Agent has an open PR — start next build task (Scenario 1 already tried)
            # Queue was empty, so agent is correctly idle after shipping
            log.info("[%s] Scenario 5: has open PR, queue empty — correctly idle", callsign)
            status.summary = "shipped pull request, idle, queue empty"
        else:
            log.info("[%s] Scenario 2: queue empty, no reviews — correctly idle", callsign)
            status.summary = "queue empty, no reviews — correctly idle"
        return status

    # Agent has an active claim
    task_id, title = claim
    status.active_task_id = task_id
    status.active_task_title = title

    # Scenario 3: claimed + check activity
    last_call = get_last_tool_call(conn, callsign)
    status.last_tool_call = last_call

    now_utc = _dt.datetime.now(_dt.UTC)
    if last_call is None:
        minutes_ago = INACTIVITY_MINUTES + 1  # treat as stale
    else:
        minutes_ago = (now_utc - last_call.replace(tzinfo=_dt.UTC)).total_seconds() / 60

    if minutes_ago < INACTIVITY_MINUTES:
        m = int(minutes_ago)
        log.info("[%s] active on %s (last call %dm ago)", callsign, task_id, m)
        status.summary = f"building {task_id} (last activity {m}m ago)"
        return status

    # Stale — check context
    is_full = context_is_full(tmux_session)
    status.context_full = is_full

    if is_full:
        log.info("[%s] 100%% context — restarting + re-claiming %s", callsign, task_id)
        try:
            restart_service(service)
        except subprocess.CalledProcessError as exc:
            log.warning("[%s] restart failed: %s", callsign, exc)
        # re-claim same KEI after restart
        lin_title, description = fetch_linear_description(task_id)
        effective_title = lin_title or title
        prompt = build_task_prompt(task_id, effective_title, description)
        if tmux_has_session(tmux_session):
            inject_task(tmux_session, prompt)
        status.summary = f"100%% context, restarted, re-claimed {task_id}"
    else:
        nudge = f"You have {task_id} claimed. Resume building. Title: {title}"
        inject_task(tmux_session, nudge)
        m = int(minutes_ago)
        log.info("[%s] nudged on %s (%dm stale)", callsign, task_id, m)
        status.summary = f"nudged on {task_id} ({m}m stale)"

    return status


# ---------------------------------------------------------------------------
# CEO post
# ---------------------------------------------------------------------------


def post_ceo_status(report: FleetReport) -> None:
    now_str = _dt.datetime.now(_dt.UTC).strftime("%H:%M UTC")
    lines = [f"**Fleet Status [{now_str}]**"]
    for s in report.statuses:
        lines.append(f"- {s.callsign}: {s.summary}")
    lines.append("")
    lines.append(
        f"**Queue: {report.queue_available} available | "
        f"{report.queue_active} active | "
        f"{report.queue_done} done**"
    )
    text = "\n".join(lines)

    tg_script = os.path.join(os.path.dirname(__file__), "tg")
    try:
        subprocess.run([tg_script, "-c", "ceo", text], check=True)
    except Exception as exc:
        log.warning("CEO post failed: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    log.info("Fleet supervisor starting")
    conn = _connect()

    try:
        # Scenario 6: release stale claims first
        released = release_stale_claims(conn)
        if released:
            log.info("Released %d stale claim(s)", released)

        phase_max = get_phase_max(conn)
        prs = list_open_prs()

        report = FleetReport()
        report.queue_available, report.queue_active, report.queue_done = get_queue_counts(conn)

        for agent in AGENTS:
            try:
                status = process_agent(agent, conn, prs, phase_max)
            except Exception as exc:
                log.exception("[%s] unhandled error: %s", agent["callsign"], exc)
                status = AgentStatus(
                    callsign=agent["callsign"],
                    tmux_session=agent["tmux"],
                    service_name=agent["service"],
                    summary=f"error: {exc}",
                )
            report.statuses.append(status)

        post_ceo_status(report)
    finally:
        conn.close()

    log.info("Fleet supervisor complete")


if __name__ == "__main__":
    main()
