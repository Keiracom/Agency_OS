## Session Start — Read the Manual First (HARD BLOCK)

On every new session, your FIRST action before any directive, query, or build work:

0. Read `./IDENTITY.md` first — your callsign is the single source of truth for this session (LAW XVII). Verify CALLSIGN env var matches if set.
1. Read the Agency OS Manual from Google Drive (Doc ID: `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho`). This is the CEO SSOT — current state, active directives, blockers, and system status.
2. Do not work from memory. Do not work from stale docs. Read the Manual before any directive.
3. If the Manual is unreachable, alert Dave and STOP. Do not proceed from cached knowledge.
4. **Telegram verification (HARD BLOCK):** Read the §Group Chat Plumbing section below. Verify `tg -g "test"` works. Your FIRST outbound message to Dave MUST go via `tg -g`, not terminal output. If `tg` fails, fix it before proceeding — Dave reads Telegram, not your terminal. All communication with Dave and peers happens via the Telegram group (chat_id `-1003926592540`), never terminal-only.
5. **READ RECENT GROUP CHAT ON RESET (HARD BLOCK):** Pull the last ~30 messages or last 24 hours of the Telegram supergroup before acting on any directive. The Manual + ceo_memory capture ratified state but miss in-flight conversation — Dave approvals given in the last 10 minutes, peer corrections, dispatch announcements may NOT be in ceo_memory yet. Read from the listener log at `/tmp/telegram-relay-<callsign>/` or via Telegram getUpdates API. If the most recent messages reference a pending decision or approval, that state is ACTIVE — do NOT re-ask Dave for something visible in recent chat history.
6. **CLONE AWARENESS (HARD BLOCK):** Check for active clone sessions (ATLAS, ORION, SCOUT) via `tmux list-sessions` and inbox/outbox watchers. Clones may have in-flight work dispatched before your reset. Read any pending outbox messages from clones before proceeding. You are not working alone — your clone assistant may already be executing directives.

This overrides all other startup steps. The Manual is ground truth.
