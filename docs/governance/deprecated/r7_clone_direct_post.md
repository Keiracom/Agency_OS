# Deprecated Rule: R7 — CLONE-DIRECT-GROUP-POST

**Retired:** 2026-05-11 via PR #1b (TBD)
**Replaced by:** Structural prevention (clones have no Slack write paths; outbound flows via parent's outbox by design)

## Incident that created this rule

In the Telegram-relay era, ATLAS and ORION clones occasionally posted directly to the team supergroup via an inotify side-effect (their outbox writes triggered the central relay watcher which forwarded them to Telegram). This bypassed the C3 clone rule "parent surfaces clone artefacts via `[CONSUMED:<parent>]` post" — Dave would see a `[ATLAS]`-prefixed message in the group as if the clone were a primary participant.

R7 was added to flag any clone-direct-post in the group, enforcing the parent-relay model.

## Original RULES_PROMPT text (verbatim, pre-retirement)

```
Rule 7 — CLONE-DIRECT-GROUP-POST: If the message SENDER is a CLONE (callsign attribution returns "atlas" or "orion"), flag as VIOLATION — clones must not post to group per C3. Parent surfaces clone artefacts via `[CONSUMED:<parent>]` post. NOTE: MAX is a PRIME agent (CTO), NOT a clone. [MAX] prefixed messages are legitimate group posts. Only ATLAS and ORION are clones.
SCOPE — Rule 7 ONLY triggers on SENDER attribution, NOT on mentions of clone names:
  TRIGGER: sender resolves to atlas/orion (via enforcer_callsign_map.attribute()) OR message text begins with `[ATLAS]` / `[ORION]` (clone-prefix self-tag).
  EXEMPT (always PASS — legitimate references):
    (i)   Mentions of ATLAS/ORION as WORKSPACE NAMES (e.g. "edited _session_start.md in Atlas worktree", "Agency_OS-atlas/scripts/X") — these are filesystem paths or workspace identifiers, not clone posts.
    (ii)  Dispatch coordination posts ("ATLAS dispatched", "ORION queued") posted by parent callsigns (Elliot/Aiden/Max) — these report on clone work, don't BE clone work.
    (iii) `[CONSUMED:<parent>]` parent-surfacing posts — explicitly allowed pattern.
    (iv)  Discussions about clone migration, clone Rules, clone architecture from any non-clone sender.
```

## Why this is safe to retire

The Slack migration (AIDEN-SLACK-MIGRATION-001, 2026-05-11) eliminated the failure mode structurally:

1. **Clones have no Slack write paths.** Clones (ATLAS/ORION) communicate only via the inbox/outbox filesystem pattern — they write to `/tmp/telegram-relay-<clone>/outbox/` and have no `slack_relay.py` access. There's no path for a clone to invoke `chat.postMessage` directly.

2. **Outbox→Slack mirror is parent-callsign only.** `aiden_slack_mirror.py` watches `/tmp/telegram-relay-aiden/outbox/` (Aiden parent), not the clone outboxes. ORION outbox writes never reach Slack.

3. **Central listener routes by channel→callsign matrix, not by sender.** A hypothetical clone post wouldn't pass the matrix routing because clones aren't in the `[elliot, aiden, max]` routing targets.

4. **Zero non-FP R7 fires this session.** All R7 fires today were false positives on `[MAX]`-tagged messages (Max is PRIME, not a clone) or on workspace-name mentions in body text. The structural prevention is already complete; the LLM check produced only noise.

## Verification

```bash
# Confirm clones have no slack_relay access:
ls /home/elliotbot/clawd/Agency_OS-atlas/scripts/slack_relay.py 2>&1
ls /home/elliotbot/clawd/Agency_OS-orion/scripts/slack_relay.py 2>&1
# Expected: not found OR present-but-no-Slack-token-in-clone-env

# Confirm Slack mirror only watches parent outboxes:
grep -l 'telegram-relay-atlas\|telegram-relay-orion' scripts/*slack_mirror*.py 2>&1
# Expected: no matches (mirrors watch parent outboxes only)

# Confirm zero R7 fires when sender is genuinely a clone (vs FPs on text mentions):
grep 'Rule 7' /home/elliotbot/clawd/logs/aiden-slack-listener.log | grep -v 'workspace\|MAX\|mention'
# Expected: 0 in recent windows
```

## What to watch for

If a clone produces a Slack post that lands in `#execution` / `#ceo` / etc. — the architecture has changed. Investigate:
1. Did ATLAS/ORION get their own Slack bot tokens?
2. Did a relay watcher start polling clone outboxes for Slack mirroring?
3. Did the central listener routing matrix accidentally include clones?

If clone-direct-post recurs, restore R7 as a deterministic check on the sender attribute (`event.user` / `bot_id` → `enforcer_callsign_map.attribute()` → reject if returns "atlas"/"orion"). That was the proposed implementation before retirement.
