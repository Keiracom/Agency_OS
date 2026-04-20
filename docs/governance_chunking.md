# Governance Chunking Rules

Defines what content from CLAUDE.md, docs/MANUAL.md, and ARCHITECTURE.md gets ingested into `public.agent_memories` so the listener can whisper it on retrieval.

Established under directive LISTENER-KNOWLEDGE-SEED-V1 (2026-04-19).

## Principle

The listener searches `agent_memories` semantically. Index content that answers factual queries about the product, stack, pipeline, governance, and economics. Do not index prose that tells Claude how to behave — that pollutes retrieval and burns L2 discernment tokens on meta-matches.

## INCLUDE

- **Tables:** pricing tiers, dead-ref → replacement maps, LAW index, provider stack, enrichment stage costs, category ETV windows, ALS gates, margin tables.
- **Numeric thresholds + named constants:** `PRE_ALS_GATE = 20`, `HOT_THRESHOLD = 85`, per-stage parallelism values, similarity thresholds, monthly record caps.
- **Law body text:** each LAW I through LAW XVIII as its own chunk — the rule statement + its consequences. One chunk per law.
- **Stage definitions:** each enrichment stage (T0, T1, T1.5a, T1.5b, T2, T2.5, T3, T5, T-DM0 through T-DM4) as its own chunk with vendor + cost + output fields.
- **Decision records with rationale:** directive-level decisions that ratify an approach, with the *why*.
- **Service-tier mappings:** pricing tier → capacity → included features.
- **Compliance rules:** SPAM Act 2003, DNCR, TCP Code, Privacy Act — one chunk per rule with the obligation it creates.
- **Named vendor + cost + API endpoint mappings** from the provider stack section.
- **Business universe + territory rules** from onboarding/campaign model.

## EXCLUDE

- **Claude-instruction prose:**
  - `Step 0 RESTATE` format blocks and prose directing Claude what to output
  - `Session Startup` bullet lists (they're instructions to the bot, not product facts)
  - `READ THE MANUAL FIRST` HARD BLOCK wording
  - `Directive Acknowledgement` protocol text
  - `MANDATORY STEP 0 RESTATE ON EVERY DIRECTIVE` sections
- **Persona / voice-shaping:**
  - `Who You Are` / `You are Elliottbot` intro prose
  - `Core Truths` SOUL excerpts
  - `Default mode is TERSE` style guidance
- **Meta reminders:**
  - `Never skip steps`, `Never execute before approval`, `Never summarise output`
  - `Completion Alerts — MANDATORY` boilerplate
  - `/kill — Emergency Stop` procedure (operational, not factual)
- **Claim-Before-Touch protocol text** (process, not fact)
- **Generic onboarding narrative** ("Your job is to decompose, delegate, verify...")
- **Code files** — embeddings on English corpus don't rank source code meaningfully; leave as-is
- **Directive execution logs** older than the current sprint — already covered by `daily_log` rows
- **Build sequence sprint plans** (e.g. MANUAL.md Section 13 v7 Sprint Plan) — too volatile; lives in git history

## Chunk metadata

Every ingested row must carry:

```
{
  callsign: null,               // not tied to a session
  source_type: 'verified_fact',
  state: 'confirmed',
  content: <chunk body, 100-500 tokens>,
  typed_metadata: {
    source: 'governance_doc',
    origin_file: <absolute path>,
    section: <section heading>,
    sub_section: <optional>,
    ingested_by: 'LISTENER-KNOWLEDGE-SEED-V1',
    ingested_at: <iso8601>
  },
  tags: [<topic tags — pricing, enrichment, compliance, gate, law, stack>],
  embedding: <text-embedding-3-small vector>
}
```

## Sizing targets

- Chunk length: 100-500 tokens typical, 700 max
- Total expected ingest: 150-200 chunks
  - ~30 from the 3 CLAUDE.md files (laws, governance tables)
  - ~100-130 from MANUAL.md (sections 1-12, skip 13 directive log)
  - ~30-50 from ARCHITECTURE.md (stages, vendors, validation rules, environment)

## Future currency

This is v1 (manual curated ingest). Follow-up directive LISTENER-KNOWLEDGE-SEED-V2 should build auto-ingest: chunk+embed+upsert on commit to any of the three source files. Until then, re-run this ingest script whenever a major governance doc change lands, and bump the `ingested_by` to a new version tag.

## Verification

Post-ingest Hit Rate@5 test:
- 10 test queries covering pricing (3), enrichment (3), ALS/compliance (2), dead-refs (2)
- Pass bar: ≥8/10 return a correctly-cited factual chunk in the top-5 from L2 discernment
- Elliot spot-checks 20 random ingested rows to verify no meta-prose leaked through the filter
