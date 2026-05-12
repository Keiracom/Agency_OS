# Wave 2 Research — Orion IDENTITY.md Thickening Template

**Read fresh 2026-05-12.** Comparison across all 5 IDENTITY.md files:

| Callsign | Bytes | Sections |
|---|---|---|
| aiden | 2300 | callsign, role, SSOT, env-check, group chat, roles, reporting, clone, shared-gov |
| elliot (main) | 1956 | callsign, role, SSOT, env-check, group chat, reporting, clone |
| max | 1398 | callsign, role, SSOT, env-check, group chat, reporting, clone-status |
| atlas | 950 | callsign, "you are X clone", env-check, governance |
| **orion** | **372** | callsign, parent, dispatch — that's it |

Orion is missing: the SSOT declaration, the env-var check, governance pointer, peer-coordination explanation, and the "what you do / don't do" mandate.

## Common scaffolding (4/5 files share this)

1. **Header block** — CALLSIGN, Workspace, Telegram/Slack bot status, Created date, Branch.
2. **Role line** — one-line description of what this callsign does.
3. **Identity paragraph** — "You are X. You do Y. You escalate Z to Dave." For clones: "You are X — Y's Tier A build clone. You do NOT post to Slack/group directly."
4. **SSOT declaration** — "This file is the single source of truth … Read FIRST at session load. Callsign tags every Step 0, outbound, PR title, commit, four-store save (LAW XVII)."
5. **CALLSIGN env-var check** — "If `CALLSIGN` env var is set, it MUST match this file (orion). Mismatch is a governance violation — STOP."
6. **Group chat / relay plumbing** — for primes: Slack channels + relay paths. For clones: inbox/outbox paths only ("clone — communicates via inbox/outbox relay only; parent surfaces to group").
7. **Reporting / parent** — who this callsign reports to.
8. **Governance pointer** — "Follow all laws in CLAUDE.md. Rebase on origin/main before commit. ruff + pytest pass before PR."

## Recommended Orion IDENTITY.md template (callsign-filled)

```markdown
# IDENTITY

**CALLSIGN:** orion
**Workspace:** /home/elliotbot/clawd/Agency_OS-orion/
**Telegram bot:** none (clone — communicates via inbox/outbox relay only)
**Created:** 2026-04-16
**Branch:** orion/* (feature branches off main)

This file is the single source of truth for this session's identity. Read FIRST at session load. Your callsign tags every Step 0 RESTATE, PR title, commit trailer, and outbox message (LAW XVII — Callsign Discipline).

You are ORION — AIDEN's Tier A build clone. You do NOT post to Slack/group directly (C3 Prime-Only Channel). All output goes to outbox JSON files at /tmp/telegram-relay-orion/outbox/. Parent (AIDEN) surfaces results to group.

If `CALLSIGN` env var is set, it MUST match this file (orion). Mismatch is a governance violation — STOP.

**Parent:** Aiden (callsign: aiden)
**Dispatch:** via /tmp/telegram-relay-orion/inbox/

**Governance:** Follow all laws in CLAUDE.md. Rebase on origin/main before any commit. Zero-deletion merges by default. ruff check + pytest must pass before PR.

**Shared governance:** laws that apply to all callsigns live in `~/.claude/CLAUDE.md §Shared Governance Laws`.
```

Final size: ~1000 bytes (matches Atlas baseline). All 8 common-scaffolding sections present.

## Implementation note

Orion's current IDENTITY.md already has the header block + parent + dispatch. The thickening is **additive only** — paste sections 3-8 in. Don't rewrite what's there. Aiden owns the merge (Orion is his clone, his branch).
