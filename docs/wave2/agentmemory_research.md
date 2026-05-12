# agentmemory MCP Server — Research + Drop Recommendation

**Author:** atlas
**Roadmap reference:** `ceo:roadmap_20_capabilities_phases_2026-05-11` → `phase_2_new_services[0] = "agentmemory_hybrid_mcp_server"`
**Companion tracking:** Beads `Agency_OS-oaj` (Phase 2 epic)

## Project

- **Repo:** https://github.com/rohitg00/agentmemory
- **License:** Apache-2.0
- **Install:** `npx -y @agentmemory/mcp` (stdio MCP) or `npx @agentmemory/agentmemory` (REST API on :3111). Optional Docker via `iiidev/iii:0.11.2`.
- **MCP shape:** stdio subprocess (51 tools / 6 resources / 3 prompts / 4 skills). No HTTP endpoint URL.
- **Storage:** SQLite by default (no external deps); 6 embedding providers (local, OpenAI, Gemini, Voyage, Cohere, OpenRouter).
- **Pitch:** "BM25 + vector + knowledge-graph traversal with RRF fusion" + 12 Claude-Code lifecycle hooks (SessionStart, PostToolUse, Stop) + 4-tier auto-consolidation/decay. Bidirectional `MEMORY.md` bridge. Claims **95.2% R@5 on LongMemEval-S** (vs mem0 68.5%, Letta 83.2%, BM25-only 86.2%).

## Cognee-overlap assessment

We already shipped or have in production:

| Capability | agentmemory | Cognee (this repo, PR #764) | Supabase RPC (this repo, commit 16e33445) | Compiled LLM Wiki (this repo, PR #761) |
|---|---|---|---|---|
| Vector + semantic search | ✓ (6 providers) | ✓ (Gemini text-embedding-004, pgvector) | ✓ (OpenAI text-embedding-3-small) | — |
| BM25 / keyword recall | ✓ | partial (graph traversal) | ✓ (`tsvector` + RRF in `hybrid_search_agent_memories` RPC) | — |
| Knowledge-graph entity extraction | ✓ | **✓ (Gemini 2.5 Flash via LiteLLM, primary use-case)** | — | — |
| Per-tenant isolation | partial (single SQLite) | ✓ (owner_id + tenant_id, Phase 0 wrapper) | ✓ (callsign column) | — |
| Auto-capture hook | ✓ (PostToolUse) | manual `cognify()` / `memify()` | manual `store()` | — |
| Cold-start brief | partial (`MEMORY.md` bridge) | — | — | ✓ (≤2k token wiki, weekly refresh) |
| 4-tier consolidation/decay | ✓ | — | — | — |
| Public benchmark on Claude-Code corpus | LongMemEval-S 95.2% R@5 | not measured | not measured | n/a |

Net: **agentmemory's distinguishing wins are (a) the public LongMemEval benchmark and (b) zero-config Claude-Code hook auto-capture.** Every other claimed capability is structurally covered by our existing stack — often by more than one system simultaneously.

## Roadmap drift flag

The same roadmap key still lists `pensyve_entity_aware_memory` as a Phase 2 service even though Dave's earlier directive dropped Pensyve. The `agentmemory` line is shaped identically to Pensyve and is at risk of the same drop-on-overlap pattern. Recommend updating `ceo:roadmap_20_capabilities_phases_2026-05-11` to reflect the current state regardless of the install/drop decision below.

## Recommendation: **DROP per Cognee overlap** (pending Dave confirm)

Reasons:

1. **Three SSOTs is one too many.** Aiden's memory audit just argued for retiring mem0 because three overlapping memory systems (Supabase agent_memories + Cognee + mem0) violate the one-SSOT principle. Installing agentmemory re-creates exactly that condition.
2. **The unique wins are recoverable in-house.** A LongMemEval-S benchmark harness against our `hybrid_search_agent_memories` RPC would let us measure (and beat) the same 95.2% number on our own corpus — cheaper than a new vendor surface. Auto-capture hooks can wire to Cognee's `add()` or our `store()` in a single Claude-Code hook.
3. **Maintenance load.** 51 tools + 6 resources + 3 prompts + 4 skills behind a stdio subprocess is real coordination cost when Cognee's surface is `add / cognify / memify / search`.
4. **No multi-tenant isolation story.** agentmemory's default SQLite is single-tenant. Cognee's Phase 0 wrapper already mints per-org Cognee Users for tenant safety.
5. **License + supply-chain.** Apache-2.0 is fine, but `iiidev/iii:0.11.2` Docker dependency and `iii-database` worker add a transitive runtime that isn't in our current vendor list.

If Dave overrides to install: scope the install as **stdio MCP only** (`npx -y @agentmemory/mcp`, no port 3111 REST API), single-worktree first, and gate auto-capture hooks behind explicit per-agent opt-in.

## Decision-required

- **D1:** confirm DROP, or override to install (Atlas can prepare the install PR if override).
- **D2:** update `ceo:roadmap_20_capabilities_phases_2026-05-11` to reflect post-Cognee-ship cleanup of agentmemory + pensyve entries.

Sources: https://github.com/rohitg00/agentmemory · ceo:roadmap_20_capabilities_phases_2026-05-11 · ceo:directive_10015_complete (KEI-10 ship bundle) · commit 16e33445 (hybrid BM25+RRF RPC) · PR #761 (Compiled LLM Wiki) · PR #764 (Cognee Phase 0 wrapper).
