#!/usr/bin/env python3
"""test_fleet_scoreboard.py — Proof gate for the fleet liveness scoreboard.

Re-runnable end-to-end proof that the on-box checker + the
public.fleet_liveness_status view honestly classify per-agent identity.

Four tests, all must pass:

  TEST 0 (timer liveness — NEW):
    Verify the fleet-liveness-checker.timer Trigger is not 'n/a' (i.e. the
    timer is armed and will fire), then wait up to 6 minutes for the timer
    to fire naturally. A fresh row in public.fleet_liveness with
    checked_at > the gate start time is the success condition. Proves the
    timer is doing the writing — not a manual subprocess invocation that
    masks a broken systemd unit.

  TEST 1 (live per-agent callsign correctness — NEW):
    For every callsign in EXPECTED_CALLSIGNS, query the LATEST row in
    fleet_liveness (DISTINCT ON callsign, ORDER BY checked_at DESC) and
    assert reported_callsign == callsign exactly. This is the regression
    test for the BFS depth-0 bug where the pane shell's inherited
    CALLSIGN was returned instead of the claude child's. Prints verbatim
    per-agent rows so reviewers can audit live values not summaries.

  TEST 2 (synthetic RED detection):
    INSERT a synthetic fleet_liveness row for callsign='test_agent' with
    tmux_alive=FALSE, checked_at=NOW(). Verify the view emits status='RED'.
    Synthetic row purged in a try/finally so cleanup always runs.

  TEST 3 (synthetic MISMATCH detection):
    INSERT a synthetic row for callsign='test_agent2' with tmux_alive=TRUE
    and callsign_match=FALSE. Verify the view emits status='MISMATCH'.
    Synthetic row purged in try/finally.

Exit 0 if every test passes. Exit 1 with a labelled failure list otherwise.

Anchor: KEI Agency_OS-scout fleet-scoreboard-p0 dispatch from Elliot
2026-06-02 (BFS depth-0 fix). Reviewers: aiden + max on LIVE data.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = Path.home() / ".config" / "agency-os" / ".env"

EXPECTED_CALLSIGNS = ["elliot", "aiden", "max", "atlas", "orion", "scout", "nova"]
TEST_RED_CALLSIGN = "test_agent"
TEST_MISMATCH_CALLSIGN = "test_agent2"
TEST_CALLSIGNS = (TEST_RED_CALLSIGN, TEST_MISMATCH_CALLSIGN)
TIMER_UNIT = "fleet-liveness-checker.timer"
TIMER_WAIT_MAX_SEC = 6 * 60
TIMER_POLL_INTERVAL_SEC = 10


def _load_env_file(path: Path) -> None:
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


def _timer_next_fire_label() -> str | None:
    """Return the NEXT-column label from `systemctl list-timers`, or None if disarmed.

    `systemctl --user show ... -p NextElapseUSecMonotonic` renders durations
    (e.g. '4d 7h 30min 10.8s') not raw integers, so we fall back to parsing
    `list-timers` which prints absolute timestamps. A disarmed timer shows
    NEXT='-' or omits the row entirely.
    """
    try:
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "list-timers",
                TIMER_UNIT,
                "--no-pager",
                "--no-legend",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"[TEST 0] systemctl list-timers failed: {exc}", file=sys.stderr)
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("0 timers"):
            continue
        # The NEXT column is the first whitespace-delimited token (or '-').
        next_field = line.split()[0] if line.split() else "-"
        if next_field == "-":
            return None
        return line  # return the whole row for printing context
    return None


def _test_0_timer(conn) -> list[str]:
    failures: list[str] = []
    next_label = _timer_next_fire_label()
    if next_label is None:
        failures.append(
            f"TEST 0: {TIMER_UNIT} has no scheduled next fire (Trigger 'n/a' — "
            "timer is disarmed). Run `systemctl --user start "
            "fleet-liveness-checker.service` once to anchor OnUnitActiveSec."
        )
        return failures
    print(f"[TEST 0] timer armed — list-timers row: {next_label}")

    start_time = datetime.now(UTC)
    with conn.cursor() as cur:
        cur.execute("SELECT NOW()")
        db_start = cur.fetchone()[0]
    print(f"[TEST 0] gate start: local={start_time.isoformat()} db={db_start.isoformat()}")
    print(f"[TEST 0] waiting up to {TIMER_WAIT_MAX_SEC // 60}min for natural timer fire...")

    deadline = time.monotonic() + TIMER_WAIT_MAX_SEC
    fresh_callsign = None
    fresh_at = None
    while time.monotonic() < deadline:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT callsign, checked_at
                FROM public.fleet_liveness
                WHERE checked_at > %s AND callsign = ANY(%s)
                ORDER BY checked_at DESC
                LIMIT 1
                """,
                (db_start, EXPECTED_CALLSIGNS),
            )
            row = cur.fetchone()
        if row:
            fresh_callsign, fresh_at = row[0], row[1]
            break
        elapsed = TIMER_WAIT_MAX_SEC - int(deadline - time.monotonic())
        print(f"[TEST 0]   ...no fresh row yet (waited {elapsed}s)")
        time.sleep(TIMER_POLL_INTERVAL_SEC)

    if fresh_callsign is None:
        failures.append(
            f"TEST 0: no fleet_liveness row with checked_at > {db_start.isoformat()} "
            f"after {TIMER_WAIT_MAX_SEC}s. Timer did not fire."
        )
    else:
        print(f"[TEST 0] timer fired — first fresh row: {fresh_callsign} @ {fresh_at.isoformat()}")
    return failures


def _test_1_live_callsigns(conn) -> list[str]:
    failures: list[str] = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (callsign)
                callsign, reported_callsign, callsign_match, tmux_alive, checked_at
            FROM public.fleet_liveness
            WHERE callsign = ANY(%s)
            ORDER BY callsign, checked_at DESC
            """,
            (EXPECTED_CALLSIGNS,),
        )
        rows = cur.fetchall()

    by_callsign = {r[0]: r for r in rows}
    print("[TEST 1] per-agent latest rows (verbatim):")
    print(
        f"         {'callsign':<8} {'reported_callsign':<20} "
        f"{'callsign_match':<14} {'tmux_alive':<10} checked_at"
    )
    for cs in EXPECTED_CALLSIGNS:
        row = by_callsign.get(cs)
        if row is None:
            print(f"         {cs:<8} <NO ROW>")
            failures.append(f"TEST 1: no fleet_liveness row found for callsign={cs!r}")
            continue
        callsign, reported, match, tmux_alive, checked_at = row
        print(
            f"         {callsign:<8} {str(reported):<20} "
            f"{str(match):<14} {str(tmux_alive):<10} {checked_at.isoformat()}"
        )
        if reported != callsign:
            failures.append(
                f"TEST 1: callsign={callsign!r} reported_callsign={reported!r} "
                f"(expected {callsign!r}, tmux_alive={tmux_alive}, "
                f"checked_at={checked_at.isoformat()})"
            )
    return failures


def _test_2_red(conn) -> list[str]:
    failures: list[str] = []
    row = None
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

        try:
            cur.execute(
                "SELECT status FROM public.fleet_liveness_status WHERE callsign = %s",
                (TEST_RED_CALLSIGN,),
            )
            row = cur.fetchone()
        finally:
            _purge_test_rows(cur)
            conn.commit()

    if row is None:
        failures.append(f"TEST 2: no view row for {TEST_RED_CALLSIGN}")
    elif row[0] != "RED":
        failures.append(f"TEST 2: status was {row[0]!r}, expected 'RED'")
    print(f"[TEST 2] synthetic {TEST_RED_CALLSIGN} status={row[0] if row else 'NULL'}")
    return failures


def _test_3_mismatch(conn) -> list[str]:
    failures: list[str] = []
    row = None
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

        try:
            cur.execute(
                """
                SELECT status, reported_callsign, callsign_match
                FROM public.fleet_liveness_status
                WHERE callsign = %s
                """,
                (TEST_MISMATCH_CALLSIGN,),
            )
            row = cur.fetchone()
        finally:
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
        with conn.cursor() as cur:
            _purge_test_rows(cur)
            conn.commit()

        all_failures.extend(_test_0_timer(conn))
        # TEST 1 reads the latest row per callsign; running it after TEST 0
        # means the latest rows reflect a timer-fired write, not a stale
        # pre-fix snapshot.
        all_failures.extend(_test_1_live_callsigns(conn))
        all_failures.extend(_test_2_red(conn))
        all_failures.extend(_test_3_mismatch(conn))

    print()
    print("=== FLEET SCOREBOARD PROOF VERDICT ===")
    if all_failures:
        for msg in all_failures:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS — TEST 0 timer fired naturally, TEST 1 all 7 callsigns reported "
        "correctly, TEST 2 RED, TEST 3 MISMATCH."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
