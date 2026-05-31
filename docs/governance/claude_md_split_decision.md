# CLAUDE.md Split Decision — Fleet Repo vs Product Repo

**Phase 1.2.5 bundle artefact** (required per `ceo:agency_os_keiracom_separation_v1`).  
Authored 2026-05-31. Governs how `CLAUDE.md` is divided between the fleet repo
(current, internal) and the new product repo (Keiracom System, customer-facing).

---

## Decision

The two repos serve fundamentally different purposes and their `CLAUDE.md` files must
be independent. No content from the fleet `CLAUDE.md` is inherited by the product repo.
Every reference in a product-repo `CLAUDE.md` must be true for a product-repo agent
context — fleet-internal details (callsigns, worktree paths, Telegram relay, ceo_memory
table, governance LAWs specific to the fleet) do not belong there.

---

## Fleet repo CLAUDE.md — what stays

The existing `CLAUDE.md` (and its `@`-included modules) remains unchanged in the fleet
repo. It contains:

- Callsign discipline (Elliot, Aiden, Max, Atlas, Orion, Scout, Nova)
- Worktree paths (`/home/elliotbot/clawd/Agency_OS-*`)
- Telegram relay / NATS substrate / inbox-watcher configuration
- ceo_memory table (Supabase `jatzvazlbusedwsnqxzr`) as SSOT
- Fleet governance LAWs (LAW I through LAW XVII, GOV-8 through GOV-12)
- EVO Protocol, Step 0 RESTATE, Three-Store Completion
- Session startup/shutdown protocol (Manual read, Slack verify, clone awareness)
- Beads issue tracker (`bd` commands)

None of this transfers to the product repo. It is fleet-internal operational context.

---

## Product repo CLAUDE.md — what gets its own file

The product repo (`keiracom-system`, working name) requires a fresh `CLAUDE.md` written
for product-repo agent context. It contains:

**What transfers (proven components, renamed for product context):**

| Fleet concept | Product equivalent |
|---|---|
| `api_agent_cold_start` (ephemeral hop agent) | same — kept verbatim |
| Persona definitions | same — kept verbatim, minus fleet callsign tags |
| Dual-concur governance layer | same — 2-of-3 deliberator concur before merge |
| GOV-12 (gates as code, not comments) | same — runtime enforcement required |
| 50-line limit → spawn sub-agent | same |
| Skills-first operations (use skill → MCP → exec hierarchy) | same |
| GitHub visibility requirement (all work pushed before reporting complete) | same |

**What is product-specific (authored fresh):**

- Product repo path and worktree location on Vultr VPS
- Temporal workflow entry point (chain = workflow, hop = activity)
- Vault secret resolution (no env-var passthrough carve-outs)
- LiteLLM routing (all API calls via LiteLLM proxy, not direct SDK)
- Hindsight MAL primitives (Ingest, Recall, Synthesize, Supersede, Trace, Delete)
- Self-hosted Postgres connection (not Supabase)
- Product repo CI gates (imports nothing from fleet or archive)
- Ephemeral build-hop commit protocol (git credentials via Vault, commit within activity)
- Phase 0 verification gate ledger location (`gates/ledger.jsonl`)

**What is explicitly excluded from the product CLAUDE.md:**

- Fleet callsigns and worktree paths
- Telegram relay / NATS inbox-watcher / tmux session references
- ceo_memory Supabase table (fleet SSOT; product has its own memory namespace)
- Fleet governance LAWs by number (the principles transfer; the LAW numbering does not)
- Session startup protocol referencing the Agency OS Manual or fleet Drive Doc
- Beads (`bd`) commands (product repo uses its own issue tracker or bd with `--repo` tag)

---

## Governance gate

Per `ceo:agency_os_keiracom_separation_v1` consolidated gates:

> "CLAUDE.md split decision before first migration PR"
> "CI gate: product repo imports nothing from fleet or archive repos"

This document satisfies the split decision gate. The CI gate (enforcing no fleet imports
in the product repo) is a Phase 2 build item and is not part of this artefact.

---

## Authorship and review

- Author: Aiden (architecture/governance lens)
- Eligible reviewers: Elliot (implementation-feasibility) + Max (code quality)
- 2-of-2 concur required (author-exclusion: Aiden authored)
