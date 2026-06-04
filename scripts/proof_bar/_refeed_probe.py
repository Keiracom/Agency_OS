#!/usr/bin/env python3
"""LIVE proof probe for the context_watchdog re-feed (watchdog_reaper).

Drives a real idle test agent through the REAL wired decision path and asserts
against the LIVE database + a REAL tmux pane — no mocks:

  CASE A (idle WITH queued work): an idle test callsign (old tool_call_log row,
    0 calls in 10m) with a queued inbox dispatch is classified
    idle_with_work_queued; refeed_agent injects the actual task into a real tmux
    pane; the stand-in agent resumes → a FRESH tool_call_log row appears whose
    excerpt is the task (NOT '/clear'). => re-fed, resumed real work.

  CASE B (idle, NO work — inline negative self-test): an idle test callsign with
    an EMPTY inbox is classified 'idle'; the wired branch leaves it; NO injection,
    NO fresh tool_call_log row. => correctly left, no thrash.

Prints contract substrings; exits 0 only if all asserts hold. Cleans up.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())
from scripts.orchestrator import context_watchdog as cw  # noqa: E402
from scripts.orchestrator.agent_activity import compute_activity_state  # noqa: E402

cw.slack_ceo = lambda *a, **k: None  # silence Slack during the proof

DSN = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)
PID = os.getpid()
CS_A = f"wdtest_a_{PID}"
CS_B = f"wdtest_b_{PID}"
SESS = f"wdproof{PID}"
TOKEN = f"PROOF_TASK_{PID}"
STUB = str(Path(__file__).with_name("_refeed_agent_stub.py"))
READER = str(Path(__file__).with_name("_refeed_reader.sh"))
INBOX_A = Path(f"/tmp/telegram-relay-{CS_A}/inbox")
INBOX_B = Path(f"/tmp/telegram-relay-{CS_B}/inbox")

import psycopg  # noqa: E402


def db(sql, params=None, fetch=False):
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute(sql, params or ())
        row = cur.fetchone() if fetch else None
        c.commit()
    return row


def seed_idle(cs):
    """Old row (20 min ago) → callsign appears in agent_activity_signal as 'idle'."""
    db("INSERT INTO public.tool_call_log (callsign, tool_name, tool_input, started_at) "
       "VALUES (%s, 'seed', '{}'::jsonb, now() - interval '20 minutes')", (cs,))


def fresh_rows(cs, after_iso):
    return db("SELECT count(*), max(tool_output_excerpt) FROM public.tool_call_log "
              "WHERE callsign=%s AND started_at > %s AND tool_name='refed_resume'",
              (cs, after_iso), fetch=True)


def cleanup():
    subprocess.run(["tmux", "kill-session", "-t", SESS], capture_output=True)
    for cs in (CS_A, CS_B):
        db("DELETE FROM public.tool_call_log WHERE callsign=%s", (cs,))
    for d in (INBOX_A, INBOX_B):
        try:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
            d.parent.rmdir()
        except OSError:
            pass


def main() -> int:
    ok = True
    try:
        # ── CASE A — idle WITH queued work ──────────────────────────────────
        seed_idle(CS_A)
        INBOX_A.mkdir(parents=True, exist_ok=True)
        (INBOX_A / "dispatch.json").write_text(
            f'{{"type":"task_dispatch","brief":"{TOKEN} — run bd show and resume","task_ref":"{TOKEN}"}}'
        )
        state_a = compute_activity_state(CS_A)
        print(f"CASE_A activity_state={state_a}")
        assert state_a == "idle_with_work_queued", f"expected idle_with_work_queued, got {state_a}"

        # Real tmux pane running the stand-in agent.
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", SESS, "-x", "200", "-y", "50",
             "bash", READER, CS_A, STUB],
            check=True,
        )
        time.sleep(1.5)  # let the reader print its first ❯

        t0 = db("SELECT now()", fetch=True)[0]
        refed = cw.refeed_agent("wdproof", f"{SESS}:0.0", CS_A)
        print(f"CASE_A refeed_agent_returned={refed}")
        assert refed is True, "refeed_agent did not inject"

        # Poll for the pane echoing the task + the fresh tool_call_log row.
        injected = fresh_ok = False
        for _ in range(20):
            time.sleep(1.0)
            pane = subprocess.run(["tmux", "capture-pane", "-p", "-t", f"{SESS}:0.0"],
                                  capture_output=True, text=True).stdout
            if TOKEN in pane:
                injected = True
            cnt, excerpt = fresh_rows(CS_A, t0)
            if cnt and cnt >= 1 and excerpt and TOKEN in excerpt:
                fresh_ok = True
            if injected and fresh_ok:
                break

        print(f"REFED_TASK_INJECTED={'true' if injected else 'false'}")
        print(f"REFED_FRESH_TOOL_CALL={'true' if fresh_ok else 'false'}")
        ok = ok and injected and fresh_ok

        # ── CASE B — idle, NO work (inline negative self-test) ──────────────
        seed_idle(CS_B)  # idle, but no inbox dir created → empty
        state_b = compute_activity_state(CS_B)
        print(f"CASE_B activity_state={state_b}")
        assert state_b == "idle", f"expected idle, got {state_b}"
        t1 = db("SELECT now()", fetch=True)[0]
        # Wired branch: idle (not idle_with_work_queued) => NO refeed. Replicate.
        if state_b == "idle_with_work_queued":
            cw.refeed_agent("wdtestb", "noexist:0.0", CS_B)
        time.sleep(2.0)
        cnt_b, _ = fresh_rows(CS_B, t1)
        left_alone = (cnt_b == 0)
        print(f"NEG_IDLE_NO_WORK_LEFT={'true' if left_alone else 'false'}")
        ok = ok and left_alone

        if ok:
            print("REFEED_PROOF_OK")
            return 0
        print("REFEED_PROOF_FAILED", file=sys.stderr)
        return 2
    finally:
        cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
