## Session Start — Read the Manual First (HARD BLOCK)

On every new session, your FIRST action before any directive, query, or build work:

0. Read `./IDENTITY.md` first — your callsign is the single source of truth for this session (LAW XVII). Verify CALLSIGN env var matches if set.
1. Read the Agency OS Manual from Google Drive (Doc ID: `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho`). This is the CEO SSOT — current state, active directives, blockers, and system status.
2. Do not work from memory. Do not work from stale docs. Read the Manual before any directive.
3. If the Manual is unreachable, alert Dave and STOP. Do not proceed from cached knowledge.
4. **Slack verification (HARD BLOCK):** Verify `python3 scripts/slack_relay.py -g "test"` posts to `#execution` (`C0B3QB0K1GQ`) and returns an `ok` ts. Your FIRST outbound to Dave MUST go via `slack_relay.py`, not terminal output. If it fails, fix before proceeding — Dave reads Slack, not your terminal. All communication with Dave and peers happens via Slack channels (`#execution` / `#alerts` / `#completed_directives`; `#ceo` is Dave-Elliot exclusive — do not poll). Telegram is DEAD for this callsign as of 2026-05-11 (AIDEN-SLACK-MIGRATION-001 — `aiden-telegram.service` stopped + disabled).
5. **READ RECENT CHANNEL HISTORY ON RESET (HARD BLOCK):** Pull recent Slack `#execution` history before acting on any directive. The Manual + ceo_memory capture ratified state but miss in-flight conversation — Dave approvals given minutes ago, peer corrections, dispatch announcements may NOT be in ceo_memory yet. Read from listener log at `/home/elliotbot/clawd/logs/aiden-slack-listener.log` (`inbox <-` lines) or processed inbox files at `/tmp/telegram-relay-aiden/processed/slack_*.json`. If the most recent messages reference a pending decision or approval, that state is ACTIVE — do NOT re-ask Dave for something visible in recent history.
6. **CLONE AWARENESS (HARD BLOCK):** Check for active clone sessions (ATLAS, ORION, SCOUT) via `tmux list-sessions` and inbox/outbox watchers. Clones may have in-flight work dispatched before your reset. Read any pending outbox messages from clones before proceeding. You are not working alone — your clone assistant may already be executing directives.

This overrides all other startup steps. The Manual is ground truth.
