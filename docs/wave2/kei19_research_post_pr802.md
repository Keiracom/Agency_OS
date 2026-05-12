# KEI-19 vs PR #802 — Coverage Map + Gap Analysis

## KEI-19 verbatim (Linear GraphQL pull 2026-05-12)

```
identifier: KEI-19
title:       Rate limit alerting: auto-post to #ceo on agent throttle
state:       Todo
description: Add Anthropic rate-limit detection to the polling loop.
             When any agent hits a rate limit, immediately post to #ceo
             with callsign, wait duration, and auto-clear notification
             when they resume. Dave should never have to manually check
             to find throttled agents.
```

## PR #802 verbatim coverage (merge sha `5b223065`, merged 2026-05-12T21:19:16Z)

| KEI-19 requirement | PR #802 implementation | Status |
|---|---|---|
| Add rate-limit detection to polling loop | `poll_rate_limited_agents()` in `scripts/orchestrator/elliot_polling_loop.py` | ✅ |
| Detect when ANY agent hits rate limit | `CALLSIGN_TO_TMUX` covers all 6 (elliot=elliottbot, max=maxbot, others=name) | ✅ |
| Immediately post to `#ceo` | `compose_dispatches()` appends `(CEO_CHANNEL_NAME, msg)` on `clean→throttled` | ✅ |
| Include callsign | Names joined into dispatch text: `f"…{len(throttled)} agent(s): {names}"` | ✅ |
| Include **wait duration** | **Throttle-onset dispatch has NO duration**: text is `"informational not actionable"`. Duration only computed retrospectively on resume. | ❌ **GAP A** |
| Auto-clear on resume | `throttled→clean` emits resumed dispatch with `f"resumed after {dur}m throttle"` | ✅ |
| "Dave never manually checks" | Auto-post mechanism covers; but onset-dispatch labelled "informational not actionable" subtly downgrades urgency | ⚠️ **GAP B** (wording) |

## Gaps (line/file refs)

### GAP A — wait duration missing at throttle-onset

Source: `scripts/orchestrator/elliot_polling_loop.py` (PR #802 diff, dispatch composition):
```python
msg = (
    f"[PROPOSE:elliot] Anthropic throttle detected — {len(throttled)} agent(s): {names}.\n"
    f"Throttle signal grep on tmux pane tail (rate limit / 429 / retry-after / brewed). "
    f"Agents will resume on next clean cycle; this is informational not actionable."
)
```
The regex `THROTTLE_PATTERNS = ('rate limit', r'\b429\b', 'retry-?after', 'brewed for')` matches as substrings but the surrounding numeric duration (`retry-after: 90`, `brewed for 5 minutes`) is **not extracted**. KEI-19 verbatim asks for "wait duration" — currently None on the initial alert. Fix: add capture groups to the THROTTLE_RE patterns, surface in dispatch text. ~15-20 LoC.

### GAP B — "informational not actionable" wording contradicts KEI-19 intent

KEI-19's premise is that Dave should be alerted because he otherwise has to manually check. Calling the alert "informational not actionable" undermines that framing. Trivial wording change. Suggested: `"throttled — wait Xm before retry; auto-clearing on resume"` once GAP A's duration is parsed.

### GAP C (residual, lower priority)

- **Visibility-bound detection.** Pane capture only sees the last 10 lines. A throttle banner that scrolled off mid-tool-call would be missed. PR #802's body acknowledges this tradeoff. Not strictly a KEI-19 gap; flagging as residual risk.
- **State-file corruption silently fail-open.** `_load_throttle_state` warns on JSON decode error and returns `{}` — every callsign appears un-throttled, so any subsequent throttle re-fires `clean→throttled` (re-alert), not silent miss. Acceptable degradation.

## Recommendation

**KEI-19 is NOT fully covered by PR #802.** GAP A (wait duration absent at throttle-onset) is the core unmet requirement from the verbatim description. GAP B is a wording follow-up that pairs naturally with the GAP A patch.

Suggested CTO dispatch (Aiden's lane, build only):
- Patch `THROTTLE_PATTERNS` → add named capture groups for duration values.
- Patch `poll_rate_limited_agents()` → return `(callsign, transition, duration_min, source)` 4-tuple instead of 3-tuple (source ∈ `{retry_after, brewed_for, unknown}`).
- Patch throttle-onset dispatch text to surface duration; reword to drop "informational not actionable".
- 1 new test: `test_poll_rate_limited_parses_retry_after_seconds` + `test_poll_rate_limited_parses_brewed_for_minutes`.
- Expected diff: ~30-40 LoC in `elliot_polling_loop.py` + ~30 LoC tests.

After patch: KEI-19 can be closed.
