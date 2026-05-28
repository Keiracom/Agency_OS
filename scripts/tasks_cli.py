#!/usr/bin/env python3
"""tasks_cli.py — KEI-22: Supabase tasks SSOT CLI.

Replaces `bd ready/claim/complete` against the Beads Dolt DB with direct
queries against `public.tasks` in Supabase (project jatzvazlbusedwsnqxzr).
Dave directive 2026-05-14: tasks table is now the queue source of truth;
Beads `bd ready` is bypassed.

Subcommands:
  ready     List tasks WHERE status='available', ordered by priority/created_at.
  claim     Atomically claim one task (SELECT FOR UPDATE SKIP LOCKED + UPDATE).
  complete  Mark a claimed task done (UPDATE status='done', claimed_by=NULL).
  show      Display single-task detail.

Env:
  DATABASE_URL or SUPABASE_DB_URL — postgres DSN to Supabase pooler.
  TASKS_CALLSIGN or CALLSIGN — claimant identifier (default: 'unknown').

JSON output (--json) preserves the consumer-facing shape of `bd ready --json`:
each item has at least {"id", "title", "priority"} plus the extra columns
present in public.tasks (status, claimed_by, dependencies, tags, linear_url).

Exit codes:
  0 — happy path (including "nothing to claim" on `claim --any`).
  1 — operator misconfig (no DSN, missing required arg, etc.).
  2 — database error (connection or query failure).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger("tasks_cli")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_CALLSIGN = "unknown"

# Shared help text for --callsign across subcommands (Sonar S1192 — avoid
# duplicating the same string literal across multiple add_argument calls).
_CALLSIGN_HELP = "override CALLSIGN env"

# Canonical column list shared by ready/show paths. Single source of truth
# (avoids Sonar new_duplicated_lines_density on the column projection).
_READY_COLUMNS = (
    "id, title, priority, status, claimed_by, claimed_at, "
    "dependencies, tags, linear_url, created_at, updated_at"
)

# KEI-53 Phase B — personalised score subquery joining agent_profiles.
# JSONB key-exists (?) gates the cast so non-matching tags don't error.
_PERSONALISED_SCORE_SUBQUERY = """COALESCE(
    (SELECT SUM((ap.capability_weights->>tag)::float)
     FROM public.agent_profiles ap,
          unnest(t.tags) AS tag
     WHERE ap.callsign = %s
       AND ap.capability_weights ? tag),
    0.0
) AS personalised_score"""


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise SystemExit("ERROR: DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def _callsign(arg: str | None) -> str:
    return (
        (arg or os.environ.get("TASKS_CALLSIGN") or os.environ.get("CALLSIGN") or DEFAULT_CALLSIGN)
        .strip()
        .lower()
    )


def _rows_to_dicts(cur: Any) -> list[dict]:
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]


def _enqueue_linear_sync(task_id: str, target_status: str) -> None:
    """Locked to a no-op under the Linear-read-only LAW (Dave ratified
    2026-05-20).

    This previously enqueued a public.completion_sync_queue row with
    target_sink='linear' for the completion_sync_worker to POST as an
    issueUpdate. Since Agency_OS-1x3x (Part 4) that worker's linear sink is
    itself a hard no-op, so the enqueued rows were dead writes. Linear status
    now propagates via the controlled one-way push
    (scripts/orchestrator/linear_oneway_push.py) only.

    Kept as a no-op stub so the claim/complete call sites need no change.
    """
    del task_id, target_status  # intentionally unused — enqueue suppressed
    logger.debug("Linear-read-only LAW: linear-sync enqueue suppressed (no-op)")


def _current_phase_max(cur: Any) -> float:
    """KEI-86 — read ceo_memory key 'ceo:phase_lock' → current_phase_max.

    Fail-open returns 99 (effectively unlocked) if the key is absent or the
    JSON shape is unexpected — preserves backwards-compat for any caller that
    runs before the migration lands. Real lock is enforced once the row exists.
    """
    cur.execute("SELECT value FROM public.ceo_memory WHERE key = 'ceo:phase_lock'")
    row = cur.fetchone()
    if not row:
        return 99.0
    try:
        return float(row[0]["current_phase_max"])
    except (KeyError, TypeError, ValueError):
        return 99.0


STALE_CLAIM_INTERVAL_HOURS = int(os.environ.get("TASKS_STALE_CLAIM_HOURS", "2"))


def _release_stale_claims(cur: Any) -> int:
    """KEI-104 — auto-release abandoned active claims back to available.

    A claim is "stale" when status='active' AND claimed_at older than
    TASKS_STALE_CLAIM_HOURS (default 2h) AND no task_verifications row exists
    for that task. Without this, an agent that crashed/lost context mid-claim
    leaves the task permanently locked — peers cannot bd ready or bd claim it.

    Idempotent: re-running on already-released rows is a no-op. Returns the
    number of rows released for caller-side logging. Fail-open: caller wraps
    in try/except so a release failure never blocks the originating read.
    """
    # S608 false-positive: the INTERVAL value is the module-level
    # STALE_CLAIM_INTERVAL_HOURS constant (int-cast from TASKS_STALE_CLAIM_HOURS
    # env var at import time), never user input. The suppression below uses
    # bare ruff-noqa-S608 syntax (no trailing prose) to satisfy Sonar S7632.
    cur.execute(
        f"""
        UPDATE public.tasks t
           SET status = 'available',
               claimed_by = NULL,
               claimed_at = NULL,
               updated_at = NOW()
         WHERE t.status = 'active'
           AND t.claimed_at IS NOT NULL
           AND t.claimed_at < NOW() - INTERVAL '{STALE_CLAIM_INTERVAL_HOURS} hours'
           AND NOT EXISTS (
               SELECT 1 FROM public.task_verifications v
                WHERE v.task_id = t.id
           )
        """  # noqa: S608
    )
    return cur.rowcount or 0


# ─── KEI-89 Gate 2: evidence validation helpers ─────────────────────────────

# Minimum characters required in any commands[].output field. Catches lazy
# single-word pastes like "ok" or "exit 0" that provide no verification signal.
_EVIDENCE_MIN_OUTPUT_LEN = 16


def _validate_command_entry(i: int, entry: object) -> str | None:
    """Validate a single commands[] entry shape + min-length on output."""
    if not isinstance(entry, dict):
        return f"commands[{i}] must be an object"
    if "cmd" not in entry:
        return f"commands[{i}].cmd missing"
    if "output" not in entry:
        return f"commands[{i}].output missing"
    output_len = len(str(entry["output"]))
    if output_len < _EVIDENCE_MIN_OUTPUT_LEN:
        return (
            f"commands[{i}].output too short "
            f"(min {_EVIDENCE_MIN_OUTPUT_LEN} chars, got {output_len})"
        )
    return None


def _validate_evidence_schema(payload: dict) -> str | None:
    """Validate the evidence JSON payload shape. Returns an error string on
    failure, or None when the payload is valid.
    """
    for field in ("acceptance_items", "commands", "verifier_session_uuid", "timestamp"):
        if field not in payload:
            return f"{field} missing"

    items = payload["acceptance_items"]
    if not isinstance(items, list) or len(items) == 0:
        return "acceptance_items must be a non-empty list"

    cmds = payload["commands"]
    if not isinstance(cmds, list) or len(cmds) == 0:
        return "commands must be a non-empty list"
    for i, entry in enumerate(cmds):
        err = _validate_command_entry(i, entry)
        if err:
            return err

    if not str(payload.get("verifier_session_uuid", "")).strip():
        return "verifier_session_uuid must be a non-empty string"
    if not str(payload.get("timestamp", "")).strip():
        return "timestamp must be a non-empty string"

    return None


def _canonical_hash(payload: dict) -> str:
    """Return sha256 hex of the canonical JSON representation (sort_keys=True)."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _check_hash_uniqueness(
    cur: Any, task_id: str, evidence_hash: str
) -> tuple[str | None, str | None]:
    """Check task_verifications for reuse of the same evidence text on a
    DIFFERENT task within the last 30 days.
    """
    cur.execute(
        """
        SELECT task_id, test_output, created_at
          FROM public.task_verifications
         WHERE task_id != %s
           AND created_at >= NOW() - INTERVAL '30 days'
        """,
        (task_id,),
    )
    rows = cur.fetchall()
    for row in rows:
        prior_task_id_val, stored_output, prior_ts = row[0], row[1], row[2]
        try:
            stored_payload = json.loads(stored_output)
            stored_hash = _canonical_hash(stored_payload)
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
        if stored_hash == evidence_hash:
            return str(prior_task_id_val), str(prior_ts)
    return None, None


def _build_ready_sql(agent: str, callsign: str, phase_max: int, limit: int) -> tuple[str, tuple]:
    """Compose the ready-query SQL + params for personalised/legacy and
    callsign-excluded/all variants. Extracted so cmd_ready stays under
    SonarCloud's cognitive-complexity cap (S3776)."""
    exclusion_clause = (
        "AND (t.excluded_callsign IS NULL OR t.excluded_callsign != %s) " if callsign else ""
    )
    if agent:
        sql = (
            f"SELECT t.{', t.'.join(_READY_COLUMNS.split(', '))}, "
            f"{_PERSONALISED_SCORE_SUBQUERY} "
            "FROM public.tasks t WHERE t.status = 'available' AND t.claimed_by IS NULL "
            "AND t.phase <= %s "
            f"{exclusion_clause}"
            "ORDER BY personalised_score DESC, "
            "t.priority ASC, t.created_at ASC LIMIT %s"
        )
        params: tuple = (
            (agent, phase_max, callsign, limit) if callsign else (agent, phase_max, limit)
        )
        return sql, params
    # KEI-97 — exclusion clause splices in identically on the non-personalised path.
    sql = (
        f"SELECT {_READY_COLUMNS} FROM public.tasks "
        "WHERE status = 'available' AND claimed_by IS NULL "
        "AND phase <= %s "
        f"{exclusion_clause}"
        "ORDER BY priority ASC, created_at ASC LIMIT %s"
    )
    params = (phase_max, callsign, limit) if callsign else (phase_max, limit)
    return sql, params


def _print_ready_rows(rows: list[dict], agent: str) -> None:
    """Render the human-readable ready listing. Extracted from cmd_ready
    so the main entry-point stays under S3776's complexity cap."""
    for r in rows:
        score_suffix = (
            f"  [score={r['personalised_score']:.2f}]"
            if agent and "personalised_score" in r
            else ""
        )
        # Coerce NULL priority to 'X' — Postgres NULL → Python None on
        # the priority column throws TypeError on the :>1 format spec.
        # Render as 'X' (unset) and stderr-warn so the row stays visible
        # rather than being silently filtered out of bd ready.
        priority = r["priority"]
        if priority is None:
            sys.stderr.write(
                f"[tasks_cli] warning: {r['id']} has NULL priority — "
                f"rendering as PX. Fix via `bd update {r['id']} --priority=N`.\n"
            )
            priority = "X"
        print(f"  P{priority:>1}  {r['id']:<24}  {r['title']}{score_suffix}")
    suffix = f" (personalised for {agent})" if agent else ""
    print(f"\n{len(rows)} available{suffix}")


def _gate3_dave_solo_ops(
    cur: Any,
    verified_by: str,
    secondary_verifier: str,
    verifier_session: str,
) -> tuple[str | None, str]:
    """Dave-solo-ops 2-of-3 path (extracted; keeps cognitive complexity low).

    Spec (3-way ratified KEI-128 ts ~1779010883, sharpened by Aiden's PR #928
    review): when builder=='dave', require SIMULTANEOUS --verifier <a> +
    --secondary-verifier <b> where a != b, neither is 'dave', and both have
    distinct session_uuids (verifier_session != b's most-recent
    tool_call_log session_uuid). Prevents single-agent fake-quorum via
    session-renewal.
    """
    sb = (secondary_verifier or "").strip().lower()
    if not sb:
        return (
            "ERROR: KEI-90 Gate 3 Dave-solo-ops — both --verifier and "
            "--secondary-verifier <callsign> are required when builder=='dave'.",
            verified_by,
        )
    if verified_by == sb:
        return (
            f"ERROR: KEI-90 Gate 3 Dave-solo-ops — --verifier ({verified_by!r}) "
            f"and --secondary-verifier ({sb!r}) must be distinct callsigns.",
            verified_by,
        )
    if verified_by == "dave" or sb == "dave":
        return (
            "ERROR: KEI-90 Gate 3 Dave-solo-ops — neither --verifier nor "
            "--secondary-verifier may be 'dave' (builder is dave).",
            verified_by,
        )
    cur.execute(
        """
        SELECT session_uuid FROM public.tool_call_log
         WHERE callsign = %s ORDER BY created_at DESC LIMIT 1
        """,
        (sb,),
    )
    row = cur.fetchone()
    sb_session = (row[0] if row and row[0] else "").strip()
    if not sb_session:
        return (
            f"ERROR: KEI-90 Gate 3 Dave-solo-ops — secondary verifier ({sb!r}) "
            "has no tool_call_log session_uuid on record (independence "
            "cannot be proven).",
            verified_by,
        )
    if sb_session == verifier_session:
        return (
            "ERROR: KEI-90 Gate 3 Dave-solo-ops — verifier_session_uuid and "
            "secondary verifier's session_uuid must be distinct.",
            verified_by,
        )
    return None, verified_by


def _check_gate3_peer_verify(
    cur: Any,
    task_id: str,
    callsign: str,
    verifier_arg: str | None,
    verifier_session: str,
    secondary_verifier_arg: str | None = None,
) -> tuple[str | None, str]:
    """KEI-90 Gate 3: peer-verify on deployment-class tasks.

    Returns (error_or_None, verified_by_callsign). When the task's
    deployment=false the function is a no-op returning (None, callsign).
    """
    cur.execute(
        "SELECT deployment, claimed_by FROM public.tasks WHERE id = %s",
        (task_id,),
    )
    row = cur.fetchone()
    deployment = bool(row[0]) if row and row[0] is not None else False
    builder = (row[1] if row and row[1] else "").strip().lower()
    if not deployment:
        return None, callsign
    if not verifier_arg:
        return (
            f"ERROR: KEI-90 Gate 3 — task is deployment=true; --verifier "
            f"<callsign> is required (must differ from builder={builder!r}).",
            callsign,
        )
    verified_by = (verifier_arg or "").strip().lower() or callsign
    if not verifier_session:
        return (
            "ERROR: KEI-90 Gate 3 — evidence.verifier_session_uuid is "
            "required for deployment=true tasks (session-independence).",
            verified_by,
        )
    if builder == "dave":
        err, verified_by = _gate3_dave_solo_ops(
            cur, verified_by, secondary_verifier_arg or "", verifier_session
        )
        if err:
            return err, verified_by
    elif verified_by == builder:
        return (
            f"ERROR: KEI-90 Gate 3 — verifier ({verified_by!r}) must differ "
            f"from builder ({builder!r}).",
            verified_by,
        )
    cur.execute(
        "SELECT 1 FROM public.tool_call_log WHERE callsign = %s AND session_uuid = %s LIMIT 1",
        (builder, verifier_session),
    )
    if cur.fetchone() is not None:
        return (
            f"ERROR: KEI-90 Gate 3 — verifier_session_uuid matches a prior "
            f"session of builder ({builder!r}); session-independence required.",
            verified_by,
        )
    return None, verified_by


def cmd_ready(args: argparse.Namespace) -> int:
    """List available tasks ordered by priority ASC then created_at ASC.

    KEI-53 Phase B: if --agent <callsign> is supplied, re-rank by
    personalised affinity score = SUM(capability_weight × matching_tag).
    Adds `personalised_score` to each row; preserves existing JSON shape
    (no renames) per Max's tasks-cli compat note.

    KEI-97: if --callsign is supplied, filter out tasks where
    excluded_callsign matches the given callsign (author-exclusion for
    REVIEW-PR tasks). Without --callsign, the exclusion filter is skipped
    (legacy behaviour preserved).
    """
    import psycopg

    limit = max(1, min(args.limit, 250))
    agent = (args.agent or "").strip().lower() if getattr(args, "agent", None) else ""
    callsign_arg = getattr(args, "callsign", None)
    callsign = (callsign_arg or "").strip().lower() if callsign_arg else ""
    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            # KEI-104 — release any stale claims before listing so abandoned
            # rows surface again. Fail-open: ready listing must not block on
            # release-helper failure.
            try:
                released = _release_stale_claims(cur)
                if released:
                    conn.commit()
                    logger.info("KEI-104 released %d stale active claim(s)", released)
            except Exception:
                logger.debug("KEI-104 stale-claim release failed (non-fatal)", exc_info=True)
            phase_max = _current_phase_max(cur)
            sql, params = _build_ready_sql(agent, callsign, phase_max, limit)
            cur.execute(sql, params)
            rows = _rows_to_dicts(cur)
    except psycopg.Error:
        logger.exception("ready query failed")
        return 2
    if args.json:
        print(json.dumps(rows, default=str))
    else:
        _print_ready_rows(rows, agent)
    return 0


def cmd_claim(args: argparse.Namespace) -> int:
    """Atomically claim one task (by id, or the next available).

    KEI-71: refuse the claim when the resolved callsign is the
    DEFAULT_CALLSIGN sentinel ('unknown') — Elliot Dave-direct callout
    2026-05-14T08:30Z: silent sentinel-writes (`claimed_by='unknown'`)
    leak when an agent omits `CALLSIGN=<callsign>` from the env. Fail
    fast at the validation layer so the operator notices the env gap
    instead of orphan-claiming a row.
    """
    import psycopg

    cs = _callsign(args.callsign)
    if cs == DEFAULT_CALLSIGN:
        print(
            "ERROR: callsign resolves to the DEFAULT_CALLSIGN sentinel "
            f"({DEFAULT_CALLSIGN!r}). Set CALLSIGN=<your_callsign> in the env or "
            "pass --callsign explicitly. Refusing to write a sentinel claim.",
            file=sys.stderr,
        )
        return 1
    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            # KEI-104 — release any stale claims before claiming so abandoned
            # rows become claimable again. Fail-open per release-helper contract.
            try:
                released = _release_stale_claims(cur)
                if released:
                    conn.commit()
                    logger.info("KEI-104 released %d stale active claim(s)", released)
            except Exception:
                logger.debug("KEI-104 stale-claim release failed (non-fatal)", exc_info=True)
            phase_max = _current_phase_max(cur)
            if args.id:
                # KEI-86 — phase pre-check on targeted claim so we can emit
                # an explanatory error instead of silently returning 'could
                # not claim …' (which is indistinguishable from a race loss).
                # Fail-open on parse errors so legacy rows / fixtures without
                # a numeric phase fall through to the UPDATE's own filter.
                # KEI-227: id OR bd_id — caller may pass either the canonical
                # Linear KEI-N or the bd-Dolt Agency_OS-xxx short-code.
                cur.execute(
                    "SELECT phase FROM public.tasks WHERE id = %s OR bd_id = %s",
                    (args.id, args.id),
                )
                _phase_row = cur.fetchone()
                _task_phase: float | None = None
                if _phase_row is not None:
                    try:
                        _task_phase = float(_phase_row[0])
                    except (TypeError, ValueError):
                        _task_phase = None
                if _task_phase is not None and _task_phase > phase_max:
                    print(
                        f"ERROR: KEI-86 phase-lock — task {args.id} is phase {_task_phase} "
                        f"but ceo:phase_lock.current_phase_max is {phase_max}. "
                        "Wait for CEO to advance the lock or pick a task at phase "
                        f"<= {phase_max}.",
                        file=sys.stderr,
                    )
                    return 1
                cur.execute(
                    """
                    UPDATE public.tasks
                       SET status = 'active', claimed_by = %s,
                           claimed_at = NOW(), updated_at = NOW()
                     WHERE (id = %s OR bd_id = %s)
                       AND status = 'available'
                       AND (claimed_by IS NULL OR claimed_by = %s)
                     RETURNING id, title, priority, status, claimed_by, linear_url, tags
                    """,
                    (cs, args.id, args.id, cs),
                )
            else:
                # KEI-86 — also filter the next-available SELECT by phase.
                cur.execute(
                    """
                    WITH next AS (
                      SELECT id
                        FROM public.tasks
                       WHERE status = 'available'
                         AND claimed_by IS NULL
                         AND phase <= %s
                       ORDER BY priority ASC, created_at ASC
                       FOR UPDATE SKIP LOCKED
                       LIMIT 1
                    )
                    UPDATE public.tasks t
                       SET status = 'active', claimed_by = %s,
                           claimed_at = NOW(), updated_at = NOW()
                      FROM next
                     WHERE t.id = next.id
                     RETURNING t.id, t.title, t.priority, t.status, t.claimed_by, t.linear_url, t.tags
                    """,
                    (phase_max, cs),
                )
            row = cur.fetchone()
            conn.commit()
    except psycopg.Error:
        logger.exception("claim query failed")
        return 2
    if row is None:
        if args.json:
            print("null")
        else:
            print("nothing to claim" if not args.id else f"could not claim {args.id}")
        return 0
    cols = ["id", "title", "priority", "status", "claimed_by", "linear_url", "tags"]
    claimed = dict(zip(cols, row, strict=False))
    # KEI-103 — fire retrieval on every successful claim so cognee_recall/Weaviate
    # is actually exercised (the writers existed but no production caller did).
    # Fail-open: agent_query.query() has its own try/except; we re-catch
    # ImportError + anything else so a broken retrieval layer never blocks a claim.
    try:
        from src.retrieval import orchestrator as _retrieval_orchestrator
        from src.retrieval.agent_query import query as _retrieval_query

        # Fleet-internal bd-claim recall — audit fix YELLOW-4, Agency_OS-7sj6.
        _retrieval_query(
            claimed["title"],
            agent=claimed["claimed_by"],
            tenant_id=_retrieval_orchestrator.FLEET_TENANT_SLUG,
        )
    except Exception:
        logger.debug("retrieval query for claim failed (non-fatal)", exc_info=True)
    # KEI-106 — propagate claim status to Linear via completion_sync_queue
    # (worker KEI-74 owns the Linear API call). Fail-open inside the helper.
    _enqueue_linear_sync(claimed["id"], "active")
    if args.json:
        print(json.dumps(claimed, default=str))
    else:
        # KEI-51 — context preamble before the success line. Best-effort:
        # failure to render preamble must never block the claim print itself.
        try:
            import importlib.util as _u

            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            spec = _u.spec_from_file_location(
                "claim_context_injector",
                os.path.join(repo_root, "scripts", "orchestrator", "claim_context_injector.py"),
            )
            inj = _u.module_from_spec(spec)
            spec.loader.exec_module(inj)
            # KEI-103 — wire Weaviate recall source so retrieval_events grows
            # per bd claim. Source is fail-open: import/query errors yield [].
            weaviate_src = inj.weaviate_recall_source(
                kei=claimed["id"],
                title=claimed.get("title") or "",
                callsign=claimed.get("claimed_by") or cs,
            )
            preamble = inj.format_preamble(
                kei=claimed["id"],
                tags=claimed.get("tags") or [],
                extra_sources=(weaviate_src,),
            )
            if preamble:
                print(preamble)
        except Exception:
            logger.exception("KEI-51 preamble emit failed (non-fatal)")
        # KEI-76 — Cognee session-memory preamble (second context block).
        # Sits between the KEI-51 discovery_log block and the success line.
        # Fail-open per cognee_recall contract: any failure → empty preamble.
        try:
            import importlib.util as _u

            _orch = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "scripts",
                "orchestrator",
            )
            cog_spec = _u.spec_from_file_location(
                "cognee_recall_injector",
                os.path.join(_orch, "cognee_recall_injector.py"),
            )
            cog_inj = _u.module_from_spec(cog_spec)
            cog_spec.loader.exec_module(cog_inj)
            cog_preamble = cog_inj.format_preamble(
                kei=claimed["id"],
                callsign=claimed.get("claimed_by") or cs,
            )
            if cog_preamble:
                print(cog_preamble)
        except Exception:
            logger.exception("KEI-76 cognee preamble emit failed (non-fatal)")
        print(f"claimed {claimed['id']} by {claimed['claimed_by']}: {claimed['title']}")
    return 0


def _coerce_behavioral_test(acceptance_items: list) -> str:
    """Coerce acceptance_items[0] to text for the behavioral_test column.

    Dict with `criterion` → criterion string. Dict without → deterministic JSON
    (no data loss). Plain string → passthrough (backwards-compat). Empty/None →
    "see commands". Hoisted out of cmd_complete to keep its cognitive
    complexity under the Sonar S3776 limit (y244 review feedback).
    """
    if not acceptance_items:
        return "see commands"
    first = acceptance_items[0]
    if isinstance(first, dict):
        return first.get("criterion") or json.dumps(first, sort_keys=True, ensure_ascii=False)
    return str(first) if first is not None else "see commands"


def _load_evidence_payload(evidence_path: str) -> dict | None:
    """Read evidence from a file path or stdin ('-'). Returns the parsed JSON
    dict on success, or None on read/parse failure (after printing the error)."""
    try:
        if evidence_path == "-":
            raw = sys.stdin.read()
        else:
            with open(evidence_path) as fh:
                raw = fh.read()
        return json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not load evidence from {evidence_path!r}: {exc}", file=sys.stderr)
        return None


def _execute_atomic_complete(
    cur: Any,
    task_id: str,
    callsign: str,
    behavioral_test: str,
    canonical_str: str,
    force_mode: str,
) -> tuple[Any, ...] | None:
    """INSERT task_verifications row + UPDATE tasks.status='done' in a single
    transaction. Returns the UPDATE's RETURNING row, or None when the task is
    not claimed by the caller (caller-side rollback expected)."""
    import uuid as _uuid

    cur.execute(
        """
        INSERT INTO public.task_verifications
               (id, task_id, verified_by, behavioral_test, test_output, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        """,
        (str(_uuid.uuid4()), task_id, callsign, behavioral_test, canonical_str),
    )
    cur.execute(
        """
        UPDATE public.tasks
           SET status = 'done',
               claimed_by = NULL,
               claimed_at = NULL,
               updated_at = NOW()
         WHERE (id = %s OR bd_id = %s)
           AND (claimed_by = %s OR %s = 'force')
         RETURNING id, title, status
        """,
        (task_id, task_id, callsign, force_mode),
    )
    return cur.fetchone()


def cmd_heartbeat(args: argparse.Namespace) -> int:
    """KEI-105 — write heartbeat_at = NOW() on a task the caller has claimed.

    Updates `public.tasks` for `id = %s AND claimed_by = %s` so an agent can
    only heartbeat tasks it currently owns. Returns rc=0 with the updated
    row on success, rc=1 when the task is not owned by the caller (so the
    helper is safe to invoke from auto-claim loops without sentinel
    side-effects), rc=2 on DB error. Idempotent — repeat calls just
    refresh the timestamp.

    Pairs with KEI-104 stale-claim auto-release: a recent heartbeat_at
    signals "actively working" even if claimed_at is old, so the release
    helper can avoid releasing live claims (follow-up integration).
    """
    import psycopg

    cs = _callsign(args.callsign)
    if cs == DEFAULT_CALLSIGN:
        print(
            "ERROR: callsign resolves to the DEFAULT_CALLSIGN sentinel "
            f"({DEFAULT_CALLSIGN!r}). Set CALLSIGN=<your_callsign> in the env or "
            "pass --callsign explicitly. Refusing to write a sentinel heartbeat.",
            file=sys.stderr,
        )
        return 1
    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.tasks
                   SET heartbeat_at = NOW(),
                       updated_at = NOW()
                 WHERE (id = %s OR bd_id = %s)
                   AND claimed_by = %s
                 RETURNING id, claimed_by, heartbeat_at
                """,
                (args.id, args.id, cs),
            )
            row = cur.fetchone()
            conn.commit()
    except psycopg.Error:
        logger.exception("heartbeat query failed")
        return 2
    if row is None:
        if args.json:
            print("null")
        else:
            print(f"could not heartbeat {args.id} (not claimed by {cs}?)", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"id": row[0], "claimed_by": row[1], "heartbeat_at": str(row[2])}))
    else:
        print(f"heartbeat {row[0]} by {row[1]} at {row[2]}")
    return 0


def _build_auto_verify_payload(task_id: str, callsign: str) -> dict:
    """KEI-239 — synthesise an evidence payload for `bd complete --auto-verify`.

    Used when the agent has done the work (PR merged, post-merge cleanup) and
    wants to mark the KEI done without manually crafting an evidence JSON.
    The synthetic payload still satisfies the KEI-89 schema:
      - acceptance_items: one entry attributing the close to the agent
      - commands: one entry with verbatim text >= 16 chars
      - verifier_session_uuid: CLAUDE_CODE_SESSION_ID env or a fresh uuid
      - timestamp: ISO-8601 UTC now

    Distinguishable from human-evidence by verifier_session_uuid prefix
    when CLAUDE_CODE_SESSION_ID is unset (uses 'auto-verify' marker).
    """
    import uuid as _uuid
    from datetime import UTC
    from datetime import datetime as _dt

    session = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not session:
        session = f"auto-verify-{_uuid.uuid4()}"
    now_iso = _dt.now(UTC).isoformat()
    return {
        "acceptance_items": [
            {
                "criterion": f"Task {task_id} closed via `bd complete --auto-verify`",
                "satisfied": True,
                "evidence": (
                    f"agent={callsign} closed via auto-verify at {now_iso}. "
                    f"Pre-conditions assumed satisfied by prior PR-merge / agent process; "
                    f"no separate evidence document was supplied at close time."
                ),
            }
        ],
        "commands": [
            {
                "cmd": f"bd complete {task_id} --auto-verify",
                "output": (
                    f"auto-verify path: agent={callsign} task={task_id} "
                    f"closed_at={now_iso}; no behavioural-test stdout captured "
                    f"because the work-evidence lives in the prior PR merge / "
                    f"systemd service log rather than a per-task script run."
                ),
            }
        ],
        "verifier_session_uuid": session,
        "timestamp": now_iso,
    }


def cmd_complete(args: argparse.Namespace) -> int:
    """Mark a claimed task done.

    KEI-89 Gate 2: --evidence <path|-> is required by default. The KEI-239
    `--auto-verify` flag bypasses the file-path requirement by synthesising
    a schema-compliant evidence payload attributed to the calling callsign;
    the synthetic verification still goes through the same uniqueness check
    + atomic INSERT+UPDATE transaction.
    """
    import psycopg

    # KEI-239 — auto-verify path. Synthesises an evidence payload so the
    # agent doesn't need a per-task evidence JSON when the work-evidence
    # already lives in PR merges / systemd logs / orchestrator history.
    if getattr(args, "auto_verify", False) and not getattr(args, "evidence", None):
        cs_for_synth = _callsign(args.callsign)
        evidence_payload = _build_auto_verify_payload(args.id, cs_for_synth)
    else:
        # Gate 2: evidence flag required when --auto-verify NOT passed.
        evidence_path: str | None = getattr(args, "evidence", None)
        if not evidence_path:
            print(
                "ERROR: --evidence <path|-> is required (or pass --auto-verify "
                "for synthetic evidence). Refusing to complete without structured "
                "evidence.",
                file=sys.stderr,
            )
            return 1

        evidence_payload = _load_evidence_payload(evidence_path)
        if evidence_payload is None:
            return 1

    schema_err = _validate_evidence_schema(evidence_payload)
    if schema_err:
        print(f"evidence schema invalid: {schema_err}", file=sys.stderr)
        return 1

    canonical_str = json.dumps(evidence_payload, sort_keys=True, ensure_ascii=False)
    evidence_hash = _canonical_hash(evidence_payload)
    cs = _callsign(args.callsign)
    verifier_arg = getattr(args, "verifier", None)
    secondary_arg = getattr(args, "secondary_verifier", None)
    verifier_session = str(evidence_payload.get("verifier_session_uuid", "")).strip()
    behavioral_test = _coerce_behavioral_test(evidence_payload["acceptance_items"])

    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            # KEI-90 Gate 3: deployment peer-verify (extracted helper).
            gate3_err, verified_by = _check_gate3_peer_verify(
                cur, args.id, cs, verifier_arg, verifier_session, secondary_arg
            )
            if gate3_err:
                print(gate3_err, file=sys.stderr)
                return 1
            prior_id, prior_ts = _check_hash_uniqueness(cur, args.id, evidence_hash)
            if prior_id is not None:
                print(
                    f"evidence text matches prior verification on task {prior_id} "
                    f"at {prior_ts} — reuse not allowed",
                    file=sys.stderr,
                )
                return 1
            row = _execute_atomic_complete(
                cur, args.id, verified_by, behavioral_test, canonical_str, args.force_mode
            )
            if row is None:
                conn.rollback()
                if args.json:
                    print("null")
                else:
                    print(f"could not complete {args.id} (not claimed by {cs}?)")
                return 1
            conn.commit()
    except psycopg.Error:
        logger.exception("complete query failed")
        return 2

    # KEI-106 — propagate completion to Linear via completion_sync_queue.
    # Reached only when commit succeeded (row is not None at this point).
    _enqueue_linear_sync(row[0], "done")
    if args.json:
        print(json.dumps({"id": row[0], "title": row[1], "status": row[2]}))
    else:
        print(f"completed {row[0]}: {row[1]}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Display single-task detail."""
    import psycopg

    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, priority, status, claimed_by, claimed_at,
                       dependencies, tags, linear_url, created_at, updated_at
                FROM public.tasks
                WHERE id = %s
                """,
                (args.id,),
            )
            rows = _rows_to_dicts(cur)
    except psycopg.Error:
        logger.exception("show query failed")
        return 2
    if not rows:
        print(f"not found: {args.id}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(rows[0], default=str))
    else:
        r = rows[0]
        print(f"{r['id']} [P{r['priority']}] {r['status']}")
        print(f"  title:      {r['title']}")
        print(f"  claimed_by: {r['claimed_by']}")
        print(f"  linear_url: {r['linear_url']}")
        print(f"  deps:       {r['dependencies']}")
        print(f"  tags:       {r['tags']}")
    return 0


def cmd_deprecate(args: argparse.Namespace) -> int:
    """KEI-63 — mark a discovery_log row deprecated. Excludes it from bd claim
    context injection (KEI-55 pipeline) and future Weaviate retrieval (KEI-46/47).

    Acceptance: discovery_log.mark_deprecated() flips deprecated=True on the
    most recent row with the given KEI. load_active_discoveries() then excludes it.
    """
    import importlib.util

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "discovery_log",
        os.path.join(repo_root, "scripts", "orchestrator", "discovery_log.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    callsign = (args.callsign or os.environ.get("CALLSIGN", "")).strip().lower()
    if not callsign:
        print("ERROR: --callsign required or set CALLSIGN env", file=sys.stderr)
        return 2

    try:
        row = mod.mark_deprecated(kei=args.id, reason=args.reason, by=callsign)
    except mod.DiscoveryLogError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(row, default=str))
    else:
        print(
            f"deprecated {row['kei']} (by {row['deprecated_by']}, "
            f"reason={row['deprecated_reason']!r}, at {row['deprecated_at']})"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="subcmd", required=True)

    p_ready = sub.add_parser("ready", help="list available tasks")
    p_ready.add_argument("--json", action="store_true")
    p_ready.add_argument("--limit", type=int, default=50)
    p_ready.add_argument(
        "--agent",
        help="KEI-53 — personalise ranking via agent_profiles.capability_weights",
    )
    p_ready.add_argument(
        "--callsign",
        help="KEI-97 — exclude tasks where excluded_callsign matches this callsign (author-exclusion for REVIEW-PR tasks)",
    )
    p_ready.set_defaults(func=cmd_ready)

    p_claim = sub.add_parser("claim", help="atomically claim a task")
    p_claim.add_argument("--id", help="specific task id; omit to take next available")
    p_claim.add_argument("--callsign", help=_CALLSIGN_HELP)
    p_claim.add_argument("--json", action="store_true")
    p_claim.set_defaults(func=cmd_claim)

    p_complete = sub.add_parser("complete", help="mark task done")
    p_complete.add_argument("id", help="task id")
    p_complete.add_argument("--callsign", help=_CALLSIGN_HELP)
    p_complete.add_argument(
        "--force-mode",
        default="strict",
        choices=["strict", "force"],
        help="force=allow completion regardless of claimed_by (admin)",
    )
    p_complete.add_argument(
        "--verifier",
        metavar="CALLSIGN",
        help="KEI-90 Gate 3: verifier callsign for deployment=true tasks. Must differ from builder; verifier_session_uuid in evidence must differ from any builder tool_call_log session_uuid.",
    )
    p_complete.add_argument(
        "--secondary-verifier",
        dest="secondary_verifier",
        metavar="CALLSIGN",
        help="KEI-90 Gate 3 Dave-solo-ops: second verifier callsign when builder=='dave'. Must differ from --verifier; neither may be 'dave'; secondary's most-recent tool_call_log session_uuid must differ from verifier_session_uuid.",
    )
    p_complete.add_argument(
        "--evidence",
        metavar="PATH",
        help="KEI-89 Gate 2: path to evidence JSON file, or '-' to read from stdin. Required unless --auto-verify is passed.",
    )
    p_complete.add_argument(
        "--auto-verify",
        action="store_true",
        dest="auto_verify",
        help="KEI-239: synthesise a schema-compliant evidence payload attributed to the calling callsign. Use when work-evidence lives in PR merges / systemd logs rather than a per-task script run.",
    )
    p_complete.add_argument("--json", action="store_true")
    p_complete.set_defaults(func=cmd_complete)

    p_show = sub.add_parser("show", help="show task detail")
    p_show.add_argument("id")
    p_show.add_argument("--json", action="store_true")
    p_show.set_defaults(func=cmd_show)

    p_deprecate = sub.add_parser(
        "deprecate",
        help="KEI-63 — mark a discovery_log entry deprecated (filtered from bd claim)",
    )
    p_deprecate.add_argument("id", help="KEI of the discovery to deprecate")
    p_deprecate.add_argument("--reason", required=True, help="why deprecated")
    p_deprecate.add_argument("--callsign", help=_CALLSIGN_HELP)
    p_deprecate.add_argument("--json", action="store_true")
    p_deprecate.set_defaults(func=cmd_deprecate)

    p_heartbeat = sub.add_parser(
        "heartbeat",
        help="KEI-105 — write heartbeat_at on a claimed task (active-work signal)",
    )
    p_heartbeat.add_argument("id", help="task id (KEI-NN) whose heartbeat to update")
    p_heartbeat.add_argument("--callsign", help=_CALLSIGN_HELP)
    p_heartbeat.add_argument("--json", action="store_true")
    p_heartbeat.set_defaults(func=cmd_heartbeat)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
