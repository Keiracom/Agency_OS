# Enforcer Bot — Slack Redesign Spec

**Author:** Elliot
**Date:** 2026-05-10
**Directive:** ENFORCER-REDESIGN-001 (P2, design only)
**Sequencing:** Build deferred until AIDEN-SLACK-MIGRATION-001 cutover lands clean.
**Source-of-truth:** `src/telegram_bot/enforcer_bot.py` (571 LOC) + `RULES_PROMPT` constant (R1-R9 verbatim).

---

## 1. Slack Socket Mode integration (`slack_sdk.socket_mode`)

### Why Socket Mode (not Events API)
Vultr host has no public HTTPS endpoint. Socket Mode is Slack's bot-token + WebSocket protocol — bot opens an outbound WebSocket to Slack, no inbound traffic required. Identical reachability profile to the current TG long-poll model. `slack_sdk.socket_mode.SocketModeClient` is the canonical Python implementation.

### Connection lifecycle
```
boot
  ├─ load SLACK_ENFORCER_BOT_TOKEN (xoxb-) + SLACK_ENFORCER_APP_TOKEN (xapp-)
  ├─ web_client = WebClient(token=SLACK_ENFORCER_BOT_TOKEN)
  ├─ socket_client = SocketModeClient(app_token=SLACK_ENFORCER_APP_TOKEN, web_client=web_client)
  ├─ socket_client.socket_mode_request_listeners.append(handle_request)
  ├─ socket_client.connect()  # blocking; auto-reconnects on disconnect
  └─ keep-alive loop
```
Two tokens required: a bot token (`chat:write` to post enforcer interjections) and a Socket Mode app-level token (`connections:write`, scoped via `apps.connections.open`). Both stored in `~/.config/agency-os/.env`.

### Reconnect / failure
`socket_client.connect()` handles WebSocket reconnect transparently. On `auth.test` failure at boot, log + exit (systemd `Restart=on-failure` brings it back with backoff). No silent partial-up state.

---

## 2. Event filtering — which message events trigger rule checks

### Event types subscribed
- `message.channels` — public channels the bot is a member of
- `message.groups` — private channels (we use private `#execution`)

Excluded: `message.app_home`, `message.im`, `message.mpim`, `message_changed`, `message_deleted`. Edits + deletes don't re-trigger rule checks (matches current TG behavior — TG enforcer doesn't see edits).

### Pre-filter (deterministic, no LLM cost)
Mirrors current `should_check(text)`:
1. Channel ID must be `#execution` (`C0B3QB0K1GQ`). Drop everything else.
2. `message.subtype` absent (skip bot edits, channel joins, file shares — only top-level user messages).
3. Sender's `bot_id` set (only check bot messages — Dave is human, exempt). Mirrors current `is_bot_message()`.
4. Text matches one of `TRIGGER_PATTERNS` (verbatim from `enforcer_bot.py:100-138`). Pattern list ports as-is — Slack message text is the same shape (UTF-8).

### LLM dispatch (gpt-4o-mini, unchanged)
After pre-filter passes, build the same payload (`current_message`, `recent_messages`, `governance_events`) and POST to `https://api.openai.com/v1/chat/completions` with `RULES_PROMPT` verbatim. **Zero changes to the LLM prompt or response shape** — the 9-rule logic is preserved character-for-character.

---

## 3. Channel scope (`#execution` monitoring, `#alerts` for output)

| Channel | ID | Role |
|---|---|---|
| `#execution` | `C0B3QB0K1GQ` | Monitored — bot reads every message here for rule violations |
| `#alerts` | `C0B2EJU53EK` | Enforcer interjections posted here — does NOT interrupt `#execution` flow |
| `#ceo` | `C0B2PM3TV0B` | Not subscribed — enforcer is silent on CEO-direct channel |
| `#completed_directives` | `C0B2U15PSEA` | Not subscribed — outputs only, no interjection target |

### Why split monitoring vs interjection
Current TG behavior: enforcer interjects in the SAME group it monitors (-1003926592540), so violation flags interleave with peer dialog. This created the "noise during high-throughput dispatch" pattern observed last 2 sessions (Max's directives crossing my reviews in flight).

Splitting `#execution` (peers + Dave + Max) from `#alerts` (enforcer-only) means:
- Dave + Max can mute `#alerts` if they want a clean execution stream
- Enforcer interjections don't fragment peer threads
- Bots still see violations because we ALSO write to bot inboxes (see §5)

---

## 4. Cross-message state — CONCUR-BEFORE-SUMMARY needs last-N context

### Current TG mechanism
`message_window` (deque length `MAX_WINDOW=20`) holds last 20 messages observed. `governance_events` dict tracks `last_concur_elliot`, `last_concur_aiden`, `last_step0`, `last_stage0_request` with timestamps. Both fed into the LLM payload as `recent_messages` + `governance_events`.

### Slack port
Identical mechanism — in-process state, no external store. Slack's `events.message` payload provides `text` and `user` (Slack user ID); we map user ID → callsign (`U_ELLIOT_BOT`, `U_AIDEN_BOT`, `B0B2W7VL7T4`-style) at message-receive time, then push `(callsign, text, timestamp)` into the deque.

### Callsign-to-Slack-user-id mapping table
Loaded once at startup from env vars; rejected with a warn-and-skip if any expected ID is missing. Mapping lives in `src/slack_bot/enforcer_callsign_map.py` (small constants module — `SLACK_USER_ELLIOT`, `SLACK_USER_AIDEN`, `SLACK_USER_MAX`, `SLACK_USER_DAVE`).

### Persistence note
State is volatile (deque + dict in-process). Restart loses the last 20-message window. Acceptable per current TG behavior — the `governance_events` rebuild via the next 20 messages within ~5 minutes of typical traffic.

### MAX outbox watcher
Current `watch_max_outbox()` watches `/tmp/telegram-relay-max/outbox/` for PR/completion claims and runs `verify_pr.sh` mechanically. **This is filesystem-side and unaffected by the TG→Slack migration** — the relay writes JSON to that path regardless of which messaging surface the bot then posts to. Keep the watcher unchanged; just ensure its interjection sender (`send_interjection`) targets Slack `#alerts` not TG.

---

## 5. Interjection method — post to `#alerts`, do NOT interrupt `#execution`

### `send_interjection()` rewrite
Two outputs per current behavior:
1. **Slack post** — `web_client.chat_postMessage(channel="C0B2EJU53EK", text=interjection, username="Enforcer", icon_emoji=":police_officer:")`. `chat:write.customize` scope required for the username override (matches Aiden's bot scope set per AIDEN-SLACK-MIGRATION-001).
2. **Bot inbox writes** — verbatim retain the current write-to-inbox pattern. Bots in tmux still poll `/tmp/telegram-relay-<callsign>/inbox/` for context. The inbox payload's `chat_id` field is currently a TG int; can become an opaque string `"slack:#alerts"` or just a flag `"surface": "slack"`. Bots don't act on `chat_id`, only on `text` — change is purely cosmetic.

### Cross-post to `#execution` — explicitly NOT done
Current behavior: enforcer writes the interjection to BOTH the group AND the bot inboxes. New design: enforcer posts ONLY to `#alerts` (Slack) + bot inboxes (filesystem). `#execution` stays clean — Dave can scan it without enforcer noise; if he wants to see violations he switches to `#alerts`.

### Trade-off
Risk: Dave glances at `#execution` only and misses an enforcer flag that bots ignored. Mitigation:
- Bots still see the inbox flag and CAN re-surface to `#execution` if they choose
- `#alerts` channel notification badge still fires for Dave's mobile

---

## 6. Cooldown preservation — `FLAG_COOLDOWN_SECONDS=300` per rule

### Direct port
`last_flag_times: dict[str, float]` keyed by `f"rule_{rule_num}"`, value is `time.time()` of last flag. Suppression check identical to current `enforcer_bot.py:347-356`. `FLAG_COOLDOWN_SECONDS=300` constant unchanged.

### Persistence
Same as §4 — in-process, lost on restart. Acceptable; cooldowns naturally re-establish within 5 minutes.

### Scope nuance for split channels
Cooldown is bot-process-global (one `last_flag_times` dict). Doesn't matter that we now post to `#alerts` instead of `#execution` — cooldown logic operates on the rule_num, not the destination channel.

---

## 7. Migration cutover plan

### Sequencing (aligned with AIDEN-SLACK-MIGRATION-001)
1. **Phase 0 (this PR):** Spec lands. No code change. Aiden's AIDEN-SLACK-MIGRATION-001 proceeds in parallel — relay build, dual-post smoke, cutover.
2. **Phase 1 (post-Aiden cutover):** Build directive ENFORCER-BUILD-001 issued with the LOC estimate + file map below. New code lands behind a feature flag.
3. **Phase 2 (dual-post smoke):** `ENFORCER_SURFACE=both` runs 24h. New Slack enforcer + old TG enforcer both observe `#execution`-mirrored-into-TG-group via Aiden's DUAL_POST. Compare flag counts + latencies. Identical interjections expected.
4. **Phase 3 (cutover):** `ENFORCER_SURFACE=slack`. Old TG enforcer service stopped. Revert via single `systemctl --user restart enforcer-bot.service` after flipping the env flag back.
5. **Phase 4 (decommission):** After 7 days of stable Slack operation, remove TG-only code paths.

### Revert strategy
- Single env var flip (`ENFORCER_SURFACE=tg`) + `systemctl --user restart enforcer-bot.service`
- TG `ENFORCER_BOT_TOKEN` retained in `.env` until Phase 4 decommission
- Old TG bot stays in the group (silent — no unsubscribe needed)

### Rollback indicators (any one triggers immediate revert)
- Slack interjection posts succeed but bots' inboxes don't receive (suggests filesystem write permissions or path resolution broke during port)
- LLM check rate doubles or halves (pre-filter regression)
- `auth.test` fails repeatedly (token rotated without notice — Phase 0 hardening: log token-prefix on boot for visibility)

---

## 8. File map

### New files
| Path | Purpose | Est. LOC |
|---|---|---|
| `src/slack_bot/enforcer_bot.py` | Socket Mode entrypoint, mirrors `src/telegram_bot/enforcer_bot.py` shape | ~450 |
| `src/slack_bot/enforcer_callsign_map.py` | Slack user-id ↔ callsign constants + lookup helper | ~30 |
| `src/slack_bot/__init__.py` | Package init | ~5 |
| `infra/cron/agency-os-enforcer-slack-bot.service` | systemd user-service for the new bot | ~10 |

### Modified files
| Path | Change | Est. LOC |
|---|---|---|
| `~/.config/agency-os/.env` | Add `SLACK_ENFORCER_BOT_TOKEN`, `SLACK_ENFORCER_APP_TOKEN`, `ENFORCER_SURFACE=tg|slack|both` | +3 lines |

### Untouched (load-bearing)
- `src/telegram_bot/enforcer_bot.py` — kept for revert path through Phase 4
- `RULES_PROMPT` content — copied verbatim into the new module (or import from a shared constants file — open question)
- Filesystem inbox plumbing (`/tmp/telegram-relay-<callsign>/inbox/`) — bots still poll this regardless of source surface

### Open: shared constants module
**Question for build phase:** extract `RULES_PROMPT`, `TRIGGER_PATTERNS`, `FLAG_COOLDOWN_SECONDS`, `MAX_WINDOW` to `src/bot_common/enforcer_rules.py` so the TG and Slack bots import the SAME constants? Reduces drift risk during the dual-post phase. Recommend YES; ~50 LOC extraction PR before the Slack bot lands.

---

## 9. Risk register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| RULES_PROMPT diverges between TG + Slack bots during dual-post | Medium | High (false positives / missed violations) | Shared `src/bot_common/enforcer_rules.py` constants module (see §8 open question) |
| Slack Socket Mode reconnect storm during instability | Low | Medium (bot offline during outage) | `slack_sdk` handles reconnect natively; systemd `Restart=on-failure` is the safety net |
| `chat:write.customize` username override silently ignored on free-tier workspace | Low | Low (cosmetic only) | Test in connectivity verification step; fall back to default bot display name if it fails |
| Bot user ID mapping (`SLACK_USER_*`) drifts when Aiden bot rotates / re-OAuths | Medium | Medium (callsign attribution wrong in `recent_messages`) | Boot-time `auth.test` for each expected ID; hard-fail if any missing rather than silently mis-attribute |
| `#alerts` channel notifications get muted by Dave; he misses violations | Medium | Medium (false-quiet) | Document explicitly in the build PR; consider adding a `[VIOLATION]` keyword that surfaces in `#execution` for high-severity rules (R3 + R6 verification claims) |
| Dual-post phase doubles LLM cost (TG enforcer + Slack enforcer both query gpt-4o-mini) | Certain | Low | Time-bounded (24h); ~$0.50 USD at current rate |
| Existing TG `BOT_INBOXES` filesystem path changes during Aiden's relay rewrite | Low | Medium (interjections silently fail to reach bots) | Aiden's AIDEN-SLACK-MIGRATION-001 explicitly carves enforcer code out of scope; verify enforcer inbox writes still land during smoke |
| Slack rate limits (Tier 2: 50 msgs/sec for chat.postMessage) | Very Low | Low | Cooldown already enforces ≤1 interjection per rule per 5 min; well under any tier limit |
| Rule 7 (CLONE-DIRECT-GROUP-POST) trigger pattern matches arbitrary `[atlas]` / `[orion]` substring — fires on bots **describing** the rule, not posting AS the clone (observed false positive 2026-05-11 on this spec PR) | High (during meta-discussion) | Low (cooldown limits noise) | In Slack rewrite, scope Rule 7 to **sender** prefix detection only (Slack's `event.user` / `bot_id` is already structured — match callsign-from-sender against the clone allowlist, ignore message text). Pre-filter `should_check` keeps `[atlas]` for backward-compat but the rule-evaluation prompt should explicitly exclude messages where the bot's own callsign (extracted from sender, not text) is in the allowlist (ELLIOT, AIDEN, DAVE, SCOUT, ENFORCER). |

---

## 10. LOC estimate

| Component | New LOC | Modified LOC | Notes |
|---|---|---|---|
| `src/slack_bot/enforcer_bot.py` | ~450 | — | mirror of TG enforcer shape; Socket Mode handler replaces inbox watcher |
| `src/slack_bot/enforcer_callsign_map.py` | ~30 | — | constants + lookup helper |
| `src/bot_common/enforcer_rules.py` (recommended extraction) | ~80 | — | RULES_PROMPT + TRIGGER_PATTERNS + cooldown const |
| `src/telegram_bot/enforcer_bot.py` | — | ~30 | refactor to import from shared module + `ENFORCER_SURFACE` flag |
| `infra/cron/agency-os-enforcer-slack-bot.service` | ~10 | — | systemd user-service |
| **Total** | **~570** | **~30** | net new ~570 LOC; net touched ~600 LOC |

**Rough vs current 571-LOC TG bot:** ~1:1 mirror. The bulk is Socket Mode boilerplate replacing inbox-watch loops; rule-check + cooldown + interjection logic is character-for-character identical.

---

## 11. Build directive draft (ENFORCER-BUILD-001)

```
═══ DIRECTIVE: ENFORCER-BUILD-001 ═══
Type: Build
Priority: P2
Pre-req: AIDEN-SLACK-MIGRATION-001 cutover landed clean (Slack relay live, TG decommissioned for Aiden side)
From: Claude (CEO) via Dave
To: Elliot

CONTEXT:
Per ENFORCER-REDESIGN-001 spec at docs/specs/elliot/enforcer_slack_redesign_2026-05-10.md.
Build the Slack-side enforcer bot per the spec's §1-§7 implementation plan.
Land behind ENFORCER_SURFACE feature flag. Dual-post smoke 24h. Cutover.
Do NOT decommission TG enforcer until Phase 4 (7 days post-cutover).

CONSTRAINTS:
- Preserve RULES_PROMPT verbatim (extract to src/bot_common/enforcer_rules.py first)
- Slack Socket Mode required (slack_sdk.socket_mode.SocketModeClient)
- Separate token SLACK_ENFORCER_BOT_TOKEN + SLACK_ENFORCER_APP_TOKEN
- Interjections post to #alerts (NOT #execution)
- Bot inbox writes to /tmp/telegram-relay-<callsign>/inbox/ unchanged
- Cooldown FLAG_COOLDOWN_SECONDS=300 preserved
- gpt-4o-mini, temperature 0.1, MAX_WINDOW=20 preserved

ACTION:
Phase A: extract shared constants (src/bot_common/enforcer_rules.py)
Phase B: build src/slack_bot/enforcer_bot.py + callsign map + systemd unit
Phase C: dual-post smoke (ENFORCER_SURFACE=both) 24h, compare flag counts
Phase D: cutover (ENFORCER_SURFACE=slack), single systemctl restart
Phase E (deferred 7d): remove TG-only code paths

OUTPUT:
~570 LOC across 4 new files + ~30 LOC TG bot refactor. Live INSERT-equivalent
(Socket Mode connect succeeds, rule check fires on a synthetic violation,
interjection lands in #alerts + bot inboxes). Smoke evidence per Rule 3.
```

---

## 12. Decision points requiring CEO/Max input before build

1. **Shared constants extraction** — extract `RULES_PROMPT` etc. to `src/bot_common/enforcer_rules.py`? **Recommendation: YES** — drift risk during dual-post is the highest-impact item in the risk register. Decision before build avoids a same-PR refactor.
2. **High-severity surface escalation** — should R3 (completion-without-evidence) + R6 (save-without-proof) violations ALSO post to `#execution` (not just `#alerts`)? Pre-revenue these are the rules most likely to hide a false-green. **Recommendation: YES for R3 + R6 only.** Other rules stay in `#alerts`.
3. **Bot icon / username** — `username='Enforcer'` + `icon_emoji=':police_officer:'`? Or just default Slack-app icon? **Recommendation: explicit `'Enforcer'` username for parity with TG `[ENFORCER]` prefix; emoji = `:rotating_light:` for severity signal.**
4. **`#alerts` channel mute risk** — should Phase C smoke include a deliberate-violation test where Dave confirms he saw the `#alerts` notification on his phone? **Recommendation: YES** — verify the cross-device path before cutover.

---

## 13. Out of scope (explicitly)

- Migrating non-enforcer Telegram bots (chat_bot, max_bot, etc.) — separate directives if/when needed
- Adding new rules — preserve R1-R9 verbatim per directive constraint
- Changing the LLM model from gpt-4o-mini — preserve per directive
- Changing the rule-check trigger logic (`should_check`, `is_bot_message`) — preserve per directive
- Slack-side of the AIDEN-SLACK-MIGRATION-001 (Aiden owns)
