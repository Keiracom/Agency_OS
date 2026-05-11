# Deprecated Rule: R1 — CONCUR-BEFORE-SUMMARY

**Retired:** 2026-05-11 via PR #697
**Replaced by:** `src/bot_common/concur_gate.py` (PR #685) — deterministic outbound gate

## Incident that created this rule

Early in the dual-bot era (Aiden + Elliot operating in parallel on Telegram), peer agents independently posted "complete" / "done" status reports to Dave for overlapping work. Dave received conflicting summaries within minutes of each other — neither bot knew the other had reported, and the second post's content silently overrode the first's framing in Dave's mental model.

R1 was added to enforce explicit peer concurrence before any Dave-facing summary or recommendation post.

Repeated specifically on 2026-05-11 session: 18 R1 fires in one session with ~70% false-positive rate (per Max audit). Pattern was the LLM check firing on peer-to-peer coordination posts that weren't actually Dave-directed, plus genuine concurrence races during high-throughput cycles.

## Original RULES_PROMPT text (verbatim, pre-retirement)

```
Rule 1 — CONCUR-BEFORE-SUMMARY: If a bot's message is a SUMMARY, RECOMMENDATION, OR completion report directed at Dave (in #ceo or addressed by name in #execution), check recent_messages for explicit peer [CONCUR:<callsign>] tags from BOTH other peers (Aiden + Elliot + Max — 3-way concur ratified 2026-05-11). Missing peer concur = VIOLATION.

EXCEPTIONS (always PASS):
  (i)   Concur requests + draft posts ([SUMMARY-DRAFT:<callsign>], [CONCUR-REQUEST:<callsign>]) themselves
  (ii)  Bare acknowledgements ("ack", "concur", "received", "on it", "holding")
  (iii) Peer-to-peer #execution status updates that don't address Dave directly
  (iv)  Direct factual answers to a specific Dave question (yes/no, single line)
  (v)   Results report on action taken under explicit Dave directive — narrow scope, factual content only
```

## Why this is safe to retire

`concur_gate.py` imports the SAME `TRIGGER_PATTERNS` from `enforcer_rules.py` that the LLM R1 check used. Coverage is bit-identical. The gate runs BEFORE `chat.postMessage`, so:

- Triggered messages are HELD at the relay layer (deterministic refuse-to-post)
- Bypass for `[CONCUR]` / `[COUNTER]` / `[SUMMARY-DRAFT]` / `ack` patterns matches the R1 exceptions verbatim
- Outbound gate failure-mode is fail-closed (script exits 2 with `R1_BLOCKED` if peer concur is missing)

LLM R1 was post-hoc detection of what the gate already prevents. ~70% FP rate vs deterministic gate's 0% FP (it either matches the trigger pattern or doesn't) makes the LLM net-negative for the same protection.

## Verification

```bash
# Confirm concur_gate uses the same TRIGGER_PATTERNS:
grep -n 'TRIGGER_PATTERNS' src/bot_common/concur_gate.py
# Expected: import from enforcer_rules + `any(p in lower for p in TRIGGER_PATTERNS)` check

# Confirm LLM R1 path removed in central_listener:
grep -n 'Rule 1\|R1' src/slack_bot/central_listener.py
# Expected: explicit skip path when R1 trigger detected (concur_gate handles), no LLM call
```

## What to watch for

If peer agents start posting Dave-facing summaries without peer concur AND the gate doesn't block them — investigate:
1. Is the gate being bypassed via `CONCUR_GATE_SKIP=1` env (legitimate one-shot evidence reports use this)?
2. Did `TRIGGER_PATTERNS` get accidentally narrowed?
3. Did the gate's outbound integration get bypassed (e.g., new relay script that doesn't call `gate_check`)?

If gate is structurally bypassed, restore the LLM R1 check as a fallback while diagnosing.
