# SOP: Architecture Source of Truth Discipline

**Status:** ACTIVE
**Effective:** 2026-05-07 (on merge of PR #606)
**Authority:** CEO directive (2026-05-07)
**Applies to:** All agents (Elliot, Aiden, clones)

## 1. Canonical Sources

Architecture state lives in exactly TWO places:
- **ARCHITECTURE.md** — pipeline, vendors, tiers, deprecated items
- **Drive Manual** (Doc ID: 1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho) — CEO-facing mirror

Everything else (CLAUDE.md, .claude/modules/, ceo_memory snapshots, training knowledge) is a POINTER or CACHE. Never quote architecture from a cache.

## 2. Session Start (HARD BLOCK)

Before any directive work:
1. Read ARCHITECTURE.md fresh (cat, not from memory)
2. Read dave_corrections table (`SELECT * FROM public.dave_corrections ORDER BY corrected_at DESC LIMIT 20`)
3. If architecture was last validated >7 days ago, flag before proceeding

Skipping this is a governance violation.

## 3. Before Quoting Architecture

Before stating pipeline stages, channels, vendors, or tier specs:
1. Verify claim against ARCHITECTURE.md (read fresh, not cached)
2. If ARCHITECTURE.md doesn't cover the claim, check Drive Manual
3. If neither covers it, say 'unverified — not in SSOT' — do NOT fill from training data

Never fill architecture gaps from training knowledge or stale module files.

## 4. CLAUDE.md and Module Files

CLAUDE.md contains:
- Identity, governance, process, agent assignment
- One-line POINTERS to ARCHITECTURE.md sections

CLAUDE.md NEVER contains:
- Pipeline stage descriptions
- Vendor lists or comparisons
- Channel enumerations
- Enrichment tier specs

.claude/modules/ files follow the same rule — pointers only, no state duplication.

## 5. Deprecated Items

ARCHITECTURE.md Section 3 is the canonical deprecated list. Items currently deprecated:
- Direct mail (channel — removed permanently)
- Lemlist (never adopted — Salesforge is canonical)
- SmartLead (dropped from watchlist — Salesforge is canonical)
- All items in Section 3 table

Before proposing any vendor or channel, check Section 3 first.

## 6. Sub-Agent Prompts

When briefing sub-agents on architecture:
- Reference 'see ARCHITECTURE.md Section X' — never paste pipeline prose
- Do not include tier sequences, vendor names, or channel lists in prompt text
- Sub-agents must read the source themselves

## 7. Freshness Headers

Every architecture doc carries a 'Last validated: YYYY-MM-DD' header. When you make substantive edits (add/remove/modify sections), update the date. Read-only verification doesn't bump the date.

## 8. Drift Detection

Layer 6 hook (`scripts/ssot_drift_check.sh`) fires on the **SessionStart:clear** hook event (scripts/ssot_drift_check.sh per PR #606) and:
- Checks .claude/modules/ for size, pointer presence, forbidden patterns
- Warns if divergence detected before any directive work proceeds

Hook runs in fail-WARN mode (exit 0 always) — surfaces drift without blocking session start.

## 9. Violations

Quoting stale architecture as current = governance violation. Correct immediately:
1. Retract the claim in group chat
2. Post the correct information AS A POINTER (e.g. 'see ARCHITECTURE.md §X') — not as a paraphrase. Paraphrases in chat history can be re-extracted later as truth, recreating the original drift.
3. Check whether the stale source still exists — if so, file PR to fix or archive it
