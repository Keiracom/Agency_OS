## Session Start

On every new session, your FIRST action before any directive, query, or build work:

0. Read `./IDENTITY.md` first — your callsign is the single source of truth for this session (LAW XVII). Verify CALLSIGN env var matches if set.
1. **Manual (LAZY-LOAD, was HARD BLOCK pre-2026-05-11):** the Agency OS Manual (Drive Doc `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho`) is the CEO SSOT. You do NOT need to read it on every session start. Read it on first cross-reference within a session — when a directive mentions "the Manual", references active directives by number, or queries CEO state. Don't work from stale cached knowledge of the Manual; when you reference it, fetch fresh. Most operational sessions never need it (current directive context is in #ceo + #execution + ceo_memory + this module set). Phase 6 W4 conversion 2026-05-11 — burns ~10-20K tokens/session that mostly weren't needed.
2. Do not work from stale memory of Manual content. Re-fetch when referenced.
3. If the Manual is unreachable when needed, alert Dave and STOP. Do not proceed from cached knowledge of CEO SSOT.
4. **Slack relay verification (HARD BLOCK):** Verify `tg -g "test"` works (tg script posts to Slack post-cutover). Your FIRST outbound message MUST go via `tg -g`, not terminal output. Dave reads Slack #execution, not your terminal. All communication with Dave and peers happens via Slack channels (#execution for team, #ceo for Elliot↔Dave), never terminal-only.
5. **READ RECENT CHANNEL ON RESET (HARD BLOCK):** Check `/tmp/telegram-relay-<callsign>/inbox/` for recent messages before acting on any directive. The central Slack listener fans out channel messages to per-callsign inbox dirs. If recent inbox files reference a pending decision or approval, that state is ACTIVE — do NOT re-ask for something visible in recent messages.
6. **CLONE AWARENESS (HARD BLOCK):** Check for active clone sessions (ATLAS, ORION, SCOUT) via `tmux list-sessions` and inbox/outbox watchers. Clones may have in-flight work dispatched before your reset. Read any pending outbox messages from clones before proceeding. You are not working alone — your clone assistant may already be executing directives.

This overrides all other startup steps. The Manual is ground truth.
