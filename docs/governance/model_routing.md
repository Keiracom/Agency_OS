# Model Routing — Core System Fact

Ratified 2026-05-20. Canonical source of truth for which LLM each tier runs
on. This file exists because the routing fact was absent from memory
entirely (the "Anthropic error" — a memory-content audit found no agent had
the worker-vs-governance model split). It lives in `docs/governance/` so the
Cognee auto-ingest watcher carries future edits into memory automatically.

## Worker / agent tier

The agent fleet — deliberators **Elliot, Aiden, Max** and workers
**Orion, Atlas, Scout, Nova** — runs as Claude Code sessions on a
**Claude Max OAuth subscription**. Agent sessions are billed through that
subscription, NOT through the Anthropic API, and do NOT consume
`ANTHROPIC_API_KEY`.

## Internal governance / listener tier

Internal governance and listener subsystems — Slack-listener discernment,
enforcement, query-expansion, save-extraction, embeddings — route through
LiteLLM to **OpenAI (primary) and Gemini (failover)**. Per the ratified
governance-routing policy change (PR #1106): `infra/litellm/config.yaml`
sets OpenAI primary (weight 10) + Gemini failover (weight 1); the Anthropic
deployment was removed. `litellm_boot_check.py` makes OpenAI the mandatory
governance model.

## Rule

- Worker/agent sessions → Claude Max OAuth subscription.
- Internal governance / listener LLM calls → OpenAI or Gemini, **never
  Anthropic**.
- This is distinct from the *product's* use of Anthropic: ARCHITECTURE.md §4
  lists "Anthropic API — Claude Haiku" as a live PRODUCT vendor (the voice
  persona, enrichment LLM calls). That product usage is unaffected by this
  rule — this rule governs the agent fleet and the internal governance tier
  only.
