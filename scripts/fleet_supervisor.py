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
# KEI-183 / KEI-222: Supervisor v2 feature flags
# ---------------------------------------------------------------------------
# FLEET_SUPERVISOR_V2_ENABLED=1  enables v2 for agents whose AGENT_ROUTING=v2.
# AGENT_ROUTING_<CALLSIGN>=v2 (e.g. AGENT_ROUTING_ELLIOT=v2) opts that agent in.
# Both default OFF — v1 path is unchanged when flags absent. The flag is read
# at runtime (not import time) so install/test env writes always take effect.

FLEET_SUPERVISOR_V2_ENV = "FLEET_SUPERVISOR_V2_ENABLED"

# NATS connection details — canonical messaging backbone per KEI-205.
# Valkey stays for KEI-117 rate limiting + KV state only; NATS is the
# canonical messaging backbone per KEI-205.
NATS_URL: str = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")


def _supervisor_v2_enabled() -> bool:
    """KEI-185 — read `FLEET_SUPERVISOR_V2_ENABLED` env truthy-flag."""
    raw = os.environ.get(FLEET_SUPERVISOR_V2_ENV, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _agent_routing(callsign: str) -> str:
    """Return 'v2' if this agent is opted into v2 routing, else 'v1'."""
    env_key = f"AGENT_ROUTING_{callsign.upper()}"
    return os.environ.get(env_key, "v1")


def _is_v2(callsign: str) -> bool:
    """True when both global flag and per-agent routing are set to v2."""
    return _supervisor_v2_enabled() and _agent_routing(callsign) == "v2"


def _nats_publish_state(callsign: str, state: str) -> None:
    """KEI-183 v2 / KEI-205: publish agent state to NATS subject keiracom.agent.status.<callsign>.

    Payload: {"state": "<state>", "ts": <unix_epoch_int>}
    Subject: keiracom.agent.status.<callsign>
    Fail-open — NATS unavailable should never crash the supervisor.

    Note: Valkey stays for KEI-117 rate limiting + KV state only;
    NATS is the canonical messaging backbone per KEI-205.
    """
    try:
        import asyncio  # noqa: PLC0415 - lazy import inside try; nats-py optional on v1 path

        import nats.aio.client as nats_client  # noqa: PLC0415 — nats-py optional for v1 path

        payload = json.dumps({"state": state, "ts": int(time.time())}).encode()
        subject = f"keiracom.agent.status.{callsign}"

        async def _publish() -> None:
            nc = nats_client.Client()
            await nc.connect(NATS_URL, connect_timeout=2)
            try:
                await nc.publish(subject, payload)
                await nc.flush()
            finally:
                await nc.close()

        asyncio.run(_publish())
        log.debug("[%s] NATS PUBLISH %s → %s", callsign, subject, state)
    except Exception as exc:  # noqa: BLE001
        log.warning("[%s] NATS publish failed (non-fatal): %s", callsign, exc)


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
    {"callsign": "nova", "tmux": "nova:0", "service": "nova-agent"},
]

# tmux send-keys delay in seconds
TMUX_DELAY = "0.5"

# Maximum characters of Linear issue description to inject
DESC_TRUNCATE = 2000

# Stale claim threshold
STALE_HOURS = 2

# Smoke-test fixtures (Agency_OS-test001, KEI-TEST — title "smoke", NULL
# priority, no scope) are not real work; they must never be claimed or nudged
# on. SQL fragment excludes them by id and by any "smoke" in the title. Uses
# %% so it survives psycopg's %s-param queries unescaped.
_SMOKE_FIXTURE_EXCLUSION = (
    "id NOT IN ('Agency_OS-test001', 'KEI-TEST') "
    "AND lower(COALESCE(title, '')) NOT LIKE '%%smoke%%'"
)

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
    # KEI-218: strip SQLAlchemy driver suffix — psycopg3 rejects '+asyncpg'.
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
            f"""
            SELECT id, title FROM public.tasks
            WHERE status = 'active' AND claimed_by = %s
              AND {_SMOKE_FIXTURE_EXCLUSION}
            LIMIT 1
            """,
            (callsign,),
        )
        row = cur.fetchone()
    return (row[0], row[1]) if row else None


_KEI_ID_RE = re.compile(r"\bkei[-\s]?\d+\b", re.IGNORECASE)

# KEI-204 — dep-blocked drift filter. Captures the canonical phrasings used
# by Elliot's filing scripts + Linear convention. Each pattern's capture
# group is the KEI-NNN identifier that this row depends on; if any captured
# blocker is still status != 'done', claim_next_task skips the row.
# Patterns observed empirically across this session's 8 drift cases:
#   "FOLLOW-UP after KEI-185"  (KEI-191)
#   "depends on KEI-N"         (Linear convention)
#   "gated on KEI-N"
#   "blocked on KEI-N"
#   "sub of KEI-185"           (KEI-193 / KEI-194)
#   "(KEI-192 follow-up)"      (KEI-196 / KEI-197 / KEI-198)
_BLOCKER_PATTERNS = [
    re.compile(r"FOLLOW[\s-]?UP\s+after\s+(KEI-\d+)", re.IGNORECASE),
    re.compile(r"depends\s+on\s+(KEI-\d+)", re.IGNORECASE),
    re.compile(r"gated\s+on\s+(KEI-\d+)", re.IGNORECASE),
    re.compile(r"blocked\s+on\s+(KEI-\d+)", re.IGNORECASE),
    re.compile(r"sub\s+of\s+(KEI-\d+)", re.IGNORECASE),
    re.compile(r"\((KEI-\d+)\s+follow[\s-]?up\)", re.IGNORECASE),
]


def extract_blocker_keis(text: str) -> set[str]:
    """KEI-204 — extract KEI-NNN identifiers this row depends on from its
    title+description. Uses the 6 canonical phrasings observed empirically
    across the 2026-05-17→18 session's drift cases.

    Returns the canonical uppercase set; caller is responsible for the
    status='done' check against public.tasks.
    """
    if not text:
        return set()
    blockers: set[str] = set()
    for pat in _BLOCKER_PATTERNS:
        for m in pat.findall(text):
            digits = "".join(c for c in m if c.isdigit())
            if digits:
                blockers.add(f"KEI-{digits}")
    return blockers


def _unfinished_blockers(cur: psycopg.Cursor, blocker_ids: set[str]) -> set[str]:
    """KEI-204 — return the subset of blocker_ids whose tasks.status != 'done'.
    Empty set means all blockers cleared; row is claimable."""
    if not blocker_ids:
        return set()
    cur.execute(
        "SELECT id FROM public.tasks WHERE id = ANY(%s::text[]) AND status != 'done'",
        (sorted(blocker_ids),),
    )
    return {row[0] for row in cur.fetchall()}


def fetch_open_pr_kei_ids() -> set[str]:
    """KEI-199 — return set of KEI-NNN identifiers mentioned in OPEN PR titles+bodies.

    Used by claim_next_task() as a pre-claim filter to prevent the auto-claim
    loop assigning work that's already in flight via an OPEN PR. Anchor:
    4 drift-syncs in the 2026-05-17→18 session (KEI-90 / 122 / 187 / 188)
    where agents were re-claimed onto KEIs that peers had already shipped.

    Returns empty set on any gh CLI failure (fail-open — preserves prior
    claim behaviour rather than blocking all claims on a CLI hiccup).
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json", "title,body", "--limit", "100"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        log.debug("KEI-199: gh pr list failed — fail-open (returning empty set)")
        return set()
    if result.returncode != 0:
        log.debug("KEI-199: gh pr list exit=%d — fail-open", result.returncode)
        return set()
    try:
        prs = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return set()
    kei_ids: set[str] = set()
    for pr in prs:
        title = pr.get("title") or ""
        body = pr.get("body") or ""
        for m in _KEI_ID_RE.findall(title) + _KEI_ID_RE.findall(body):
            # Normalize to canonical KEI-NNN uppercase form (titles often
            # carry lowercase "kei199" in commit-scope, identifiers in DB
            # are always uppercase).
            digits = "".join(c for c in m if c.isdigit())
            if digits:
                kei_ids.add(f"KEI-{digits}")
    return kei_ids


_CANDIDATE_LIMIT = 10  # KEI-204 — top-N candidates to iterate; bounds dep-blocked rescan cost

# KEI-183 follow-up (Dave 2026-05-18) — structural dep enforcement.
# `tasks.dependencies` is a text[] ARRAY of task ids. A row is eligible only if
# every entry resolves to a row in status='done'. This makes out-of-sequence
# dispatch structurally impossible — no row reaches the candidate set unless
# all its deps are done. Complements (does not replace) the title/description
# keyword filter in extract_blocker_keis (KEI-204), which catches plain-prose
# "depends on KEI-X" phrasings the dependencies column doesn't capture.
_DEPS_CLAUSE = (
    "AND (\n"
    "    dependencies IS NULL\n"
    "    OR cardinality(dependencies) = 0\n"
    "    OR NOT EXISTS (\n"
    "      SELECT 1 FROM unnest(dependencies) AS dep_id\n"
    "      JOIN public.tasks t_dep ON t_dep.id = dep_id\n"
    "      WHERE t_dep.status != 'done'\n"
    "    )\n"
    "  )\n"
)


def _build_task_query(
    v2: bool, open_pr_keis: set[str], callsign: str, phase_max: int
) -> tuple[str, tuple]:
    """Return (sql, params) for the candidate fetch in claim_next_task.

    Extracted to reduce cognitive complexity in the caller (S3776).
    Four combinations: v2 × has_open_pr_filter.

    KEI-183 follow-up — _DEPS_CLAUSE is injected on every path so the
    dependency-enforcement gate is universal (v1 + v2, with and without
    open-PR filter).
    """
    base = f"""
        SELECT id, title, COALESCE(description, '') FROM public.tasks
        WHERE status = 'available'
          AND (phase IS NULL OR phase <= %s)
          AND (is_parent IS NULL OR is_parent = false)
          AND {_SMOKE_FIXTURE_EXCLUSION}
    """
    base = base.rstrip() + "\n  " + _DEPS_CLAUSE
    # KEI-183 follow-up — phase ASC first so lower-phase work drains before
    # higher-phase work even within the same priority bucket (Dave directive).
    suffix = "ORDER BY phase ASC NULLS LAST, priority ASC, created_at ASC\nLIMIT %s\nFOR UPDATE SKIP LOCKED"
    if open_pr_keis:
        if v2:
            sql = f"{base}  AND id != ALL(%s::text[])\n  AND (persona = %s OR persona IS NULL)\n{suffix}"
            params = (phase_max, sorted(open_pr_keis), callsign, _CANDIDATE_LIMIT)
        else:
            sql = f"{base}  AND id != ALL(%s::text[])\n{suffix}"
            params = (phase_max, sorted(open_pr_keis), _CANDIDATE_LIMIT)
    else:
        if v2:
            sql = f"{base}  AND (persona = %s OR persona IS NULL)\n{suffix}"
            params = (phase_max, callsign, _CANDIDATE_LIMIT)
        else:
            sql = f"{base}{suffix}"
            params = (phase_max, _CANDIDATE_LIMIT)
    return sql, params


def claim_next_task(
    conn: psycopg.Connection, callsign: str, phase_max: int
) -> tuple[str, str] | None:
    """Attempt to claim the highest-priority available task. Returns (id, title) or None.

    KEI-199 — filters out KEIs that already have an OPEN PR (title or body
    mentions). Without this, the supervisor loop re-claims already-shipped
    work (KEI-90 / 122 / 187 / 188 drift-syncs in the 2026-05-17→18 session).

    KEI-204 — filters out FOLLOW-UP / sub-of / depends-on / gated-on rows
    whose blocking KEI is still status != 'done'. Anchor: KEI-191
    'FOLLOW-UP after KEI-C (KEI-185 Nova spawn)' was dispatched 3x in the
    session despite the explicit dep gate (Max yield, Scout yield, Aiden
    yield). Six canonical phrasings parsed via _BLOCKER_PATTERNS.

    KEI-183 v2: when _is_v2(callsign) the WHERE clause filters by persona lane:
        persona = $callsign OR persona IS NULL
    so agents only pick up tasks in their lane or unassigned-overflow tasks.
    v1 path is unchanged (no persona filter).
    """
    open_pr_keis = fetch_open_pr_kei_ids()
    v2 = _is_v2(callsign)
    sql, params = _build_task_query(v2, open_pr_keis, callsign, phase_max)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        candidates = cur.fetchall()
        for row in candidates:
            task_id, title, description = row[0], row[1], row[2] or ""
            blockers = extract_blocker_keis(title + "\n" + description)
            if blockers:
                unfinished = _unfinished_blockers(cur, blockers)
                if unfinished:
                    log.debug(
                        "KEI-204: %s skipped — blocked by %s",
                        task_id,
                        sorted(unfinished),
                    )
                    continue
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
    # Either no candidates OR all candidates dep-blocked
    return None


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


def release_merged_review_claims(conn: psycopg.Connection) -> int:
    """Release REVIEW-PR-<N> claims whose PR has merged or closed.

    A REVIEW-PR-<N> row (inserted by insert_review_task) stays status='active'
    forever once claimed — nothing transitions it when the PR merges, so the
    supervisor nudges the claimant indefinitely on a review that is already
    done. This releases the claim (status='done') the moment its PR is no
    longer open. Returns the count released. Fail-open: a gh failure on one
    PR is logged and skipped, never aborts the sweep.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM public.tasks "
            "WHERE status = 'active' AND id LIKE 'REVIEW-PR-%'"
        )
        review_ids = [r[0] for r in cur.fetchall()]
    released = 0
    for task_id in review_ids:
        m = re.match(r"REVIEW-PR-(\d+)$", task_id)
        if not m:
            continue
        pr_number = m.group(1)
        try:
            proc = subprocess.run(  # noqa: S603,S607 — controlled args, no shell
                ["gh", "pr", "view", pr_number, "--json", "state", "-q", ".state"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            log.warning("release_merged_review_claims: gh pr view %s failed: %s", pr_number, exc)
            continue
        state = (proc.stdout or "").strip().upper()
        if state in ("MERGED", "CLOSED"):
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.tasks SET status = 'done' "
                    "WHERE id = %s AND status = 'active'",
                    (task_id,),
                )
                released += cur.rowcount
            log.info("released review claim %s — PR #%s is %s", task_id, pr_number, state)
    if released:
        conn.commit()
    return released


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


# KEI-190: trailing `?` on `-final` is the bug fix — previous regex required
# `-final` to match, so bare `[REVIEW:HOLD:callsign]` (the form every reviewer
# actually uses) was treated as "no review found" and the supervisor re-dispatched
# the same PR every cycle. Now matches: bare `[REVIEW:callsign]`, `:approve:`,
# `:hold:`, `:hold-final:` — symmetric APPROVE/HOLD parsing.
_REVIEW_COMMENT_PATTERN_TMPL = r"\[REVIEW:[^\]]*\b{callsign}\b"


def comment_has_review_marker(body: str, callsign: str) -> bool:
    """Return True if body contains any [REVIEW:...:<callsign>] variant (case-insensitive)."""
    import re

    pattern = _REVIEW_COMMENT_PATTERN_TMPL.format(callsign=re.escape(callsign))
    return bool(re.search(pattern, body, re.IGNORECASE))


def agent_has_reviewed(pr: dict, callsign: str) -> bool:
    """Check if callsign already posted a [REVIEW:...] marker on this PR.

    Checks both formal GitHub review objects (pr['reviews']) and PR comments
    fetched via gh pr view --json comments, since agents post review markers
    as Slack-relayed comments rather than formal GH reviews. Uses the
    broadened pattern in `_REVIEW_COMMENT_PATTERN_TMPL` via the
    comment_has_review_marker helper.

    Agency_OS-wy3e: the prior narrow template missed real-world shapes like
    [REVIEW:HOLD max] (space-separated), [REVIEW:HOLD-CONTINUED max], and
    [REVIEW:APPROVE-WITH-NOTES:max]. The template was widened to a single
    `\\[REVIEW:[^\\]]*\\b{callsign}\\b` pattern that accepts any verdict
    prefix and any separator before the callsign — see _REVIEW_COMMENT_PATTERN_TMPL.
    """
    reviews = pr.get("reviews") or []
    for r in reviews:
        body = r.get("body", "") or ""
        if comment_has_review_marker(body, callsign):
            return True

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


_SONAR_PROJECT_KEY = "Keiracom_Agency_OS"
_SONAR_BASE = "https://sonarcloud.io/api"


def fetch_sonar_status(pr_number: int) -> dict[str, Any]:
    """KEI-189: dual-endpoint Sonar verify — issues + Quality Gate.

    /api/issues/search returns S-rule findings (bugs/code smells/vulnerabilities).
    /api/qualitygates/project_status returns the QG verdict including SEPARATE
    conditions like new_duplicated_lines_density that the issues endpoint
    does NOT surface.

    Anchored on PRs #940/#963/#981 today where issues=0 but QG=ERROR on
    dup-density — three of us missed the gap because we only checked /issues.
    Encodes the feedback_sonarcloud_verify_pattern memory pin mechanically.

    Returns {"issues_total": int, "qg_status": str, "qg_failing": list[str]}
    on success; {} on any fetch failure (fail-open — review still proceeds,
    agent sees missing-data in brief and can run curl themselves).
    """
    out: dict[str, Any] = {}
    issues_url = f"{_SONAR_BASE}/issues/search?componentKeys={_SONAR_PROJECT_KEY}&pullRequest={pr_number}&resolved=false"
    qg_url = f"{_SONAR_BASE}/qualitygates/project_status?projectKey={_SONAR_PROJECT_KEY}&pullRequest={pr_number}"
    try:
        with urllib.request.urlopen(issues_url, timeout=10) as resp:
            data = json.loads(resp.read())
        out["issues_total"] = int(data.get("total", 0))
    except Exception as exc:
        log.warning("Sonar /issues fetch failed for PR #%d: %s", pr_number, exc)
    try:
        with urllib.request.urlopen(qg_url, timeout=10) as resp:
            data = json.loads(resp.read())
        ps = data.get("projectStatus", {})
        out["qg_status"] = ps.get("status", "UNKNOWN")
        out["qg_failing"] = [
            f"{c.get('metricKey')}={c.get('actualValue')} (>{c.get('errorThreshold')})"
            for c in ps.get("conditions", [])
            if c.get("status") == "ERROR"
        ]
    except Exception as exc:
        log.warning("Sonar /qualitygates fetch failed for PR #%d: %s", pr_number, exc)
    return out


def _format_sonar_brief(sonar: dict[str, Any]) -> str:
    """Format Sonar status for inclusion in the review brief. Returns empty
    string if no data fetched (fail-open — reviewer runs curl themselves)."""
    if not sonar:
        return ""
    lines = ["", "Sonar (BOTH endpoints — issues + QG — checked at brief-emit time):"]
    if "issues_total" in sonar:
        lines.append(f"  • /api/issues/search → total NEW unresolved: {sonar['issues_total']}")
    if "qg_status" in sonar:
        lines.append(f"  • /api/qualitygates/project_status → status: {sonar['qg_status']}")
        for cond in sonar.get("qg_failing", []) or []:
            lines.append(f"      FAIL: {cond}")
    lines.append(
        "  ⚠ APPROVE requires BOTH endpoints clean (issues=0 AND QG=OK). "
        "QG can ERROR on dimensions like new_duplicated_lines_density that issues misses."
    )
    return "\n".join(lines)


def build_review_prompt(pr_number: int, pr_title: str, pr_url: str, callsign: str) -> str:
    """Emit the review-claim prompt. KEI-189: includes Sonar issues + QG snapshot."""
    sonar = fetch_sonar_status(pr_number)
    sonar_block = _format_sonar_brief(sonar)
    return (
        f"You auto-claimed review of PR #{pr_number}: {pr_title}. "
        f"URL: {pr_url}. "
        f"Run `gh pr view {pr_number}` + check CI/Sonar, "
        f"post [REVIEW:{callsign}] APPROVE or HOLD with verbatim evidence. "
        f"Don't ask — execute.{sonar_block}"
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
    """Scenario 2/5: no claim, queue empty — assign PR review or log idle.

    KEI-183 v2 / KEI-205: when _is_v2(callsign), publish {"state":"ready"} to NATS
    subject keiracom.agent.status.<callsign> instead of relying on the Slack
    [READY] tmux-send. v1 path unchanged.
    """
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
    # KEI-183 v2 / KEI-205: publish NATS ready-state instead of Slack [READY] tmux-send.
    if _is_v2(callsign):
        _nats_publish_state(callsign, "ready")
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
# Fleet-status post
# ---------------------------------------------------------------------------


def post_fleet_status(report: FleetReport) -> None:
    """Post the periodic fleet status to #execution.

    Dave directive 2026-05-20: fleet status — per-agent nudge states + queue
    counts — is operational/peer information, NOT a CEO outcome/blocker/
    decision. It belongs in #execution. #ceo must never receive it.
    """
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
        subprocess.run([tg_script, "-c", "execution", text], check=True)
    except Exception as exc:
        log.warning("fleet-status post failed: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _try_run_supervisor_v2() -> bool:
    """Attempt v2 dispatch. Returns True on success, False on ImportError so
    main() falls through to v1. Any exception inside v2.run() is left to
    propagate — v2-on operators get the real trace, not a v1 silent-fallback.
    """
    try:
        from src.fleet import supervisor_v2  # type: ignore[import-not-found]  # noqa: PLC0415
    except ImportError:
        log.warning(
            "FLEET_SUPERVISOR_V2_ENABLED=1 but supervisor_v2 module missing "
            "(KEI-183/PR #990 not yet merged) — falling back to v1"
        )
        return False
    log.info("supervisor v2 ON (KEI-185 flag flipped) — routing to supervisor_v2.run()")
    supervisor_v2.run()
    return True


def main() -> None:
    log.info("Fleet supervisor starting")
    if _supervisor_v2_enabled() and _try_run_supervisor_v2():
        log.info("Fleet supervisor complete (v2 path)")
        return
    conn = _connect()

    try:
        # Scenario 6: release stale claims first
        released = release_stale_claims(conn)
        if released:
            log.info("Released %d stale claim(s)", released)

        # Release review claims whose PR has merged/closed — stops the
        # supervisor nudging indefinitely on a review that is already done.
        released_reviews = release_merged_review_claims(conn)
        if released_reviews:
            log.info("Released %d merged/closed review claim(s)", released_reviews)

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

        post_fleet_status(report)
    finally:
        conn.close()

    log.info("Fleet supervisor complete")


if __name__ == "__main__":
    main()
