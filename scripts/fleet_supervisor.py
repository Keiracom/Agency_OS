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
import re
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
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


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
    # Two-call pattern: text in literal mode first, then Enter separately.
    # Single-call ["text", "Enter"] is unreliable when text contains newlines
    # (Claude tmux interprets embedded \n as soft-break and may eat the trailing Enter).
    subprocess.run(
        ["tmux", "send-keys", "-t", session, "-l", text],
        check=True,
    )
    # Tiny pause so the input box registers the text before Enter fires.
    time.sleep(0.3)
    subprocess.run(
        ["tmux", "send-keys", "-t", session, "Enter"],
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


_BLOCKER_PATTERN = re.compile(
    r"""
    (?:
        follow-up\s+after       # FOLLOW-UP after KEI-N
        | depends\s+on          # depends on KEI-N
        | gated\s+on            # gated on KEI-N
        | blocked\s+on          # blocked on KEI-N
        | sub\s+of              # sub of KEI-N
        | \(                    # (KEI-N follow-up)
    )
    \s*
    (KEI-\d+)                   # capture group: KEI-N
    """,
    re.VERBOSE | re.IGNORECASE,
)


def extract_blocker_keis(title: str, description: str) -> list[str]:
    """Return list of upper-cased KEI-N blocker identifiers from title + description."""
    combined = f"{title}\n{description}"
    return [m.group(1).upper() for m in _BLOCKER_PATTERN.finditer(combined)]


def _blockers_active(conn: psycopg.Connection, kei_ids: list[str]) -> list[str]:
    """Return KEI ids from kei_ids whose tasks are NOT done."""
    if not kei_ids:
        return []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM public.tasks WHERE id = ANY(%s) AND status != 'done'",
            (kei_ids,),
        )
        return [row[0] for row in cur.fetchall()]


def claim_next_task(
    conn: psycopg.Connection, callsign: str, phase_max: int
) -> tuple[str, str] | None:
    """Attempt to claim the highest-priority available task. Returns (id, title) or None.

    Skips tasks whose title/description reference a blocker KEI that is not yet done.
    """
    while True:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, COALESCE(description, '') FROM public.tasks
                WHERE status = 'available'
                  AND (phase IS NULL OR phase <= %s)
                  AND (is_parent IS NULL OR is_parent = false)
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
                (phase_max,),
            )
            row = cur.fetchone()
            if not row:
                return None
            task_id, title, description = row[0], row[1], row[2]

        blocker_keis = extract_blocker_keis(title, description)
        active_blockers = _blockers_active(conn, blocker_keis)
        if active_blockers:
            log.info(
                "[supervisor] skip %s — blocker %s not done",
                task_id,
                active_blockers[0],
            )
            # Mark temporarily so SKIP LOCKED won't re-select; we release below
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.tasks SET status = 'dep-blocked' WHERE id = %s",
                    (task_id,),
                )
            conn.commit()
            continue

        with conn.cursor() as cur:
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


def fetch_pr_comments(pr_number: int) -> list[dict]:
    """Fetch PR comments via gh pr view --json comments. Returns list of comment dicts."""
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--json", "comments"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.warning("gh pr view %d comments failed: %s", pr_number, result.stderr)
        return []
    try:
        data = json.loads(result.stdout) or {}
        return data.get("comments") or []
    except json.JSONDecodeError:
        return []


_REVIEW_COMMENT_PATTERN_TMPL = r"\[REVIEW(?::(?:approve|hold(?:-final)))?:{callsign}\]"


def comment_has_review_marker(body: str, callsign: str) -> bool:
    """Return True if body contains any [REVIEW:...:<callsign>] variant (case-insensitive)."""
    import re

    pattern = _REVIEW_COMMENT_PATTERN_TMPL.format(callsign=re.escape(callsign))
    return bool(re.search(pattern, body, re.IGNORECASE))


def agent_has_reviewed(pr: dict, callsign: str) -> bool:
    """Check if callsign already posted a [REVIEW:callsign] comment on this PR.

    Checks both formal GitHub review objects (pr['reviews']) and PR comments
    fetched via gh pr view --json comments, since agents post review markers
    as Slack-relayed comments rather than formal GH reviews.
    """
    # Check formal review objects first (fast, no subprocess)
    reviews = pr.get("reviews") or []
    tag = f"[REVIEW:{callsign}]".lower()
    for r in reviews:
        body = (r.get("body", "") or "").lower()
        if tag in body:
            return True

    # Check PR comments for [REVIEW:<callsign>] markers
    pr_number = pr.get("number")
    if pr_number is None:
        return False
    comments = fetch_pr_comments(pr_number)
    for c in comments:
        body = c.get("body", "") or ""
        if comment_has_review_marker(body, callsign):
            log.info("%s already reviewed PR #%d — skip", callsign, pr_number)
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
# Per-agent scenario handlers
# ---------------------------------------------------------------------------


def _handle_dead_tmux(
    callsign: str,
    tmux_session: str,
    service: str,
    conn: psycopg.Connection,
    phase_max: int,
    status: AgentStatus,
) -> AgentStatus | None:
    """Scenario 4: tmux session dead — restart service then claim next task."""
    if tmux_has_session(tmux_session):
        return None
    log.info("[%s] tmux session dead — restarting service", callsign)
    try:
        restart_service(service)
    except subprocess.CalledProcessError as exc:
        log.warning("[%s] restart failed: %s", callsign, exc)
    status.tmux_alive = False
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


def _handle_idle_with_queue(
    callsign: str,
    tmux_session: str,
    conn: psycopg.Connection,
    phase_max: int,
    status: AgentStatus,
) -> AgentStatus | None:
    """Scenario 1: no active claim, queue has items — claim and inject."""
    new_claim = claim_next_task(conn, callsign, phase_max)
    if new_claim is None:
        return None
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


def _handle_idle_no_queue(
    callsign: str,
    tmux_session: str,
    prs: list[dict],
    conn: psycopg.Connection,
    status: AgentStatus,
) -> AgentStatus:
    """Scenario 2/5: no claim, queue empty — assign PR review or log idle."""
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
    authored = [p for p in prs if is_authored_by_callsign(p, callsign)]
    if authored:
        log.info("[%s] Scenario 5: has open PR, queue empty — correctly idle", callsign)
        status.summary = "shipped pull request, idle, queue empty"
    else:
        log.info("[%s] Scenario 2: queue empty, no reviews — correctly idle", callsign)
        status.summary = "queue empty, no reviews — correctly idle"
    return status


def _handle_active_claim(
    callsign: str,
    tmux_session: str,
    service: str,
    conn: psycopg.Connection,
    claim: tuple[str, str],
    status: AgentStatus,
) -> AgentStatus:
    """Scenario 3/6: agent has active claim — check activity, nudge or restart."""
    task_id, title = claim
    status.active_task_id = task_id
    status.active_task_title = title
    last_call = get_last_tool_call(conn, callsign)
    status.last_tool_call = last_call
    now_utc = _dt.datetime.now(_dt.UTC)
    if last_call is None:
        minutes_ago = INACTIVITY_MINUTES + 1
    else:
        lc = last_call if last_call.tzinfo is not None else last_call.replace(tzinfo=_dt.UTC)
        minutes_ago = (now_utc - lc).total_seconds() / 60
    if minutes_ago < INACTIVITY_MINUTES:
        m = int(minutes_ago)
        log.info("[%s] active on %s (last call %dm ago)", callsign, task_id, m)
        status.summary = f"building {task_id} (last activity {m}m ago)"
        return status
    is_full = context_is_full(tmux_session)
    status.context_full = is_full
    if is_full:
        log.info("[%s] 100%% context — restarting + re-claiming %s", callsign, task_id)
        try:
            restart_service(service)
        except subprocess.CalledProcessError as exc:
            log.warning("[%s] restart failed: %s", callsign, exc)
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

    result = _handle_dead_tmux(callsign, tmux_session, service, conn, phase_max, status)
    if result is not None:
        return result

    status.tmux_alive = True
    claim = get_active_claim(conn, callsign)

    if claim is None:
        result = _handle_idle_with_queue(callsign, tmux_session, conn, phase_max, status)
        if result is not None:
            return result
        return _handle_idle_no_queue(callsign, tmux_session, prs, conn, status)

    return _handle_active_claim(callsign, tmux_session, service, conn, claim, status)


# ---------------------------------------------------------------------------
# CEO post
# ---------------------------------------------------------------------------


def _strip_ceo_banned_tokens(text: str) -> str:
    """Strip PR numbers + technical tokens that #ceo format-blocks."""
    import re

    # PR #NNN or pull request #NNN -> 'pull request' / 'a pull request'
    text = re.sub(r"(?:PR|pull request)\s*#\d+", "a pull request", text, flags=re.IGNORECASE)
    return text


def post_ceo_status(report: FleetReport) -> None:
    now_str = _dt.datetime.now(_dt.UTC).strftime("%H:%M UTC")
    lines = [f"**Fleet Status [{now_str}]**"]
    for s in report.statuses:
        # Strip PR number tokens — banned in #ceo per plain-English convention.
        # Replace "PR #NNN" / "pull request #NNN" patterns with neutral phrasing.
        clean_summary = _strip_ceo_banned_tokens(s.summary)
        lines.append(f"- {s.callsign}: {clean_summary}")
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
