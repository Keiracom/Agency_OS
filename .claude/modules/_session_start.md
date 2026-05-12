## Session Start

On every new session, your FIRST action before any directive, query, or build work:

0. Read `./IDENTITY.md` first — your callsign is the single source of truth for this session (LAW XVII). Verify CALLSIGN env var matches if set.
1. **Manual (LAZY-LOAD per Phase 6 W4, 2026-05-11):** the Agency OS Manual (Drive Doc `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho`) is the CEO SSOT. Fetch on first cross-reference (directive mentions "the Manual" / references active directives by number / queries CEO state) — never from cached knowledge. If unreachable when needed, alert Dave and STOP. Most operational sessions never need it (#ceo + #execution + ceo_memory + this module set cover current state).
2. **Slack relay verification (HARD BLOCK):** Verify `tg -g "test"` works. First outbound message MUST go via `tg -g`. Dave reads Slack #execution, not your terminal.
3. **READ RECENT CHANNEL ON RESET (HARD BLOCK):** Check `/tmp/telegram-relay-<callsign>/inbox/` for recent messages before acting on any directive. The central Slack listener fans out channel messages to per-callsign inbox dirs.
4. **CLONE AWARENESS (HARD BLOCK):** Check for active clone sessions (ATLAS, ORION, SCOUT) via `tmux list-sessions` and inbox/outbox watchers. Read any pending outbox messages from clones before proceeding.
5. **LINEAR + BEADS (Dave directive 2026-05-12, Elliot orchestrator only):** Query Linear for all `In Progress` KEI issues assigned to team Keiracom; surface any blockers; identify the next-unblocked issue via `bd ready` (local Beads task graph). Beads `bd ready` is the canonical "what can I dispatch right now" answer. Linear is the human-facing board Dave watches. Linear MCP server `linear-server` connected via HTTP at `https://mcp.linear.app/mcp` (auth via `LINEAR_API_KEY` env). Tools load on next session restart.
