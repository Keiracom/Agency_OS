## Session Start — Read the Manual First (HARD BLOCK)

On every new session, your FIRST action before any directive, query, or build work:

0. Read `./IDENTITY.md` first — your callsign is the single source of truth for this session (LAW XVII). Verify CALLSIGN env var matches if set.
1. Read the Agency OS Manual from Google Drive (Doc ID: `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho`). This is the CEO SSOT — current state, active directives, blockers, and system status.
2. Do not work from memory. Do not work from stale docs. Read the Manual before any directive.
3. If the Manual is unreachable, alert Dave and STOP. Do not proceed from cached knowledge.
4. **Slack relay verification (HARD BLOCK):** Verify `tg -g "test"` works (tg script posts to Slack post-cutover). Your FIRST outbound message MUST go via `tg -g`, not terminal output. Dave reads Slack #execution, not your terminal. All communication with Dave and peers happens via Slack channels (#execution for team, #ceo for Elliot↔Dave), never terminal-only.
5. **READ RECENT CHANNEL ON RESET (HARD BLOCK):** Check `/tmp/telegram-relay-<callsign>/inbox/` for recent messages before acting on any directive. The central Slack listener fans out channel messages to per-callsign inbox dirs. If recent inbox files reference a pending decision or approval, that state is ACTIVE — do NOT re-ask for something visible in recent messages.
6. **CLONE AWARENESS (HARD BLOCK):** Check for active clone sessions (ATLAS, ORION, SCOUT) via `tmux list-sessions` and inbox/outbox watchers. Clones may have in-flight work dispatched before your reset. Read any pending outbox messages from clones before proceeding. You are not working alone — your clone assistant may already be executing directives.

This overrides all other startup steps. The Manual is ground truth.
