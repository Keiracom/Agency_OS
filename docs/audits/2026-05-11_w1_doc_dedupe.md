# W1 Doc-Dedupe Audit — 2026-05-11

**Owner:** Aiden
**Trigger:** Elliot dispatch 2026-05-11 23:49 UTC ("Begin W1 doc-dedupe — walk through CLAUDE.md + modules, identify LAWs cited but not referenced anywhere in code or process. Build a removal list").
**Scope:** `.claude/modules/*.md` (13 files, 177 LOC total) + `CLAUDE.md` (48 LOC).

## LAW citation × code-reference cross-check

| LAW | Cited in module | Cited in src/ + scripts/ | Runtime-enforced | Disposition |
|-----|-----------------|--------------------------|------------------|-------------|
| LAW I-A | `_law_architecture_first.md` | 0 hits | None | KEEP — soft guidance, no runtime |
| LAW II | none | 10+ hits (`AUD SSOT`) | App-layer constant `settings.aud_per_usd` | KEEP — code-referenced |
| LAW VI | `_mcp_bridge.md` | 0 hits | Skill/MCP decision tree (process) | KEEP — operational guidance |
| LAW IX | `CLAUDE.md` (Supabase memory) | 0 hits | Supabase tables (operational) | KEEP — points to live infrastructure |
| LAW XII | none in modules | `austender_discovery.py`, `abn_match.py` | Skills-first contract | KEEP — code-referenced |
| LAW XIII | none in modules | `austender_discovery.py` | Skill currency (process) | KEEP — code-referenced |
| LAW XV-D | `_law_step0.md` | 0 hits | Enforcer R2 deterministic check | KEEP — runtime-enforced + doc-bound |
| LAW XVI | `_law_clean_tree.md` | 0 hits | Pre-commit hook (none) | KEEP — soft guidance |
| LAW XVII | `_session_start.md` + IDENTITY.md | `chat_bot.py`, `relay_watcher.sh` (5 hits) | `slack_relay.py` allowlist (PR #708) | KEEP — both doc + code + runtime |

**Conclusion:** No LAW citations are dead. All cited LAWs either have code references, are runtime-enforced, or are soft operational guidance that still adds value.

## Redundant content (eliminated this PR)

**`_session_start.md` Manual section** — pre-edit had 3 paragraphs (steps 1 / 2 / 3) all about the lazy-loaded Manual:
- Step 1: full lazy-load explanation
- Step 2: "do not work from stale memory" (re-statement of step 1)
- Step 3: "if unreachable, STOP" (folds into step 1 conditional)

Plus a trailing sentence "This overrides all other startup steps. The Manual is ground truth." — contradicts the lazy-load disposition (Manual is NOT consulted at session start; only on first cross-reference).

Consolidated to one paragraph. Net: -4 LOC, eliminates the contradiction.

## Out-of-scope candidates (deferred)

- **`ARCHITECTURE.md` references** in 3 modules (`_enrichment_path.md`, `_dead_references.md`, `_law_architecture_first.md`) — point to different §SECTION numbers, not redundant.
- **`_governance_rules.md`** — references the 7 consolidated rules (Dave SSOT). Doc layer over runtime rules — keep.
- **`_completion_discipline.md`** (PR #717) — overlaps with runtime gates (`verify_gate.py` PR #703 + `claim_verifier.py` PR #719) but Max shipped the doc layer today; not retiring under 24h.
- **`_hierarchy.md`** (PR #706) — doc-only org chart. No runtime equivalent.

## Recommendation

W1 audit closes here. Recommend NO further LAW retirement from modules — the audit confirms all citations are load-bearing. Doc-dedupe value-add was the `_session_start.md` Manual-paragraph consolidation alone.

W3 (memory pin audit, Aiden, deferred per Dave) and the broader Memory Audit Workstream (Aiden + Elliot, queued post-PR-B observation) cover the higher-volume dedupe target.
