---
name: cognee-recall
description: Semantic recall over the Agency OS governance corpus (Cognee Phase 1 graph). Returns top-N matched chunks for a natural-language query.
---

# Cognee Recall

Semantic search over the ingested governance corpus (MANUAL + ARCHITECTURE + DEFINITION_OF_DONE + `.claude/modules/` + skills + per-worktree identity/heartbeat). 4332 nodes / 6486 edges live in the Cognee graph as of Phase 1 Stream 1 ingest.

## When to invoke

- Mid-task: "what does `domain_metrics_by_categories` mean in our stack?"
- Onboarding: "what's the governance pattern for X?"
- Audit: "where is policy Y defined?"
- Cross-reference: "which skill handles Z?"

**Don't invoke for:**
- Code-level questions (just read the code)
- Real-time state (use `bd ready` / `gh pr list` / `git log`)
- External facts (use web search)

## Two invocation paths

### 1. Automatic (inbox-watcher dispatch enrichment)

Per KEI-7 wiring: when an inbox-watcher reads a new dispatch file for a clone callsign (atlas / orion / scout), the CONTENT is piped through `scripts/cognee_recall.py` before the `tmux send-keys` injection. The agent reads the enriched dispatch with relevant governance corpus chunks prepended as a `## Cognee context` comment block.

Operator wiring (post-merge): edit `/home/elliotbot/clawd/scripts/<callsign>_inbox_watcher.sh` and replace:

```bash
tmux send-keys -t "$TMUX_TARGET" "$CONTENT" 2>/dev/null
```

with:

```bash
ENRICHED=$(echo "$CONTENT" | /home/elliotbot/clawd/Agency_OS/.venv/bin/python3 \
    /home/elliotbot/clawd/Agency_OS/scripts/cognee_recall.py 2>/dev/null || echo "$CONTENT")
tmux send-keys -t "$TMUX_TARGET" "$ENRICHED" 2>/dev/null
```

The `|| echo "$CONTENT"` belt-and-braces guard ensures dispatch delivery never blocks on Cognee health.

### 2. On-demand (agent invokes directly)

```bash
echo "What is the Agency OS enrichment stack?" | \
  /home/elliotbot/clawd/Agency_OS/.venv/bin/python3 scripts/cognee_recall.py
```

Or with explicit args:

```bash
scripts/cognee_recall.py --text "What is the recall backend convention?" \
    --limit 3 --org-id keiracom_platform --app-id agency_os
```

## Required env

| Var | Source | Notes |
|-----|--------|-------|
| `GEMINI_API_KEY` OR `LLM_API_KEY` | `/home/elliotbot/.config/agency-os/.env` | LiteLLM auth for Gemini-backed search. Phase 0 + 1 verified GEMINI_API_KEY alias works (Cognee 1.0 reads LLM_API_KEY directly). |

If no key set, wrapper passes through dispatch unchanged (fail-open).

## Fail-open contract

Every failure mode emits the original dispatch text unchanged and exits 0:

- Cognee SDK not importable (run from shared venv that hit mistralai corruption per session-2026-05-12 evidence)
- Cognee service offline / unreachable
- Search query raises
- Search returns no hits
- Missing API key
- Argparse error

Caller (inbox-watcher) pipes through with `|| echo "$CONTENT"` redundancy. **Dispatch delivery never blocks on knowledge-graph health.**

## Prime callsigns (elliot / aiden / max)

This skill's inbox-watcher wiring is currently scoped to clone callsigns (atlas / orion / scout). The prime callsign delivery path needs an audit before applying the same pattern. Follow-up PR.

## Related

- `scripts/cognee_ingest.py` — feeds the corpus the recall searches
- `src/cognee/client.py` — wrapper interface (sole call surface)
- `docs/audits/memory_audit_2026-05-12.md` — corpus content lineage
- Phase 1 ingest evidence: 4332 nodes / 6486 edges / `$0.019 AUD` Stream 1 cost
