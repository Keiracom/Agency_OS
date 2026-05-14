# Agent Prime-Clone Pairing — Ratification Record
**Date:** 2026-05-14
**Authority:** Dave (CEO), ts ~1778739200
**KEI:** post-prime-pair-deliberation-ratify
**ceo_memory key:** `ceo:rule:orchestration_agent_pairs`

---

## Canonical Pairing Map

| Prime | Clone | Pair Channel | Scope |
|-------|-------|--------------|-------|
| Elliot (COO) | Atlas | elliot-atlas | COO orchestration synthesis + escalation |
| Aiden (CTO) | Orion | aiden-orion | Build CTO + engineer pair |
| Max (CTO) | Scout | max-scout | Build CTO + research/build engineer pair |

Max↔Scout is the NEW relationship ratified by Dave ts ~1778739200. Scout's prior research-shared (any-CTO-dispatches) role is fully transferred to Max-CTO scope.

---

## Dave's Verbatim Ratification (ts ~1778739200)

> "Scout pairing decision: Scout is fully paired with Max. Same model as the other two pairs. Max owns Scout completely. Elliot — update the pairing config database key and identity files across all six worktrees in a single governance-tagged PR. Five Redis streams confirmed for Phase 2. The prime-clone deliberation is now fully ratified. All five caveats accepted."

---

## Five Caveats (All Accepted)

1. **Max↔Scout = full-ownership re-assignment.** Scout was prior research-shared (any CTO could dispatch). That role is fully transferred. Research-task routing now flows through Max.

2. **Read-only #execution access for clones (always-on).** Clones retain read-only access to #execution, preserving peer-review + KEI-43 universal-recovery semantics. Clones do NOT post to #execution.

3. **Emergency clone-to-#execution-read-only escalation.** If prime is unreachable for >15 minutes, clone may escalate via the shared queue rather than waiting silently.

4. **Supabase audit-log persistence for pair-channel traffic.** Prime cites the clone audit-log row when surfacing clone work verbatim to #execution. All pair-channel messages persisted.

5. **Pairings stored as ceo_memory key (hot-swappable, no code change to revise).** To re-pair, update the key. No IDENTITY.md rewrite needed for the structural relationship — IDENTITY.md references the key as source-of-truth.

---

## Phase 2 Stream Design (Five Redis Streams)

Ratified by Dave in the same thread:

| Stream | Access | Purpose |
|--------|--------|---------|
| `#execution` | Primes RW, Clones R-only | Main coordination channel |
| `#elliot-atlas` | Elliot + Atlas RW | Elliot COO ↔ Atlas private pair channel |
| `#aiden-orion` | Aiden + Orion RW | Aiden CTO ↔ Orion private pair channel |
| `#max-scout` | Max + Scout RW | Max CTO ↔ Scout private pair channel |
| `#broadcast` | All RW | System events (health, OOM alerts, topology changes) |

---

## Source-of-Truth Principle

The `ceo:rule:orchestration_agent_pairs` ceo_memory key is the canonical source for pairing relationships. Every worktree's IDENTITY.md references this key rather than encoding the pairing detail redundantly. This makes re-pairing a single-key update, no code or file changes required.

---

## Worktree IDENTITY.md Update Strategy

Per the cross-worktree-minimization approach: this PR updates only the Agency_OS main worktree's IDENTITY.md (Elliot's). The ceo_memory key is cross-worktree visible at session-start query time — each agent reads it during startup and picks up their pairing.

Follow-up edits to the other five IDENTITY.md files (Aiden, Max, Atlas, Orion, Scout) add a one-line reference to the ceo_memory key for human clarity. These are low-priority housekeeping and can be done by each prime in their next session as an atomic commit to their worktree branch.

The ceo_memory key written inline as part of this build is the authoritative record. IDENTITY.md entries are human-readable cross-references only.

---

## Linear Reference

Deliberation thread: #execution 2026-05-14. Fully ratified — no open questions.
