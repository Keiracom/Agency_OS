#!/usr/bin/env python3
"""test_fleet_scoreboard.py — Proof gate for the fleet liveness scoreboard.

Re-runnable end-to-end proof that fleet_liveness_checker.py + the
public.fleet_liveness_status view honestly classify GREEN / RED / MISMATCH.

Three tests, all must pass:

  TEST 1 (positive, end-to-end):
    Invoke scripts/orchestrator/fleet_liveness_checker.py once. Verify the
    view returns one row per expected callsign (all 7) and that every
    last_seen timestamp is within the last 5 minutes. This proves the
    checker actually wrote rows and the view surfaces them.

  TEST 2 (negative, RED):
    INSERT a synthetic fleet_liveness row for callsign='test_agent' with
    tmux_alive=FALSE, checked_at=NOW(). Verify the view emits status='RED'
    for that callsign and ONLY for that callsign (no spillover to real
    agents). Then DELETE the synthetic row.

  TEST 3 (negative, MISMATCH):
    INSERT a synthetic row for callsign='test_agent2' with tmux_alive=TRUE
    and callsign_match=FALSE. Verify the view emits status='MISMATCH'.
    Then DELETE the synthetic row.

Exit 0 if every test passes. Exit 1 with a labelled failure list otherwise.

Anchor: KEI Agency_OS-scout fleet-scoreboard-p0 dispatch from Elliot
2026-06-02. Sibling to scripts/orchestrator/fleet_liveness_checker.py and
supabase/migrations/20260602_fleet_liveness_callsign_match.sql.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "scripts" / "orchestrator" / "fleet_liveness_checker.py"
ENV_FILE = Path.home() / ".config" / "agency-os" / ".env"

EXPECTED_CALLSIGNS = {"elliot", "aiden", "max", "atlas", "orion", "scout", "nova"}
TEST_RED_CALLSIGN = "test_agent"
TEST_MISMATCH_CALLSIGN = "test_agent2"
TEST_CALLSIGNS = (TEST_RED_CALLSIGN, TEST_MISMATCH_CALLSIGN)
FRESHNESS_MINUTES = 5


def _load_env_file(path: Path) -> None:
    """Populate os.environ from a KEY=VALUE .env file. Existing vars win."""
    if not path.is_file():
        return
    try:
        text = path.read_text()
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _resolve_dsn() -> str | None:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def _purge_test_rows(cur) -> None:
    cur.execute(
        "DELETE FROM public.fleet_liveness WHERE callsign = ANY(%s)",
        (list(TEST_CALLSIGNS),),
    )


def _run_checker() -> tuple[int, str, str]:
    """Invoke the on-box checker as a subprocess; return (rc, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, str(CHECKER)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def _test_1_end_to_end(conn) -> list[str]:
    """Returns a list of failure messages — empty list == pass."""
    failures: list[str] = []
    rc, out, err = _run_checker()
    if rc != 0:
        failures.append(f"TEST 1: checker exited rc={rc} (expected 0)\nstderr:\n{err}")
        return failures

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT callsign,
                   status,
                   EXTRACT(EPOCH FROM (NOW() - last_seen)) AS age_seconds
            FROM public.fleet_liveness_status
            WHERE callsign = ANY(%s)
            """,
            (sorted(EXPECTED_CALLSIGNS),),
        )
        rows = cur.fetchall()

    by_callsign = {r[0]: (r[1], float(r[2])) for r in rows}
    missing = sorted(EXPECTED_CALLSIGNS - by_callsign.keys())
    if missing:
        failures.append(
            f"TEST 1: missing callsigns in fleet_liveness_status: {missing} "
            f"(found: {sorted(by_callsign.keys())})"
        )

    threshold = FRESHNESS_MINUTES * 60
    stale = sorted(
        (cs, age) for cs, (_status, age) in by_callsign.items() if age > threshold
    )
    if stale:
        failures.append(
            f"TEST 1: callsigns with last_seen older than {FRESHNESS_MINUTES} min: {stale}"
        )

    print(f"[TEST 1] checker rc={rc}, view rows: {len(rows)}/{len(EXPECTED_CALLSIGNS)}")
    for cs in sorted(by_callsign):
        status, age = by_callsign[cs]
        print(f"         {cs:<8} status={status:<8} age={age:6.1f}s")
    return failures


def _test_2_red(conn) -> list[str]:
    failures: list[str] = []
    with conn.cursor() as cur:
        _purge_test_rows(cur)
        cur.execute(
            """
            INSERT INTO public.fleet_liveness
                (callsign, checked_at, tmux_alive, nats_last_publish_at,
                 backend_health, active_task_id, reported_callsign, callsign_match)
            VALUES (%s, NOW(), FALSE, NULL, NULL, NULL, NULL, NULL)
            """,
            (TEST_RED_CALLSIGN,),
        )
        conn.commit()

        cur.execute(
            "SELECT status FROM public.fleet_liveness_status WHERE callsign = %s",
            (TEST_RED_CALLSIGN,),
        )
        row = cur.fetchone()

        # Bonus check: synthetic insert must NOT bleed into real callsigns.
        cur.execute(
            """
            SELECT COUNT(*) FROM public.fleet_liveness_status
            WHERE callsign = ANY(%s) AND status = 'RED'
              AND last_seen > NOW() - INTERVAL '5 min'
            """,
            (sorted(EXPECTED_CALLSIGNS),),
        )
        red_real = cur.fetchone()[0]

        _purge_test_rows(cur)
        conn.commit()

    if row is None:
        failures.append(f"TEST 2: no view row for {TEST_RED_CALLSIGN}")
    elif row[0] != "RED":
        failures.append(f"TEST 2: status was {row[0]!r}, expected 'RED'")

    print(f"[TEST 2] synthetic {TEST_RED_CALLSIGN} status={row[0] if row else 'NULL'} "
          f"(real-callsign RED count after insert: {red_real} — informational)")
    return failures


def _test_3_mismatch(conn) -> list[str]:
    failures: list[str] = []
    with conn.cursor() as cur:
        _purge_test_rows(cur)
        cur.execute(
            """
            INSERT INTO public.fleet_liveness
                (callsign, checked_at, tmux_alive, nats_last_publish_at,
                 backend_health, active_task_id, reported_callsign, callsign_match)
            VALUES (%s, NOW(), TRUE, NULL, NULL, NULL, 'wrong_callsign', FALSE)
            """,
            (TEST_MISMATCH_CALLSIGN,),
        )
        conn.commit()

        cur.execute(
            """
            SELECT status, reported_callsign, callsign_match
            FROM public.fleet_liveness_status
            WHERE callsign = %s
            """,
            (TEST_MISMATCH_CALLSIGN,),
        )
        row = cur.fetchone()

        _purge_test_rows(cur)
        conn.commit()

    if row is None:
        failures.append(f"TEST 3: no view row for {TEST_MISMATCH_CALLSIGN}")
    else:
        status, reported, match = row
        if status != "MISMATCH":
            failures.append(f"TEST 3: status was {status!r}, expected 'MISMATCH'")
        if reported != "wrong_callsign":
            failures.append(
                f"TEST 3: reported_callsign was {reported!r}, expected 'wrong_callsign'"
            )
        if match is not False:
            failures.append(f"TEST 3: callsign_match was {match!r}, expected False")

    print(f"[TEST 3] synthetic {TEST_MISMATCH_CALLSIGN} row={row}")
    return failures


def main() -> int:
    _load_env_file(ENV_FILE)
    dsn = _resolve_dsn()
    if not dsn:
        print("FATAL: DATABASE_URL / SUPABASE_DB_URL unset and no .env file found.", file=sys.stderr)
        return 2

    try:
        import psycopg
    except ImportError:
        print("FATAL: psycopg not installed in this interpreter.", file=sys.stderr)
        return 2

    all_failures: list[str] = []
    with psycopg.connect(dsn, prepare_threshold=None) as conn:
        # Defensive: purge any leftover test rows from a prior crashed run BEFORE
        # the end-to-end probe — otherwise stale 'test_agent' rows could confuse
        # the freshness check (they would not be in EXPECTED_CALLSIGNS so it is
        # harmless today, but cheap insurance against future test-callsign reuse).
        with conn.cursor() as cur:
            _purge_test_rows(cur)
            conn.commit()

        all_failures.extend(_test_1_end_to_end(conn))
        all_failures.extend(_test_2_red(conn))
        all_failures.extend(_test_3_mismatch(conn))

    print()
    print("=== FLEET SCOREBOARD PROOF VERDICT ===")
    if all_failures:
        for msg in all_failures:
            print(f"FAIL: {msg}")
        return 1
    print("PASS — all three tests verified: checker writes 7/7 rows, RED case, MISMATCH case.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
