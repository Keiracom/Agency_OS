# Enforcer Bot Redesign — Telegram → Slack Spec

**Status:** design spec only — no implementation lands with this doc.
**Dispatch:** ENFORCER-REDESIGN-001 (Max, 2026-05-11). Gate 2 ratified by Dave.
**Build:** ENFORCER-BUILD-001 (sequenced AFTER Aiden's DUAL_POST smoke test + cutover).
**Source bot:** `src/telegram_bot/enforcer_bot.py` (571 LOC, current TG production).
**Target bot:** `src/bot_common/enforcer_bot.py` (Slack Socket Mode, this spec).

---

## 1. Goals and Non-Goals

### Goals
- Replace TG `getUpdates` polling with Slack Socket Mode (WebSocket, real-time push).
- Preserve all 9 rules **verbatim** — extracted from `enforcer_bot.py:42-96`.
- Preserve sliding window context (20 msgs), governance-events state tracker, rate-limited interjection, MAX-outbox PR-claim verification.
- Promote interjection persistence from in-memory + TG group post → row in `public.governance_events` Supabase table (parity with `src/governance/gatekeeper.py:53` and `src/coo_bot/group_writer.py:64`).
- Add 4 Slack-native capabilities (gate-2 decisions ratified):
  1. RULES_PROMPT extracted to `src/bot_common/enforcer_rules.py` (importable, testable).
  2. Channel-aware rule scoping — `#execution` and `#alerts` carry different rule sets; R3 + R6 surface in **both**.
  3. Bot username `Enforcer`, icon 🚨.
  4. Phase C deliberate-violation test runs cross-device.
- Slack-native threading: every violation interjection opens a thread; follow-ups (bot apology, Dave override, re-flag suppression) live in the thread, not the channel.
- Structured JSON rule definitions — `enforcer_rules.py` exposes a list[dict] of rule records with `id`, `name`, `text`, `channels`, `requires_stage0`, `cooldown_s`, `exceptions[]`. The LLM prompt is generated from this list, never hand-edited.

### Non-Goals
- New rules. The 9 are frozen verbatim. Any new rule is a separate dispatch.
- Tone / wording changes to interjection text — the prefix `[ENFORCER] Rule N — <NAME>` stays identical for grep-compat with logs and tests.
- Migration of `src/coo_bot/` or `src/governance/gatekeeper.py`. Those keep writing to Supabase as today.
- TG group decommission. TG stays live in dual-post mode until Aiden's cutover signs off.
- Slack workspace provisioning, channel creation, RBAC. Assumed already done before BUILD starts.

---

## 2. Architecture

```
┌───────────────────────┐         WebSocket          ┌────────────────────────┐
│   Slack workspace     │ ◀───────────────────────── │   Enforcer Bot         │
│                       │   Socket Mode (app token)  │   src/bot_common/      │
│  #execution           │                            │   enforcer_bot.py      │
│  #alerts              │ ──────────────────────────▶│                        │
│  #dave-direct (DM)    │   chat.postMessage         │   - Socket client      │
└───────────────────────┘                            │   - Rule engine        │
                                                     │   - State tracker      │
                                                     │   - LLM checker        │
┌───────────────────────┐                            │   - PR-claim verifier  │
│ public.governance_    │ ◀───── asyncpg INSERT ─────│                        │
│ events (Supabase)     │                            └────────────────────────┘
└───────────────────────┘                                       │
                                                                ▼
                                                     ┌────────────────────────┐
                                                     │ /tmp/telegram-relay-   │
                                                     │ {elliot,aiden,max}/    │
                                                     │ inbox  (bot tmux taps) │
                                                     └────────────────────────┘
```

Single asyncio process. Three concurrent coroutines (mirrors current `asyncio.gather` shape in `enforcer_bot.py:565`):

1. `socket_loop()` — Slack Socket Mode client receives every `message.channels` event the bot is invited to. Replaces `watch_inbox()` (`enforcer_bot.py:365`).
2. `max_outbox_watcher()` — unchanged port of `watch_max_outbox()` (`enforcer_bot.py:407-550`). Continues to read `/tmp/telegram-relay-max/outbox/`. Slack does not replace this — Max's clone outbox is a filesystem queue.
3. `housekeeping()` — periodic flush of stale `governance_events` keys (>24h), Slack connection health probe, retry of failed `public.governance_events` inserts.

Connection: `slack_sdk.socket_mode.aiohttp.SocketModeClient` (official). App-level token (`xapp-...`) + bot token (`xoxb-...`) supplied via env. No public HTTP listener — Socket Mode tunnels through Slack's edge.

---

## 3. Rule Engine

### 3.1 Source extraction (verbatim)

All 9 rules currently live as plain English in `RULES_PROMPT` (`enforcer_bot.py:42-96`). Extracted records below — the exact text in `enforcer_bot.py` is the canonical source; this section quotes it for review traceability. The build PR will copy these strings byte-for-byte into `src/bot_common/enforcer_rules.py`.

| ID  | Name (from prompt)              | Source lines  | Channels (gate-2)  |
| --- | ------------------------------- | ------------- | ------------------ |
| R1  | CONCUR-BEFORE-SUMMARY           | line 48       | #execution         |
| R2  | STEP-0-BEFORE-EXECUTION         | lines 50-59   | #execution         |
| R3  | COMPLETION-REQUIRES-VERIFICATION| lines 61-65   | #execution, #alerts|
| R4  | NO-UNREVIEWED-MAIN-PUSH         | line 67       | #execution         |
| R5  | SHARED-FILE-CLAIM               | line 69       | #execution         |
| R6  | SAVE-CLAIM-REQUIRES-PROOF       | line 71       | #execution, #alerts|
| R7  | CLONE-DIRECT-GROUP-POST         | line 77       | #execution, #alerts|
| R8  | DISPATCH-COORDINATION           | line 73       | #execution         |
| R9  | DIRECTIVE-INITIATIVE            | line 75       | #execution         |

Rules R3 + R6 fire in BOTH channels per gate-2 #2 — completion / save claims may be posted to either #execution (work band) or #alerts (escalation band), and both must be verified.

R7 fires in BOTH channels because a clone posting anywhere outside its parent inbox is a violation regardless of channel.

### 3.2 Structured JSON shape (`src/bot_common/enforcer_rules.py`)

```python
# Skeleton only — final strings copied verbatim from enforcer_bot.py:42-96
RULES: list[dict] = [
    {
        "id": "R1",
        "name": "CONCUR-BEFORE-SUMMARY",
        "text": "<verbatim from enforcer_bot.py line 48>",
        "channels": ["#execution"],
        "requires_stage0": True,          # gated by stage0_active in current code
        "cooldown_s": 300,                 # FLAG_COOLDOWN_SECONDS
        "exceptions": [],
    },
    {
        "id": "R2",
        "name": "STEP-0-BEFORE-EXECUTION",
        "text": "<verbatim from enforcer_bot.py lines 50-59>",
        "channels": ["#execution"],
        "requires_stage0": True,
        "cooldown_s": 300,
        "exceptions": [
            "PR merge on explicit CEO instruction (Dave 'merge N')",
            "Rebase as peer-review fix",
            "Orchestrator tagging peer replies",
            "CEO removed Step 0 confirmation gate",
            "Task approved via [PROPOSE:<callsign>] + Dave 'approve'",
        ],
    },
    # R3..R9 follow the same shape — each `text` field copied byte-for-byte.
]

def build_prompt(channel: str) -> str:
    """Compose RULES_PROMPT for the LLM, filtered to rules active in `channel`.

    Output is the same opening narrative + body + closing JSON-format block
    as enforcer_bot.py:42-96, but with the rule list restricted to
    [r for r in RULES if channel in r["channels"]].
    """
```

The prompt builder generates the system message; the LLM call shape (gpt-4o-mini, temperature 0.1, max_tokens 300, JSON-only response) is unchanged from `enforcer_bot.py:166-186`.

### 3.3 Channel-aware rule scoping

Each Slack message event carries `channel` (Slack channel ID). The Socket loop:

1. Resolves channel ID → channel name via `conversations.info` (cached for the process lifetime).
2. Builds the LLM prompt with `build_prompt(channel_name)` — only rules whose `channels` list contains the current channel are sent.
3. Skips checking entirely if the channel is not in any rule's scope (e.g. random side channels the bot was invited to).

This replaces the all-or-nothing prompt in the current TG implementation.

---

## 4. Message Processing Pipeline

```
Slack event (message.channels)
    │
    ▼
1. Filter: is this a bot message? (sender.bot_id present OR username == 'Enforcer' → skip)
   Mirrors enforcer_bot.py:145-148 is_bot_message(). Dave's messages always pass through to state tracker but never trigger violation checks (line 93 of RULES_PROMPT).
    │
    ▼
2. Update sliding window: deque(maxlen=20) per channel.
   Per-channel state replaces the single global deque at enforcer_bot.py:31.
    │
    ▼
3. Update governance_events state tracker keys:
   - last_concur_elliot, last_concur_aiden  → on "concur" from bot
   - last_step0                              → on "step 0"/"restate"
   - last_stage0_request                     → on Dave message ending /stage0
   Logic verbatim from enforcer_bot.py:261-301.
    │
    ▼
4. Pre-filter: should_check(text) — only proceed if any TRIGGER_PATTERN substring hits.
   TRIGGER_PATTERNS list copied verbatim from enforcer_bot.py:100-136.
    │
    ▼
5. Compute stage0_active (deterministic, NOT LLM):
   active = (now - last_stage0_request.timestamp) < 30 minutes.
   Per enforcer_bot.py:317-329.
    │
    ▼
6. Call gpt-4o-mini with build_prompt(channel) + {current_message, recent_messages[-20:], governance_events}.
   LLM returns {violation, rule_number, rule_name, detail, should_have}.
   On null result (API failure, JSON parse fail): log warn, return — fail-open.
    │
    ▼
7. Post-LLM gates:
   (a) If rule_number ∈ {1, 2} AND NOT stage0_active → suppress (enforcer_bot.py:341-343).
   (b) If rule_number was flagged in last cooldown_s (per-rule, per-channel)  → suppress (enforcer_bot.py:348-355).
    │
    ▼
8. interjection text:
   "[ENFORCER] Rule {N} -- {name}: {detail}. {should_have}."
   (Identical to enforcer_bot.py:357.)
    │
    ▼
9. POST in two places:
   (a) Slack: chat.postMessage(channel=violation_channel, text=interjection,
       username='Enforcer', icon_emoji=':rotating_light:', thread_ts=<violation_msg.ts>)
       → opens a thread anchored on the violating message. Subsequent re-flag-suppression
         and bot apology messages reply_in_thread to that ts.
   (b) Filesystem inbox (parity with enforcer_bot.py:228-244):
       Write JSON to /tmp/telegram-relay-{elliot,aiden,max}/inbox/{ts}_{uuid}.json
       so bot tmux sessions still see interjections in their inbox watchers.
    │
    ▼
10. Persist: INSERT INTO public.governance_events
    (timestamp, source='enforcer', rule_id, rule_name, channel, callsign,
     interjection_text, current_message, recent_window_json, llm_model='gpt-4o-mini').
    Best-effort via asyncpg pool (re-uses the connection style at src/coo_bot/group_writer.py:49-64).
    On insert failure: log + retry once in housekeeping(); never block the Socket loop.
```

---

## 5. State Management

| State                       | Type                       | Lifetime              | Notes |
| --------------------------- | -------------------------- | --------------------- | ----- |
| message_window[channel]     | dict[str, deque(maxlen=20)]| process lifetime      | per-channel; replaces single global deque at `enforcer_bot.py:31` |
| enforce_events              | dict[str, dict]            | process lifetime      | keys: `last_concur_elliot`, `last_concur_aiden`, `last_step0`, `last_stage0_request` — unchanged from `enforcer_bot.py:40` |
| last_flag_times[(rule, channel)] | dict[tuple, float]    | process lifetime      | rate limit; per-rule **and** per-channel (current code is per-rule global at `enforcer_bot.py:34`) |
| channel_name_cache          | dict[str, str]             | process lifetime      | channel-id → channel-name from `conversations.info`; cleared on restart |
| socket_client               | SocketModeClient           | process lifetime      | reconnects via slack_sdk built-in backoff (see §6) |
| pg_pool                     | asyncpg.Pool               | process lifetime      | size 4, idle 60s, reused across all 3 coroutines |

All state is in-memory and resets on restart (acceptable — `governance_events` table is the durable record; tracker keys are 30-min relevance windows).

Promotion to durable storage is out of scope. Adding a periodic snapshot to `agent_memories` is a follow-up dispatch if needed.

---

## 6. Error Handling

| Failure                           | Behaviour                                                                                  | Source parity |
| --------------------------------- | ------------------------------------------------------------------------------------------ | ------------- |
| LLM API timeout / 5xx             | Log warn, return None, skip interjection. Cooldown timer NOT updated.                      | `enforcer_bot.py:187-189` |
| LLM returns invalid JSON          | Log warn, return None, skip.                                                               | implicit via json.loads except |
| Slack chat.postMessage 4xx/5xx    | Retry once with 1s backoff. On second failure, log + write filesystem inbox only.          | new — TG had only fire-and-forget |
| Slack Socket disconnect           | slack_sdk reconnects with exponential backoff (built-in). On 5 consecutive failures, exit non-zero → systemd restarts service. | new |
| asyncpg connection lost           | Pool auto-reconnects. Insert retried once in housekeeping(); after 3 retries, dropped + logged. | new |
| Filesystem inbox write fail (ENOSPC, etc.) | Log error, continue. Slack post still happens.                                    | `enforcer_bot.py:243-244` |
| Invalid Slack event payload       | Log + drop. Never crash the Socket loop.                                                   | new |
| OOM / unhandled exception in process_message | Log full traceback, swallow. Surface as governance_events row of `source='enforcer', rule_id='internal_error'`. | new |

Health probe: housekeeping() pings `auth.test` every 60s. If 3 consecutive fail → process exits, systemd restarts. Restart resets all in-memory state — acceptable (TG version also resets on restart and has been stable for 3+ weeks).

---

## 7. Slack-Native Features

### 7.1 Threading

Every interjection posts with `thread_ts = violating_message.ts`. This anchors all related traffic to the offending message:

- Re-flag suppressions (within cooldown) → no new top-level post, optional reply in thread for audit.
- Bot follow-ups ("acknowledged, retroactive Step 0 posted") → bots may post into the thread without re-triggering enforcement (the enforcer skips messages with `thread_ts != null` AND `sender == 'Enforcer'`).
- Dave overrides → Dave posts in the thread; enforcer reads but does not flag (Dave-immunity preserved).

### 7.2 Bot identity (gate-2 #3)

```
username:    Enforcer
icon_emoji:  :rotating_light:
```

Sent on every `chat.postMessage`. Slack honours these per-message overrides without app reconfiguration. The bot's underlying App handle stays whatever Slack assigns; `Enforcer` + 🚨 is a display-layer choice.

### 7.3 Callsign extraction from Slack username override

Slack messages from agent bots carry a `username` override (set by the agent's posting wrapper, the planned `dual_post.py`). Mapping:

| Slack `username` override | callsign  |
| ------------------------- | --------- |
| `Elliot`                  | `elliot`  |
| `Aiden`                   | `aiden`   |
| `Max`                     | `max`     |
| `ATLAS`                   | `atlas`   |
| `ORION`                   | `orion`   |
| `SCOUT`                   | `scout`   |
| `Enforcer`                | `enforcer`|
| (Slack user, no override) | `dave`    |

Lowercase, strip; fallback to `unknown` for unrecognised values. Used to populate `governance_events.callsign` and to evaluate `enforce_events.last_concur_{elliot,aiden}` correctly (replaces `enforcer_bot.py:278-292` first-name parsing).

---

## 8. Deployment

### 8.1 systemd unit swap

Two units exist briefly side-by-side during dual-post:

```
enforcer-bot.service           # current — TG getUpdates polling, stays running
enforcer-bot-slack.service     # new — Slack Socket Mode, starts in observe-only mode
```

`enforcer-bot-slack.service` (drop-in):
```ini
[Service]
ExecStart=/home/elliotbot/clawd/venv/bin/python3 -m src.bot_common.enforcer_bot
WorkingDirectory=/home/elliotbot/clawd/Agency_OS
Environment="ENFORCER_OBSERVE_ONLY=1"          # cutover phase A
Environment="SLACK_APP_TOKEN=${SLACK_APP_TOKEN}"
Environment="SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}"
Environment="OPENAI_API_KEY=${OPENAI_API_KEY}"
EnvironmentFile=/etc/agency-os/enforcer.env
Restart=always
RestartSec=5
```

Observe-only flag: when `ENFORCER_OBSERVE_ONLY=1`, the Slack interjection POST is replaced by a log line + `governance_events` row with `interjection_text='OBSERVE: <text>'`. TG enforcer continues to be the only bot posting visible interjections. Allows Phase A traffic comparison without double-flagging.

### 8.2 Cutover phases

| Phase | State                                                  | Exit criterion                                                |
| ----- | ------------------------------------------------------ | ------------------------------------------------------------- |
| A     | TG live + Slack observe-only, 24h                      | Slack & TG flag rates within ±10% on same rules, no Slack crashes |
| B     | Both live (dual-post). Both interject.                 | 24h with no duplicate-flag complaints from Dave or bots       |
| C     | Slack live, TG observe-only. **Deliberate-violation cross-device test** (gate-2 #4) — Dave triggers each of R1-R9 from phone and laptop; verify enforcer flags from both | All 9 rules flagged at least once from each device         |
| D     | Slack live, TG service stopped + masked                | 48h stable on Slack alone → enforcer-bot.service unit removed |

### 8.3 Rollback

At any phase: `sudo systemctl stop enforcer-bot-slack.service`. If we were past Phase D and TG unit was deleted, restore from git history (`enforcer-bot.service` lives in `infra/systemd/` per existing convention) and `systemctl daemon-reload && systemctl start enforcer-bot.service`. State (in-memory tracker) is lost on either rollback — acceptable.

Symptom-triggered rollback: more than 3 enforcer crashes in 1h, OR Slack flag rate >2× TG flag rate, OR Dave invokes `/kill` → drop to previous phase.

---

## 9. Test Plan

| Phase | Test                                              | Mechanism                              |
| ----- | ------------------------------------------------- | -------------------------------------- |
| Unit  | `enforcer_rules.RULES` byte-equality vs `enforcer_bot.py:42-96` substrings | pytest, run in CI |
| Unit  | `build_prompt(channel)` filter — R3+R6 in `#alerts`; R1,R2 absent | pytest |
| Unit  | callsign extraction lookup table                  | pytest with fixture of Slack `username` overrides |
| Unit  | stage0_active deterministic timing — 29.9min PASS, 30.1min FAIL | pytest, freeze time |
| Unit  | rate limit per (rule, channel) — cooldown 300s    | pytest, freeze time |
| Integ | LLM mock returns {violation: true, rule: 3}, full pipeline | pytest, httpx mock |
| Integ | Slack 5xx → retry then filesystem inbox fallback  | pytest, httpx mock |
| Integ | governance_events INSERT shape                    | pytest with test Supabase DB / `pytest-postgresql` |
| E2E A | Slack observe-only flag rate vs TG                | live run, manual diff |
| E2E C | **Deliberate violations from phone + laptop, all 9 rules** | Dave manually triggers; enforcer flag log captured |

CI gate: unit + integ pass before merge of ENFORCER-BUILD-001. E2E phases run in production post-merge.

---

## 10. Open Questions (for Aiden cross-review)

1. **`#alerts` channel definition.** Spec lists `#execution` + `#alerts` for R3/R6/R7. Are those the only Slack channels in scope, or are `#dave-direct`, `#cohort-runs`, `#governance-debt` also relevant? Resolve before BUILD opens.
2. **Slack DM handling.** Should the bot enforce in DMs to Dave? Current TG bot does not (group-only). Default: skip DMs unless explicitly requested.
3. **Filesystem-inbox parity.** Spec keeps writing to `/tmp/telegram-relay-*/inbox/`. Do we still need this once tmux bot sessions read from Slack directly? Recommend: keep through Phase D, remove in a follow-up dispatch.
4. **PR_CLAIM_RE / verify_pr.sh.** These remain unchanged. If Max stops writing to `/tmp/telegram-relay-max/outbox/` and switches to a Slack channel-based claim flow, this watcher becomes redundant. Not in scope for this PR.

---

## 11. Out of Scope (named to prevent scope creep)

- New rules (R10+).
- LLM model upgrade (stays on gpt-4o-mini).
- Migrating coo_bot or gatekeeper.
- Multi-workspace Slack support.
- Replacing `verify_pr.sh` with a Python verifier.
- Adding `agent_memories` snapshots of enforce_events.

---

## 12. References

- Source bot: `src/telegram_bot/enforcer_bot.py` (571 LOC)
- Sibling Supabase writers: `src/coo_bot/group_writer.py:49-64`, `src/governance/gatekeeper.py:53`
- Phoenix span emitter (downstream of `governance_events`): `src/observability/phoenix_client.py`
- Rule canonical text: `enforcer_bot.py:42-96`
- Trigger patterns: `enforcer_bot.py:100-136`
- PR claim regex: `enforcer_bot.py:202-206`
- Existing systemd convention: `infra/systemd/` (search for sibling `.service` files)
- Slack Socket Mode: `slack_sdk.socket_mode.aiohttp.SocketModeClient` (Slack SDK Python, official)
- Gate-2 ratification: Max dispatch 2026-05-11, all 4 decisions approved by Dave.
