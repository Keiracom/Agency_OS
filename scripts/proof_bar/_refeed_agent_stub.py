#!/usr/bin/env python3
"""Stand-in "agent" for the context_watchdog re-feed live proof.

The proof's tmux test pane runs _refeed_reader.sh, which calls this once per
line injected into the pane. It writes ONE tool_call_log row for the test
callsign IFF the injected line is real work (a task brief) — NOT a bare
'/clear' and NOT an empty Enter. This is what makes the proof assert the
dispatch's exact requirement: a re-fed agent emits a FRESH tool_call_log row
because it RESUMED REAL WORK, not because a tab was cleared.

Env: REFED_LINE (the injected line), TEST_CS (test callsign), DATABASE_URL.
"""
import os
import sys

line = os.environ.get("REFED_LINE", "").strip()
cs = os.environ.get("TEST_CS", "")
dsn = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)

# A cleared tab / empty Enter is NOT resumed work — record nothing.
if not line or line == "/clear" or not cs or not dsn:
    sys.exit(0)

try:
    import psycopg
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.tool_call_log "
            "(callsign, tool_name, tool_input, tool_output_excerpt, started_at) "
            "VALUES (%s, 'refed_resume', '{}'::jsonb, %s, now())",
            (cs, line[:200]),
        )
        conn.commit()
except Exception as exc:  # noqa: BLE001 — proof harness; surface to stderr
    print(f"stub insert failed: {exc}", file=sys.stderr)
    sys.exit(1)
