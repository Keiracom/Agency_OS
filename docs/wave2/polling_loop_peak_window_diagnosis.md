# Polling Loop Peak-Window Diagnosis

Source: `scripts/orchestrator/elliot_polling_loop.py` (read fresh 2026-05-12 21:14 UTC).

## Headline: not a code bug — a deployment-staleness bug

`should_run_now()` at lines 94-103 is correct. `PEAK_HOURS_UTC` at line 50 is correct. The observed "outside peak window" log at UTC 13:35 was emitted by a STALE checkout of the file — auto-pull-main had been silently skipping the worktree for the entire window after PR #782 merged.

## Empirical repro

### Time arithmetic is correct in the current file

```
$ /home/elliotbot/clawd/venv/bin/python3 -c "
from datetime import datetime, UTC
PEAK_HOURS_UTC = set(list(range(21, 24)) + list(range(0, 14)))
print('PEAK_HOURS_UTC =', sorted(PEAK_HOURS_UTC))
for h in [12, 13, 14, 20, 21]:
    print(f'  hour={h}: in peak = {h in PEAK_HOURS_UTC}')"
PEAK_HOURS_UTC = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 21, 22, 23]
  hour=12: in peak = True
  hour=13: in peak = True       ← matches dispatch hypothesis
  hour=14: in peak = False
  hour=20: in peak = False
  hour=21: in peak = True
```

### Auto-pull-main was skipping main throughout the bug window

```
$ journalctl --user -u agency-os-auto-pull-main.service \
    --since '2026-05-12 12:30:00' --until '2026-05-12 14:00:00' -o short-iso
2026-05-12T12:31:59+00:00 ... SKIP /home/elliotbot/clawd/Agency_OS: working tree dirty
2026-05-12T12:37:29+00:00 ... SKIP /home/elliotbot/clawd/Agency_OS: working tree dirty
2026-05-12T12:43:09+00:00 ... SKIP /home/elliotbot/clawd/Agency_OS: working tree dirty
2026-05-12T12:48:29+00:00 ... SKIP /home/elliotbot/clawd/Agency_OS: working tree dirty
2026-05-12T12:53:49+00:00 ... SKIP /home/elliotbot/clawd/Agency_OS: working tree dirty
[…continues skipping past 13:35 UTC observation window…]
```

### The schedule update was on origin at 12:31 UTC but never reached the worktree

```
$ git -C /home/elliotbot/clawd/Agency_OS show ba769083 \
    -- scripts/orchestrator/elliot_polling_loop.py | grep PEAK_HOURS_UTC
-PEAK_HOURS_UTC = set(list(range(21, 24)) + list(range(0, 11)))  # 21–10 UTC inclusive
+PEAK_HOURS_UTC = set(list(range(21, 24)) + list(range(0, 14)))  # 21–13 UTC inclusive = 07–23 AEST
```

PR #782 ("KEI-17 schedule update — peak 07-24 AEST") merged 2026-05-12 12:31 UTC. Auto-pull immediately tried to pull (12:31:59) but **skipped** because main was dirty. Every subsequent pull (12:37, 12:43, 12:48, 12:53, …) also skipped. So during the 13:35 observation the on-disk file was still the **pre-#782** version with `range(0, 11)` — under which hour 13 is correctly NOT in peak.

## Root cause (line-numbered)

| Layer | Where | What |
|---|---|---|
| Code | `elliot_polling_loop.py:50` + `:94-103` | Correct. No fix needed. |
| Deployment | systemd unit `agency-os-auto-pull-main.service` | SKIPs on dirty tree, silently. Reader-side enablement gap (Pattern A). |
| Worktree state | `/home/elliotbot/clawd/Agency_OS` | Was dirty during the bug window (uncommitted files blocking ff-only pull). |

## Suggested fix (Aiden builds; this is the design)

1. **Make auto-pull-main loud, not silent on SKIP.** In the auto-pull script (the env-running one at `agency-os-auto-pull-main.service`), when a SKIP happens for >N consecutive runs, post to `#execution` with the reason. Cheap: add a counter file at `~/.local/state/agency-os/auto-pull-main.skip-streak`; reset on success; alert at threshold (e.g. ≥3 consecutive skips = 15 min stale).
2. **Defense-in-depth — log effective PEAK_HOURS_UTC at startup of each cycle.** Single-line addition near line 380: `logger.info("PEAK_HOURS_UTC=%s now=%s", sorted(PEAK_HOURS_UTC), n.isoformat())`. Future drift between code and runtime becomes diff-able from log alone. Costs nothing.
3. **No Python bug to patch.** The hour/tz logic at lines 94-103 is correct (`datetime.now(UTC)`, no `utcnow()`, set membership is integer). Don't refactor or "fix" the function itself.

Net: 1 ops change (auto-pull alerting), 1 log-line addition. Don't touch `should_run_now()`.

## Out of scope but worth flagging

- The aiden-worktree skip ("on aiden/betterstack-integration (only auto-pull when on main)") is intentional design — feature branches don't auto-pull. Not a bug.
- 3 distinct hashes for `elliot_polling_loop.py` exist across worktrees (main/max/atlas match, aiden + orion differ). Independent worktree-sync concern, separate dispatch.
