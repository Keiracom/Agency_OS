## Session Start

On every new session, your FIRST action before any directive, query, or build work:

0. Read `./IDENTITY.md` first — your callsign is the single source of truth for this session (LAW XVII). Verify CALLSIGN env var matches if set.
1. **Manual (LAZY-LOAD per Phase 6 W4, 2026-05-11):** the Agency OS Manual (Drive Doc `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho`) is the CEO SSOT. Fetch on first cross-reference (directive mentions "the Manual" / references active directives by number / queries CEO state) — never from cached knowledge. If unreachable when needed, alert Dave and STOP. Most operational sessions never need it (#ceo + #execution + ceo_memory + this module set cover current state).
2. **Slack relay verification (HARD BLOCK):** Verify `tg -g "test"` works. First outbound message MUST go via `tg -g`. Dave reads Slack #execution, not your terminal.
3. **READ RECENT CHANNEL ON RESET (HARD BLOCK):** Check `/tmp/telegram-relay-<callsign>/inbox/` for recent messages before acting on any directive. The central Slack listener fans out channel messages to per-callsign inbox dirs.
4. **CLONE AWARENESS (HARD BLOCK):** Check for active clone sessions (ATLAS, ORION, SCOUT) via `tmux list-sessions` and inbox/outbox watchers. Read any pending outbox messages from clones before proceeding.
5. **BEADS READY (Dave directive 2026-05-12, Elliot orchestrator only):** Identify the next-unblocked issue via `bd ready` (local Beads task graph) — the canonical "what can I dispatch right now" answer; surface any blockers. (The former Linear board query was retired 2026-06-03 — "we don't need linear"; Postgres is SSOT.)
6. **COGNEE CONTEXT (KEI-107 — fail-open):** Read `/tmp/cognee-context-<callsign>.md` if present — recent Cognee memory relevant to this callsign, written by `scripts/cognee_session_start.py` at session launch. If the file is absent or empty, proceed without it. To refresh manually: `python3 scripts/cognee_session_start.py --callsign <callsign>`.

> **Linear retirement (Dave 2026-06-03, "we don't need linear"):** the former step 6 `bd linear sync --pull-if-stale` session-start pull was removed. Its host timer (`bd_linear_sync.timer`) and the sanctioned Linear writer (`linear-oneway-push.service`) are already `inactive`+`disabled`. Postgres is SSOT (Linear demoted 2026-06-02); do not reintroduce a session-start Linear pull. Step 5's former orchestrator-only Linear board query was retired in the same pass — `bd ready` is now the sole dispatch source. No session-start Linear reference remains.
