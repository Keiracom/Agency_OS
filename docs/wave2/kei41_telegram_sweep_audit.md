# KEI-41 Telegram dead-reference sweep — Phase 1 audit

**Author:** Aiden (Phase 1 audit per Elliot CONCUR ts ~1778674780)
**Beads:** Agency_OS-4uk — P0 URGENT
**Status:** Audit-only. NO rm/edit until Phase 2 CONCUR from Dave + Elliot.

## Critical finding upfront

**`src/telegram_bot/` is NOT a dead package — it contains LIVE INFRASTRUCTURE.** Wholesale delete would break 4 active systemd services + 3 live core-module imports.

- `src/telegram_bot/relay_watcher.sh` — invoked by ACTIVE systemd services: `aiden-relay-watcher.service`, `max-relay-watcher.service`, `scout-relay-watcher.service`, `orion-relay-watcher.service`, `relay-watcher.service`. Verbatim `ExecStart=/home/elliotbot/clawd/Agency_OS/src/telegram_bot/relay_watcher.sh <callsign>`.
- `src/telegram_bot/openai_cost_logger.py` — imported live at:
  - `src/governance/router.py:32` — `from src.telegram_bot.openai_cost_logger import COST_LOG_PATH, log_openai_call`
  - `src/memory/organise.py:85` — `from src.telegram_bot.openai_cost_logger import log_openai_call`
  - `src/memory/store.py:49` — `from src.telegram_bot.openai_cost_logger import log_openai_call`

The package name is legacy (post-Slack migration the `telegram_bot/` dir was kept rather than renamed); a subset of files inside it are dead Telegram API; the rest are live cross-cutting utilities.

## Recommended surgical strategy (proposal for Dave + Elliot ratification)

Three options, ranked by my preference:

### Option A (PREFERRED) — surgical delete + keep utilities in place

- Delete the 8 dead-Telegram-API files from `src/telegram_bot/`:
  - `chat_bot.py`, `enforcer_bot.py`, `listener_discernment.py`, `memory_listener.py`, `recall_handler.py`, `relay.py`, `retrieval_metrics.py`, `save_handler.py`, plus their tests.
- Keep `relay_watcher.sh` + `openai_cost_logger.py` + `__init__.py` in place (live infrastructure; rename is a separate concern).
- Delete dead `src/coo_bot/` package entirely (all 10 .py files) — `coo-bot.service` inactive; no live imports outside the package itself.
- Cost: 18 deletes (8 telegram + 10 coo) + ~14 test deletes.
- Risk: low — files are unimported outside their own package.

### Option B — rename + move

- Move `relay_watcher.sh` to `scripts/orchestrator/relay_watcher.sh` + update 5 systemd unit `ExecStart=` lines.
- Move `openai_cost_logger.py` to `src/bot_common/openai_cost_logger.py` + update 3 import sites.
- Then wholesale-delete `src/telegram_bot/`.
- Cost: 18 deletes + 8 moves + 8 patch sites + 5 systemd unit edits.
- Risk: medium — systemd unit edits require operator restart; one bad path breaks 4 active services.

### Option C — defer

- Mark dead files with `# DEPRECATED — KEI-41 dead Telegram code, removal scheduled` comments.
- No actual deletes this session.
- Cost: ~50 LoC comment additions.
- Risk: zero, but defers the sweep indefinitely.

Recommend Option A — surgical + safe + immediate.

## Category-by-category file matrix

### Category A — Active Telegram API import sites (7 files; DELETE per Option A)

| File | Import line | Live caller? | Recommended action |
|---|---|---|---|
| `src/telegram_bot/save_handler.py` | `from telegram import Update; from telegram.ext import ContextTypes` | None outside package | DELETE |
| `src/telegram_bot/recall_handler.py` | `from telegram import ...` | None outside package | DELETE |
| `src/telegram_bot/chat_bot.py` | `from telegram.ext import ...` | None outside package | DELETE |
| `src/coo_bot/bot.py` | `from telegram.ext import ApplicationBuilder` | None outside package | DELETE |
| `src/coo_bot/group_handler.py` | `from telegram import ...` | None outside package | DELETE |
| `src/coo_bot/dm_handler.py` | `from telegram import ...` | None outside package | DELETE |
| `tests/test_save_handler.py` | `from src.telegram_bot.save_handler import ...` | Tests the dead file | DELETE |

### Category B — Dead package files (DELETE per Option A; full directory minus utilities)

#### `src/telegram_bot/` (8 dead + 2 LIVE utilities)

DELETE:
- `chat_bot.py`, `enforcer_bot.py`, `listener_discernment.py`, `memory_listener.py`, `recall_handler.py`, `relay.py`, `retrieval_metrics.py`, `save_handler.py`

KEEP (live infrastructure):
- `relay_watcher.sh` — 5 active systemd services invoke it.
- `openai_cost_logger.py` — 3 live imports (governance, memory.organise, memory.store).
- `__init__.py` — package marker; keep if any kept file lives here.

#### `src/coo_bot/` (10 files; DELETE all)

`coo-bot.service` is **inactive** (verified via `systemctl --user is-active coo-bot.service` → `inactive`). `scripts/coo_bot_service.py` imports only within the package itself.

DELETE:
- `__init__.py`, `bot.py`, `config.py`, `dm_handler.py`, `group_handler.py`, `group_writer.py`, `memory_retriever.py`, `opus_client.py`, `persona.py`, `tier_framework.py`.
- Also delete: `scripts/coo_bot_service.py` (entry point for the inactive service).

### Category C — Legacy-named-Slack-backed paths (PRESERVE — 26 files)

All 26 files mention `/tmp/telegram-relay-<callsign>/inbox/` — the systemd central-listener inbox-path convention. Slack-backed via `src/slack_bot/central_listener.py`. NO Telegram API. **PRESERVE per Elliot's prior audit + Dave KEI-41 design.** Rename is a separate KEI.

Sample files: `src/clone_dispatch.py`, `src/security/inbox_hmac.py`, `scripts/sign_dispatch.py`, etc.

### Category D — String-only refs (~38 files; case-by-case)

#### D1 — Cost-logging refs to KEEP (telegram-named-Slack-backed cost tracking)

| File | Context | Action |
|---|---|---|
| `src/telegram_bot/openai_cost_logger.py` | Live utility | KEEP (Option A) or RENAME (Option B) |
| `scripts/openai_cost_rollup.py` | Imports cost-logger | KEEP if Option A |
| `scripts/openai_cost_weekly.py` | Imports cost-logger | KEEP if Option A |
| `tests/test_openai_cost_logger.py` | Tests live utility | KEEP if Option A |

#### D2 — Old systemd-paths in script comments (KEEP as historical context)

Slack listeners (`scripts/elliot_slack_listener.py`, `scripts/aiden_slack_listener.py`, `scripts/coo_slack_listener.py`, etc.) reference `/tmp/telegram-relay-*` paths in their docstrings — the path convention they replaced Telegram for. KEEP.

#### D3 — Prefect / Orchestration / Outreach `tg_notify` calls (REPLACE with Slack)

| File | Action |
|---|---|
| `src/evo/tg_notify.py` | DELETE — entire module is a Telegram-only notifier; callers should use slack_relay.py |
| `src/prefect_utils/failure_alert.py` | REPLACE imports of `tg_notify` with `slack_relay` |
| `src/prefect_utils/hooks.py` | Same |
| `src/orchestration/flows/health_check_flow.py` | Same |
| `src/orchestration/flows/outreach_flow.py` | Same |
| `src/orchestration/flows/stage_9_10_flow.py` | Same |
| `src/orchestration/cohort_runner.py` | Same |
| `src/outreach/safety/alert_emitter.py` | Same |
| `src/outreach/safety/deliverability_monitor.py` | Same |
| `src/bot_common/verify_gate.py` | Same |

10 files to patch — each replaces `from src.evo.tg_notify import notify` with `from scripts.slack_relay import post` (or equivalent). Mechanical refactor.

#### D4 — Tests for Category A/B (DELETE with their subjects)

| File | Action |
|---|---|
| `tests/test_save_handler.py` | DELETE (already in Cat A) |
| `tests/test_memory_listener.py` | DELETE (subject in Cat B telegram_bot/) |
| `tests/test_retrieval_metrics.py` | DELETE |
| `tests/test_classify_sender.py` | DELETE |
| `tests/test_chat_bot_peer_map.py` | DELETE |
| `tests/test_enforcer_max_outbox.py` | DELETE — tests enforcer_bot in dead package |
| `tests/telegram_bot/test_recall_handler.py` | DELETE |
| `tests/telegram_bot/test_relay_watcher_dispatch.py` | **PRESERVE if relay_watcher.sh kept** |
| `tests/telegram_bot/test_cmd_update.py` | Check subject — if dead, DELETE |
| `tests/coo_bot/*.py` (8 files) | DELETE — all test the coo_bot package |
| `tests/test_openai_cost_logger.py` | **PRESERVE** — tests live utility |

#### D5 — Inactive systemd unit files (operator-action, NOT this PR)

Inactive systemd units (telegram-chat-bot.service, coo-bot.service, aiden-telegram.service, max-telegram.service, scout-telegram.service, agency-os-coo.service, enforcer-bot.service) should be `systemctl --user disable` then file removed by operator. NOT in this PR (operator-edited).

## Dependency analysis summary

Per Option A, the actual delete set is **bounded**:

- 8 telegram_bot/ Python files (dead Telegram API)
- 10 coo_bot/ Python files (entire package, service inactive, no external imports)
- 1 evo/tg_notify.py
- 1 scripts/coo_bot_service.py
- ~12 test files for the above
- **Plus 10 file-edit patches** (D3 — replace tg_notify imports with slack_relay).

Total: ~32 deletes + 10 edits = ~42 file operations + ~14 test file deletes.

## What survives wholesale (Option A)

- `src/telegram_bot/relay_watcher.sh` + `openai_cost_logger.py` + `__init__.py` — live infrastructure.
- `tests/test_openai_cost_logger.py` + `tests/telegram_bot/test_relay_watcher_dispatch.py` — tests for live infrastructure.
- All 26 Category C legacy-named-Slack-backed paths.
- All D1 cost-logging callers.
- All D2 historical-context docstrings.

## Phase 2 execution plan (gated on Dave + Elliot CONCUR)

Once Phase 1 audit doc is CONCUR-ed:

1. Branch `aiden/kei41-telegram-sweep-execute` off main.
2. Apply Option A deletes + D3 import replacements as a SINGLE atomic PR.
3. Run full test suite — surface any unexpected import breakage immediately.
4. PR opens green.
5. Dual-CTO concur + self-merge.
6. Operator follow-up (separate, NOT this PR): `systemctl --user disable` the 7 inactive telegram/coo systemd units.

## Acceptance criteria (Phase 2)

- `grep -ri "import telegram\|from telegram" src/ scripts/ tests/` returns 0 lines (excluding string-context-only matches in design docs).
- All 5 active relay-watcher.service units continue running unaffected.
- `src/telegram_bot/openai_cost_logger.py` import paths from governance + memory.{organise,store} continue to resolve.
- Full pytest suite passes.
- No active code path references `src.evo.tg_notify`.

## Open questions for Dave

1. Option A (surgical, preserve live utilities in legacy-named package) vs Option B (rename + move utilities out)?
2. D3 tg_notify replacement: should I migrate the 10 caller sites' notify calls to slack_relay.post() in this same PR, or scope as a follow-up?
3. systemd unit disable: operator manual, or include in PR (.service file edits + commit)?

## Rollback (Phase 2)

Single PR = single revert. Each deleted file recoverable via `git revert <merge-sha>`. systemd services keep running (relay_watcher.sh preserved). Pre-revert sanity: confirm no test depends on a deleted file before merge.
