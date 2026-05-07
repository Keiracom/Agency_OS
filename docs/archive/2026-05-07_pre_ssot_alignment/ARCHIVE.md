# Pre-SSOT-Alignment Archive (2026-05-07)

These docs were valid at the time of authorship but pre-date the **2026-05-07 SSOT-alignment governance correction**. They are preserved here for historical reference; **do not extract them as current architecture**.

## Why these were archived

In the 2026-05-07 session, both `[ELLIOT]` and `[AIDEN]` independently quoted stale pipeline architecture (`T0 GMB → T1 ABN → T1.5 SERP → ... → T5 Leadmagic Mobile`) and a deprecated channel (Mail) as if they were current. Root cause: stale prose in `CLAUDE.md` modules, `docs/`, and `ceo_memory` keys was extracted from auto-loaded context and treated as truth, instead of reading the canonical source (`ARCHITECTURE.md` + Drive Manual) fresh.

CEO directive (Dave) and COO relay (Max) ratified a multi-layer fix:

- **Layer 1 (Aiden):** Strip pipeline/channel/vendor prose from `CLAUDE.md` + `.claude/modules/` in both worktrees; replace with one-line pointers to `ARCHITECTURE.md` sections. Add Lemlist + SmartLead as deprecated to `ARCHITECTURE.md` §3.
- **Layer 5 (Elliot — this PR):** Move stale architecture docs in `docs/` to this archive directory; archive stale `ceo_memory` keys (moved to `ceo_memory_archive` table); archive stale `agent_memories` rows referencing deprecated architecture.
- **Layer 3 (both):** Memory pins requiring fresh `ARCHITECTURE.md` reads before quoting pipeline/channel/vendor facts.
- **Layer 6 (Aiden, follow-up):** Session-start drift detection hook (warns on divergence between `.claude/modules/` and `ARCHITECTURE.md`).

## Canonical sources going forward

- `/home/elliotbot/clawd/Agency_OS/ARCHITECTURE.md` — pipeline (FLOW A + FLOW B), live vendors, deprecated vendors, enrichment tier specs.
- Drive Manual (Doc ID `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho`) — CEO-facing SSOT mirror.
- `public.ceo_memory` (current keys only; archived snapshots in `public.ceo_memory_archive`).

## Files in this archive

- `lessons_2026-04-20.md` — pre-SSOT-alignment lessons doc.
- `claude_md_consolidation_plan.md` — superseded by the 2026-05-07 governance correction.
- `audits/p4_prefect_status_2026-04-21.md` — pre-Pipeline-F-v2.1-validation Prefect audit.
- `pipeline-brief-for-claude.md` — stale pipeline framing (highest extraction risk).
- `e2e/SDK/SDK_IMPLEMENTATION_SPEC.md` — references stale enrichment path.
- `architecture/business/SCORING.md` — referenced stale enrichment path; current scoring lives in code (`src/pipeline/`) + `ARCHITECTURE.md` §5.
- `governance/RULE_CONSOLIDATION_PROPOSAL.md` — superseded by ratified `docs/governance/CONSOLIDATED_RULES.md`.

If you need the historical content, read it here. **Do not paraphrase or extract into new docs as current state.**
