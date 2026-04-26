# P7 — Managed Agents Evaluation

**Date:** 2026-04-26
**Author:** SCOUT (research clone)
**Branch:** `scout/p7-managed-agents-eval`
**Mission:** Evaluate whether Anthropic Managed Agents (GA 2026-04-08, public beta) could replace our custom EVO sub-agent harness AND host EVO + DSAE + Clone Queue Board governance inside a Managed Agent session.
**Verdict (TL;DR):** **PARTIAL — Adopt for single-task SCOUT-style research clones; reject for ELLIOT/AIDEN multi-bot peer-review orchestration until `multi-agent coordination` exits research preview.**

---

## 1. Managed Agents Capabilities Catalog

### 1.1 Launch and pricing

- **GA / public beta:** 2026-04-08, available to all Anthropic API accounts ([Anthropic engineering](https://www.anthropic.com/engineering/managed-agents); [InfoQ](https://www.infoq.com/news/2026/04/anthropic-managed-agents/)).
- **Pricing:** USD $0.08 per **active** session-hour + standard token rates (Opus 4.7 / Opus 4.6 / Sonnet 4.6). Idle time (waiting for user input or tool confirmation) does **not** accrue. Web search is $10 per 1,000 calls. Replaces — does not stack on top of — Code Execution container-hour billing ([WaveSpeedAI pricing breakdown](https://wavespeed.ai/blog/posts/claude-managed-agents-pricing-2026/)).
- **AUD impact (1 USD = 1.55 AUD):** $0.124 AUD per session-hour. Four concurrent clones × 12h × 30 days ≈ $179 AUD/month base before tokens. Non-trivial but not blocking.
- **Beta header:** `anthropic-beta: managed-agents-2026-04-01` required on every request; SDK injects automatically.

### 1.2 Core abstractions ([overview docs](https://platform.claude.com/docs/en/managed-agents/overview))

| Concept | Role |
|---|---|
| **Agent** | Saved config: model, system prompt, tools, MCP servers, skills. Versioned. |
| **Environment** | Cloud container template (packages, network policy `unrestricted` or `limited`). Capped at **5 concurrent**. |
| **Session** | A running instance of (Agent × Environment). Append-only event log. |
| **Events** | `user.message`, `user.custom_tool_result`, status updates. SSE stream + polling. |

### 1.3 Endpoints ([API reference](https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/managed-agents-api-reference.md))

`/v1/agents`, `/v1/sessions`, `/v1/sessions/{id}/events`, `/v1/environments`, `/v1/vaults` (MCP credential vaults), `/v1/memory_stores` (versioned, redactable), `/v1/skills`, `/v1/files`. Session resources can mount `github_repository` (token, branch/commit checkout) or `memory_store`.

### 1.4 Session model and durability

Anthropic's engineering post explicitly decouples **Session** (durable append-only log) from **Harness** (Claude loop) from **Sandbox** (container). `getEvents()`, `wake(sessionId)`, `provision({resources})` are exposed as recovery primitives. Containers fail independently; harness reboots replay from event log. TTFT improved 60% p50 / 90% p95 by deferring container provisioning.

### 1.5 Tools and skills

Built-in: Bash, file ops (read/write/edit/glob/grep), web search/fetch, MCP servers (HTTP). Per-agent caps: 50 tools, 64 skills, 20 unique MCP servers. Custom tools share the `execute(name, input) → string` interface.

### 1.6 Rate limits

- Create endpoints (agents/sessions/vaults/etc.): **60 RPM** org-level
- Read endpoints (retrieve/list/stream): **600 RPM** org-level
- Environments: 60 RPM, **5 concurrent**
- Standard ITPM/OTPM tier limits still apply to model inference.

### 1.7 Governance / observability

Console renders structured timeline traces; click any tool call for arguments + response; replay supported. Triggers: HTTP, webhook, cron, programmatic ([MindStudio dashboard guide](https://www.mindstudio.ai/blog/anthropic-managed-agents-dashboard-guide)). Vaults provide MCP credential isolation — credentials never reach the harness.

### 1.8 Research-preview features (gated; require [access form](https://claude.com/form/claude-managed-agents))

- **`outcomes`** — declarative success criteria
- **`multi-agent`** — split-and-merge fan-out to up to 10 sub-agents within one session
- **memory** (advanced) — durable cross-session memory store
- **Self-evaluation** — agent grading own runs

This is the single biggest constraint for our use case (see §2).

---

## 2. Compatibility Matrix vs Agency OS Governance

| Governance primitive | Native fit | Gap | Workaround |
|---|---|---|---|
| **Step 0 RESTATE** (LAW XV-D) | ✅ Native — agent waits on `user.message` events. Pause-for-Dave is the default loop. | None | System prompt enforces RESTATE-first behavior. |
| **EVO Decompose → Present → Execute → Verify → Report** | ✅ Fits a single session naturally; tracing gives Verify/Report for free. | None | — |
| **Three/Four-store completion** (LAW XV) — Supabase ceo_memory + cis_directive_metrics + MANUAL.md + Drive | ✅ All four already external; connect as MCP servers. Memory Stores are an **additive** managed substrate, not a replacement. | Doubles persistence layer if we mount Memory Stores too. | Use existing Supabase MCP; ignore Memory Stores until Drive parity is needed. |
| **Skills-First (LAW VI / XII)** | ✅ Skills are first-class — `/v1/skills` versioned with `anthropic` and `custom` types. | Our skills are bash/Node; need port to Skill API schema. | 2–3 day port. |
| **Telegram routing** | ✅ Wrap relay as HTTP MCP server. | None | — |
| **Callsign discipline (LAW XVII)** | 🟡 Encode in agent system prompt + agent name. | No platform-level callsign isolation. | Agent-per-callsign + metadata tags. |
| **Worktree isolation (per-callsign branch)** | 🟡 `Environment` mounts a `github_repository` resource with branch/commit checkout. | Environments are container templates, not git worktrees. Concurrent edits to same branch from two sessions need coordination. | One Environment per callsign + branch convention preserved externally. |
| **Claim-Before-Touch on shared files** | ❌ No primitive. | Cross-session locking absent. | External coordination via Telegram relay (status quo). |
| **DSAE-DELAY (Elliot-first, 10s, Aiden agree/differ)** | ❌ Cross-session synchronisation is `multi-agent` research preview. | Two parallel sessions cannot natively wait on each other. | Either (a) get research-preview access, or (b) keep DSAE in external orchestrator. |
| **Clone Queue Board** (current/next per clone, peer reads) | 🟡 Memory Stores can hold board state; both sessions mount the same store as a resource. | No native pub/sub on memory writes — peer must poll. Polling burns 600 RPM read budget fast. | External Redis pub/sub (status quo) or accept polling cost. |
| **Constant Progression Rule** | ✅ System prompt + tool constraint. | None | — |
| **Per-PR peer review (clones cross-review)** | ❌ Two sessions reviewing each other's branches need cross-session orchestration. | `multi-agent` research preview again. | External orchestrator (status quo). |
| **Sub-agent fan-out (research-1, build-2, …)** | 🟡 Marketing references "split-and-merge to up to 10 sub-agents," but the API reference explicitly notes the **sub-agent spawn endpoint is not in the public beta**; gated behind `multi-agent` preview. | Hard block for parallel agent dispatch. | Continue spawning sub-agents externally OR request preview access. |
| **Gates as Code (GOV-12)** | 🟡 No documented `pre-tool` / `post-tool` / `on-error` interceptors. | Cannot enforce LAW XV gates at platform layer. | System prompt + MCP server wrappers (current model). |
| **Raw Output Mandate (LAW XIV)** | ✅ Console traces capture verbatim tool I/O. | None | — |
| **Step 0 immutability + audit** | ✅ Append-only event log; Memory Versions support `redact` (no delete). | Mature audit story. | — |

**Net read:** Single-session, single-agent governance maps cleanly. Multi-bot coordination — which is the heart of DSAE, Clone Queue Board, and per-PR peer review — does not, because the multi-agent primitive is research-preview-gated.

---

## 3. Migration Cost vs Benefit

### 3.1 Gained (if we migrate)

- **Durable session log + harness recovery** — replaces our ad-hoc tmux + relay state.
- **Container/credential isolation via Vaults** — better than env-file sharing.
- **Built-in prompt caching + compaction** — token savings on long EVO runs (likely 20–40%).
- **Console tracing** — replaces manual `LAW XIV` raw-output capture.
- **Faster TTFT** — 60% p50 / 90% p95 improvement over self-built harness.
- **Skill versioning + archive** — better than git-only tracking.

### 3.2 Lost (if we migrate)

- **Multi-bot peer review** — research-preview-gated; cannot match current DSAE workflow.
- **Self-hosting** — Anthropic-only execution; loses Railway redundancy and on-prem optionality. **Vendor lock to Claude models** (no GPT-5/Gemini/Kimi fallback).
- **Worktree-per-callsign git isolation** — must restructure to Environment-per-callsign.
- **Cost floor** — ~$179 AUD/month base for 4 concurrent clones before tokens.
- **External rate limit surface** — 60 RPM create / 5 concurrent environments are tight if we ever fan out to 10+ clones.

### 3.3 Engineering effort to migrate

| Workstream | Estimate |
|---|---|
| Port `/skills/*` to Skill API schema | 2–3 days |
| Wrap Telegram relay as HTTP MCP server | 1–2 days |
| Build Agent definitions per callsign (ELLIOT, AIDEN, SCOUT, ATLAS, ORION) | 1 day |
| Re-implement DSAE coordination external to sessions (or wait for multi-agent GA) | 3–5 days OR blocked-on-Anthropic |
| Wire Supabase + Drive MCPs | 1 day |
| Migrate four-store completion check to MCP | 1 day |
| Operational runbook + cost dashboard | 1 day |
| **Total** | **~10–15 engineer-days, with DSAE work blocked on research-preview access** |

---

## 4. Recommendation — PARTIAL

### 4.1 Adopt now

**Single-task research/build clones with no peer-review requirement.** Concretely:

- **SCOUT** (this bot) — research, web fetch, file outputs, no PR cross-review. One agent, one session per dispatch. Maps perfectly to Managed Agents.
- **One-shot devops jobs** — Railway redeploys, Vercel previews, Supabase migrations. Long-running, sandbox-friendly, single-output.
- **Listener log triage** — periodic cron-triggered sessions over the Telegram log.

For these, Managed Agents replaces our tmux-relay-watcher pattern with native session durability and saves an estimated ~$30–50 AUD/month in dev-time-equivalent maintenance.

### 4.2 Reject now (revisit when `multi-agent` exits preview)

**ELLIOT + AIDEN + ATLAS + ORION orchestration.** Reasoning:

1. **DSAE-DELAY and Clone Queue Board require cross-session coordination.** That is the `multi-agent` research-preview surface; without it, we either (a) request preview access and still build coordination glue, or (b) keep external orchestration — at which point we've absorbed Managed Agents pricing without the platform-level coordination win.
2. **Worktree-per-callsign isolation is stronger than Environments for code review.** Our current model gives each bot a real git worktree on disk; merging happens via PRs cross-reviewed by the other bot. Environments mount repos but don't model worktrees-as-callsign.
3. **Vendor lock-in cost compounds at the orchestration layer.** Single-purpose research clones are cheap to swap. EVO + DSAE + Clone Queue Board is months of governance ratification — porting it to a Claude-only platform we cannot self-host is a meaningful resilience regression.
4. **No platform-level governance hooks.** GOV-12 (Gates as Code) prefers runtime enforcement; Managed Agents lacks documented `pre-tool`/`post-tool`/`on-error` interceptors. We'd still rely on system prompt + MCP wrappers — the same enforcement surface we have today.

### 4.3 Suggested follow-up directives

- **P7-A** — Pilot Managed Agent for SCOUT only. One agent definition, one Environment with `unrestricted` networking, MCP for Supabase + Telegram. Compare cost and TTFT vs current tmux-relay model over 14 days.
- **P7-B** — Submit research-preview access request for `multi-agent` and `outcomes`; track Anthropic GA timeline. Re-evaluate ELLIOT/AIDEN migration when multi-agent ships GA.
- **P7-C** — Port `skills/mcp-bridge` MCP servers to standalone HTTP MCP servers so they're consumable by Managed Agents without rewrite (decoupling investment regardless of migration decision).

---

## Sources

- [Anthropic — Scaling Managed Agents engineering blog](https://www.anthropic.com/engineering/managed-agents)
- [Claude Managed Agents overview docs](https://platform.claude.com/docs/en/managed-agents/overview)
- [Managed Agents API reference (anthropics/skills GitHub)](https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/managed-agents-api-reference.md)
- [InfoQ — Anthropic Introduces Managed Agents (April 2026)](https://www.infoq.com/news/2026/04/anthropic-managed-agents/)
- [WaveSpeedAI — Managed Agents Pricing & Beta Limits](https://wavespeed.ai/blog/posts/claude-managed-agents-pricing-2026/)
- [Sathish Raju — Reading the Fine Print on Managed Agents](https://medium.com/@sathishkraju/anthropics-managed-agents-i-read-the-fine-print-so-you-don-t-have-to-ed17b77e17c5)
- [MindStudio — Managed Agents Dashboard Guide](https://www.mindstudio.ai/blog/anthropic-managed-agents-dashboard-guide)
