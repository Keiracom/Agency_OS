# ENFORCER Slack Cutover — Operational README

## Overview

Two systemd units run concurrently during the Slack enforcer transition. The legacy Telegram unit (`enforcer-bot.service`) remains until Phase D; the new Slack unit (`enforcer-bot-slack.service`) starts in observe-only mode and progressively takes over enforcement duties.

## Units in Play

| Unit                           | Source                                | Mode               |
| ------------------------------ | ------------------------------------- | ------------------- |
| `enforcer-bot.service`         | `/home/elliotbot/clawd/Agency_OS` (existing) | TG polling (active until Phase D) |
| `enforcer-bot-slack.service`   | `/home/elliotbot/clawd/Agency_OS-atlas` | Slack Socket Mode (begins Phase A) |

**Do NOT touch** existing `~/.config/systemd/user/aiden-slack-mirror.service` or the TG `enforcer-bot.service` unit file. The Slack unit runs alongside them.

## Cutover Phases

| Phase | State                                    | Duration | Exit Criterion |
|-------|------------------------------------------|----------|---|
| A     | TG live + Slack observe-only             | 24h      | Slack & TG flag rates within ±10% on same rules; no Slack crashes |
| B     | Both live (dual-post). Both interject.   | 24h      | No duplicate-flag complaints from Dave or bots |
| C     | Slack live, TG observe-only. **Cross-device deliberate-violation test** | 1-2h | All 9 rules flagged at least once from phone AND laptop |
| D     | Slack live, TG service stopped + masked | 48h      | Stable on Slack alone → TG unit removed from disk |

## Phase A → Phase B Flip

When Phase A exit criteria are met, flip `ENFORCER_OBSERVE_ONLY=1` off:

```bash
systemctl --user edit enforcer-bot-slack.service
```

In the editor, **remove or comment out** the line:
```ini
Environment="ENFORCER_OBSERVE_ONLY=1"
```

Save and exit. Then reload and restart:

```bash
systemctl --user daemon-reload
systemctl --user restart enforcer-bot-slack.service
```

**Verification:** `journalctl --user -u enforcer-bot-slack.service -f` should show Socket Mode connected and **active interjections** (not `OBSERVE:` prefixed) on the next rule violation in `#execution` or `#alerts`.

## Phase C Smoke Test Procedure

**Objective:** Verify all 9 rules are correctly enforced from both phone and laptop devices.

**Setup:**
1. Dave is logged into Slack on **phone** and **laptop** (different sessions, same workspace).
2. Both devices have access to `#execution` and `#alerts` channels.

**Process:**
For each rule R1–R9:
1. Dave posts a deliberate violation (rule-specific message) to `#execution` from the **phone**.
2. Within 5 seconds, the enforcer should flag the message in a **thread** on the violating message.
   - Expected interjection format: `[ENFORCER] Rule N — <NAME>: <detail>. <should_have>.`
   - Thread anchor: the violating message.ts.
3. Repeat from the **laptop**.
4. For rules R3, R6, R7 (which fire in both channels), also test in `#alerts`.

**Expected outcome:**
- All 9 rules flagged at least once from **phone**.
- All 9 rules flagged at least once from **laptop**.
- Every flag lands in a thread on the original violating message.
- No duplicate flags within 300s (cooldown window).

**Verification:**
Query `public.governance_events` for the enforcement run:

```sql
SELECT rule_id, COUNT(*) as flag_count, array_agg(DISTINCT channel) as channels
FROM public.governance_events
WHERE source='enforcer' AND created_at > NOW() - INTERVAL '2 hours'
GROUP BY rule_id
ORDER BY rule_id;
```

Expected: 9 rows, one per rule, with flag_count >= 2 (phone + laptop) and channels matching spec (R1,2,4,5,8,9 in `#execution`; R3,6,7 in both).

## Rollback

**Controlled rollback** (any phase):

```bash
systemctl --user stop enforcer-bot-slack.service
```

This stops the Slack unit immediately. TG enforcer continues (if still running). State (in-memory tracker) is lost; acceptable.

**If Phase D was reached** (TG unit removed from disk):
Restore from git history and re-enable:

```bash
git show HEAD~N:infra/systemd/enforcer-bot.service > ~/.config/systemd/user/enforcer-bot.service
systemctl --user daemon-reload
systemctl --user start enforcer-bot.service
```

**Symptom-triggered rollback:**
Stop the Slack unit immediately if:
- More than 3 crashes in 1 hour (check `journalctl --user -u enforcer-bot-slack.service`)
- Slack flag rate > 2× TG flag rate (compare `governance_events` rows over 1h window)
- Dave invokes `/kill` (emergency stop — all agents pause)

## Installation

**Do NOT install, enable, or start manually.** This is for reference only.

When ready for Phase A (post-merge of ENFORCER-BUILD-001):

```bash
cp infra/systemd/enforcer-bot-slack.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now enforcer-bot-slack.service
```

**Verify startup:**

```bash
systemctl --user status enforcer-bot-slack.service
journalctl --user -u enforcer-bot-slack.service -n 50
```

Expected logs: `Socket Mode client connected`, `governance_events pool initialized`, `Listening on channels...`.

## Observability

**Live logs:**
```bash
journalctl --user -u enforcer-bot-slack.service -f
```

**File logs:**
```bash
tail -f /home/elliotbot/clawd/logs/enforcer-bot-slack.log
```

**Governance events table:**
```sql
SELECT created_at, rule_id, callsign, channel, interjection_text
FROM public.governance_events
WHERE source='enforcer'
ORDER BY created_at DESC
LIMIT 20;
```

**Health checks:**
- Socket connection: `auth.test` ping every 60s (built-in); 3 consecutive failures → process exits, systemd restarts.
- Slack flag rate: compare `COUNT(*) WHERE source='enforcer' AND created_at > NOW() - INTERVAL '1 hour'` to TG baseline.
- Uptime: `systemctl --user show -p ActiveEnterTimestamp -p ExecMainPID enforcer-bot-slack.service`.
