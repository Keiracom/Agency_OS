# OpenClaw Deep Dive — Releases Since 2026.3.8

**Date:** 2026-04-26
**Callsign:** scout
**Last deployed version:** 2026.3.8 (retired April 7, 2026)
**Status:** tentative — awaiting peer review

---

## Summary

OpenClaw is **very actively developed** — multiple releases per week, 247K+ GitHub stars, 13,700+ skills in ClawHub. Since our 2026.3.8 retirement, 4 major releases shipped (2026.4.7 through 2026.4.24). Key new capabilities: Dreaming memory consolidation, REM Backfill for historical replay, TaskFlows, Session Branching, multi-model support (DeepSeek V4, xAI Grok), and browser automation. However, OpenClaw suffered **a catastrophic security vulnerability flood** in March–April 2026 (9 CVEs in 4 days, CVSS 9.9 critical, 341+ malicious skills in supply chain attack). Anthropic also imposed a paywall on April 4 — subscription users can no longer use Claude via OpenClaw without separate pay-as-you-go billing. The separate fork **Enderfga/openclaw-claude-code** (Claude Code headless wrapper) is more relevant to Agency OS and actively maintained with zero outstanding issues.

**Bottom line:** OpenClaw has valuable patterns to adopt (Dreaming, multi-agent orchestration, hook system) but the security posture is disqualifying for production. Extract the patterns; don't deploy the runtime.

---

## Project Status: Actively Developed

| Metric | Value |
|--------|-------|
| GitHub stars | 247,000+ |
| Forks | 47,700+ |
| Release frequency | Multiple per week |
| Latest release | 2026.4.24 (April 25, 2026) |
| Contributors | Active community + foundation governance |
| License | MIT |
| Creator | Peter Steinberger (joined OpenAI Feb 14, 2026) |
| Governance | Non-profit foundation announced (structure unverified) |
| Anthropic relationship | Permissive, not endorsed. Paywall imposed April 4 |

**Not stalled.** One of the fastest-growing open-source AI projects in history.

---

## Releases Since 2026.3.8

### v2026.4.7 (April 7) — TaskFlows, Memory-Wiki, Session Branching

| Feature | What It Does | Adopt/Defer/Skip |
|---------|-------------|-----------------|
| **TaskFlows** | Structured task execution with dependency tracking within agent sessions | **ADOPT pattern** — maps to EVO Decompose step. Don't adopt runtime |
| **Memory-Wiki** | Wiki-style persistent memory pages editable by agents | **DEFER** — Agency OS uses Supabase memories. Wiki format is interesting for structured knowledge but would require migration |
| **Session Branching** | Fork a session at any point, explore alternatives, merge back | **ADOPT pattern** — valuable for "what-if" exploration in directives. Implement via git worktree branching (already used) |

### v2026.4.9 (April 9) — Dreaming + REM Backfill

| Feature | What It Does | Adopt/Defer/Skip |
|---------|-------------|-----------------|
| **Dreaming (3-phase memory consolidation)** | Light Phase: short-term signal capture → REM Phase: candidate promotion to "possible lasting truths" → Deep Phase: durable persistence | **ADOPT pattern** — directly addresses listener noisy corpus problem. Implement as: daily_log → consolidation pass → core_fact promotion |
| **REM Backfill** | `memory rem-backfill --path <dir>` replays historical notes through Dreaming pipeline. Grounded backfill stages candidates into short-term store. Reversible entries written to DREAMS.md | **ADOPT pattern** — replay Agency OS's 90+ daily_logs through consolidation to extract core_facts. One-time migration tool |
| **SSRF + Node Injection Hardening** | Security patches for server-side request forgery and node injection vectors | N/A — security fix, not a feature to adopt |

### v2026.4.22 (April 20) — xAI Support + Memory Pressure

| Feature | What It Does | Adopt/Defer/Skip |
|---------|-------------|-----------------|
| **xAI Grok support** | Full provider for image gen, TTS, STT, 6 voices, G.711 audio | **SKIP** — Agency OS uses Claude/Anthropic stack exclusively |
| **Moonshot Kimi K2.6 tool-calling** | Tool-calling fixes for Moonshot models | **SKIP** — irrelevant provider |
| **tokenjuice bundle** | Token cost analytics package | **DEFER** — interesting concept but we track costs via Supabase |
| **cgroup memory pressure hardening** | Linux cgroup-based memory limits for agent processes | **ADOPT** — useful for Railway containers running agent workloads. Prevents OOM cascades |
| **OpenAI Codex removed from onboarding** | Cleanup of retired provider | N/A |

### v2026.4.23 (April 22) — Context Forking + Plugin Dependencies

| Feature | What It Does | Adopt/Defer/Skip |
|---------|-------------|-----------------|
| **Agent context forking** | Child agents inherit forked context from parent transcript. Configurable what gets inherited | **ADOPT pattern** — critical for sub-agent quality. Currently Elliottbot sub-agents start with a fresh prompt brief. Context forking passes relevant parent context automatically |
| **Plugin peer dependencies** | Skills can declare dependencies on other skills | **DEFER** — Agency OS skills are standalone. Dependency chains add complexity |
| **ElevenLabs Scribe v2** | Voice transcription integration | **SKIP** — we use Vapi/Telnyx |
| **xAI image gen + OpenRouter image editing** | Multi-provider image capabilities | **SKIP** — not relevant to outbound sales automation |

### v2026.4.24 (April 25) — Google Meet + Browser Automation

| Feature | What It Does | Adopt/Defer/Skip |
|---------|-------------|-----------------|
| **Google Meet integration** | Agent joins/participates in Google Meet calls | **DEFER** — interesting for future voice/meeting features but premature |
| **DeepSeek V4 Flash/Pro** | New model provider support | **SKIP** — Claude-only stack |
| **Realtime voice loops** | Continuous voice conversation with agent | **DEFER** — relevant when voice AI matures in Agency OS |
| **Browser automation (coordinate clicks)** | Agent can interact with web UIs via coordinate-based clicking | **DEFER** — useful for scraping/testing but Bright Data handles our web data |
| **Plugin/model infrastructure lightened** | Reduced overhead for plugin loading | N/A — internal optimization |

---

## Feature Deep Dives

### Multi-Agent Orchestration

OpenClaw supports 4 coordination patterns:

| Pattern | Description | Agency OS Equivalent |
|---------|-------------|---------------------|
| **Orchestrator-Subagent** | Central coordinator delegates to specialized executors. 80% of usage | EVO protocol — Elliottbot orchestrates build/test/review/devops agents |
| **Fan-Out/Fan-In** | Same task parallelized across N agents, results merged | Batch enrichment — same waterfall run across N domains |
| **Pipeline** | Sequential chain — output of agent A feeds agent B | Waterfall enrichment — T0→T1→T2→T3 sequential |
| **Peer-to-Peer** | Equal-status agents with direct communication, no orchestrator | Elliot ↔ Aiden peer review pattern |

**Key primitives:**
- Every agent is fully isolated (separate workspace, auth, session store)
- `agentToAgent` tool enables cross-agent messaging (off by default)
- `extraCollections` config allows searching other agents' transcripts
- `sessions_spawn` for background agent runs with optional context fork

**Missing:** No evaluator-optimizer loop pattern. No built-in quality gates between agents.

### Memory Architecture (Beyond Dreaming)

**Three-phase pipeline:**

```
Light Phase (noisy, recent)
  → Signal capture from conversation
  → Everything logged, nothing filtered

REM Phase (staged, reviewable)
  → LLM promotes candidates to "possible lasting truths"
  → Entries written to DREAMS.md (reversible)
  → Human or agent review before persistence

Deep Phase (durable)
  → Confirmed memories written to persistent storage
  → Queryable via semantic search
```

**REM Backfill:** Replays historical notes through the full pipeline without a second memory stack. Stages durable candidates into the short-term dreaming store. One command: `memory rem-backfill --path <dir>`.

**Storage:** Local Markdown files + SQLite vector databases. Self-hosted only.

**What's missing vs Agency OS needs:**
- No cloud-native storage (we use Supabase pgvector)
- No memory deduplication (mem0 does this, OpenClaw doesn't)
- No contradiction detection
- No entity extraction or linking
- Light/REM/Deep is temporal staging, not semantic categorization

### Hook System

| Hook Type | When It Fires | Use Case |
|-----------|--------------|----------|
| PreToolUse | Before any tool executes (synchronous) | Security validation, audit logging, context injection, blocking dangerous commands |
| PostToolUse | After tool result returns | Result transformation, logging, cleanup |
| tool_result_persist | Before result written to transcript | Custom result formatting/trimming |
| Internal lifecycle | `/new`, `/reset`, `/stop`, presence events | Session management automation |
| Webhooks | External HTTP triggers | Telegram relay, CI/CD triggers |

**Compared to Claude Code hooks:** Similar PreToolUse/PostToolUse model. OpenClaw adds tool_result_persist (transform before save) and webhook triggers. Claude Code now has MCP tool hooks (type: `mcp_tool`) which OpenClaw lacks.

### Cost Optimization

OpenClaw's documented cost drivers:
1. Context accumulation (session history grows unbounded)
2. Tool output storage (large outputs resent per message)
3. System prompt complexity (resent each turn)
4. Heartbeat background consumption
5. Poor model selection

**Tactics:** Session reset to control context size, model routing (cheap models for simple tasks), disable background generation (title/tags/follow-up), reduce tool/skill count in context.

**No token dashboard.** Manual config tuning only. Weaker than Agency OS's approach of tracking costs per directive via cis_directive_metrics.

### Session Management

- Gateway owns session state
- Session isolation via DM flag
- Sub-agents use UUID-based session keys
- **Gateway restart = session loss** for autonomous tasks
- No durable named sessions for sub-agents (feature requested, not shipped)
- No cross-platform session handoff (proposed, not shipped)

**Weaker than Agency OS model:** Our Supabase-backed memory + ceo_memory survives restarts. OpenClaw sessions are ephemeral by default.

---

## Security Assessment — CRITICAL

### Vulnerability Flood (March–April 2026)

| Period | CVEs | Worst CVSS | Details |
|--------|------|-----------|---------|
| March 18–21 | 9 CVEs in 4 days | 9.9 (critical) | Command injection, SSRF, path traversal, prompt injection RCE |
| March 29 | 1 CVE | 9.9 | Privilege escalation (340K+ GitHub stars exposed) |
| April 9–10 | 13 security fixes | 8.7 | Privilege escalation, arbitrary code execution |
| Jan–Feb | 341+ malicious skills | N/A | ClawHavoc supply chain attack — typosquatting, reverse shells, SSH key exfiltration |

**Scale:** Joel Gamblin's tracker shows 137 advisories between Feb 2 and Apr 4, 2026 — approximately **one advisory every 15 hours for two months**.

**Kaspersky assessment:** Some vulnerabilities are "fundamental to design, not patchable — only containable."

**40,214 internet-exposed instances** found by SecurityScorecard (Feb 2026). 35.4% confirmed vulnerable. 12,812 susceptible to RCE.

**Verdict: Not suitable for production deployment without significant hardening.** The pattern ideas are valuable; the runtime is a liability.

---

## Anthropic Relationship

| Event | Date | Impact |
|-------|------|--------|
| Anthropic staff confirm OpenClaw usage is "allowed" | Pre-April | Permissive |
| Anthropic imposes paywall | April 4 | Subscription users can no longer use Claude via OpenClaw without separate pay-as-you-go billing |
| Full refunds offered | April 4+ | Acknowledged surprise |
| Peter Steinberger joins OpenAI | Feb 14 | Creator no longer at Anthropic or OpenClaw |
| Non-profit foundation announced | Feb 14 | Governance structure unverified |

**Status:** Tolerated, not endorsed. Anthropic provides no SLA, support, or guarantees for OpenClaw usage.

---

## Enderfga/openclaw-claude-code Fork (More Relevant)

The **Enderfga/openclaw-claude-code** fork is a headless Claude Code wrapper, more directly relevant to Agency OS than upstream OpenClaw.

| Metric | Value |
|--------|-------|
| Stars | 400 |
| Forks | 61 |
| Open issues | 0 |
| Latest release | v2.13.0 (April 16, 2026) |
| License | MIT |
| Activity | Actively maintained |

**Recent releases (post-2026.3.8):**

| Version | Date | Features |
|---------|------|----------|
| v2.13.0 | Apr 16 | Hook event streaming, permission delegation, prompt cache optimization, GitHub PR sessions, MCP Channels, API retry tracking |
| v2.12.2 | Apr 16 | Latency fixes for large tool payloads |
| v2.12.1 | Apr 14 | Configurable Anthropic base URL (proxy support) |
| v2.12.0 | Apr 13 | Architecture cleanup, structured logging, new base classes |
| v2.11.0 | Apr 10 | Full OpenAI function calling via `/v1/chat/completions` |
| v2.10.0 | Apr 10 | Custom engine integration for any CLI |
| v2.9.4 | Apr 9 | System prompt injection, Cursor routing |

**Key capabilities:** Drives Claude Code/Cursor/Gemini/OpenAI headlessly, multi-engine via unified `ISession` interface, persistent Claude Code CLI sessions with Anthropic prompt caching, Council + Ultraplan for multi-agent coordination.

**Security posture:** Zero outstanding issues. Much smaller attack surface than upstream OpenClaw (no skill registry, no ClawHub, no multi-channel plugins).

---

## Adoption Recommendations

### ADOPT (extract pattern, implement in Agency OS)

| Pattern | Source | Implementation |
|---------|--------|---------------|
| **Dreaming (3-phase memory)** | v2026.4.9 | Build Light→REM→Deep pipeline for daily_log → core_fact promotion. LLM evaluates which daily_logs contain durable insights |
| **REM Backfill** | v2026.4.9 | One-time script to replay 90+ existing daily_logs through consolidation pipeline. Extract core_facts from accumulated noise |
| **Agent context forking** | v2026.4.23 | Pass relevant parent context to sub-agents automatically. Currently EVO sub-agents get manual brief only |
| **Orchestrator-Subagent pattern** | Multi-agent docs | Already implemented via EVO. Validate against OpenClaw's isolation model (separate workspace, auth, session per agent) |
| **PreToolUse security hooks** | Hook system | Add validation hooks before external API calls (cost gates, rate limit checks, input validation) |
| **cgroup memory hardening** | v2026.4.22 | Apply to Railway containers running agent workloads |

### DEFER (interesting but not immediate priority)

| Pattern | Reason to Defer |
|---------|----------------|
| Memory-Wiki | Would require migration from Supabase. Evaluate after listener v3 ships |
| Browser automation | Bright Data handles web data collection. Revisit if scraping needs change |
| Google Meet integration | Premature for current voice AI maturity |
| Plugin peer dependencies | Adds complexity to skill system. Evaluate if skill count exceeds 25 |
| tokenjuice cost analytics | We track costs via cis_directive_metrics. Evaluate if cost visibility gaps emerge |
| Realtime voice loops | Relevant when voice outreach matures |

### SKIP (not relevant to Agency OS)

| Pattern | Why Skip |
|---------|---------|
| xAI Grok / DeepSeek V4 / Moonshot | Claude-only stack |
| ElevenLabs Scribe | We use Vapi/Telnyx |
| OpenAI Codex integration | Irrelevant provider |
| OpenClaw runtime deployment | Security posture disqualifying (137 advisories in 2 months) |
| ClawHub skill registry | Supply chain attack history (341+ malicious skills) |

---

## Sources

- [GitHub openclaw/openclaw](https://github.com/openclaw/openclaw)
- [GitHub openclaw/openclaw/releases](https://github.com/openclaw/openclaw/releases)
- [OpenClaw docs — Multi-agent](https://docs.openclaw.ai/concepts/multi-agent)
- [OpenClaw docs — Dreaming](https://docs.openclaw.ai/concepts/dreaming)
- [OpenClaw docs — Hooks](https://docs.openclaw.ai/automation/hooks)
- [OpenClaw docs — Token Use](https://docs.openclaw.ai/reference/token-use)
- [OpenClaw docs — Sessions](https://docs.openclaw.ai/concepts/session)
- [OpenClaw docs — ClawHub](https://docs.openclaw.ai/tools/clawhub)
- [GitHub Enderfga/openclaw-claude-code](https://github.com/Enderfga/openclaw-claude-code)
- [OpenClaw CVE flood blog](https://openclawai.io/blog/openclaw-cve-flood-nine-vulnerabilities-four-days-march-2026)
- [Joel Gamblin CVE tracker](https://github.com/jgamblin/OpenClawCVEs)
- [SecurityScorecard exposure report](https://blink.new/blog/openclaw-2026-cve-complete-timeline-security-history)
- [Sangfor CVE analysis](https://www.sangfor.com/blog/cybersecurity/openclaw-ai-agent-security-risks-2026)
- [TechCrunch — Anthropic paywall](https://techcrunch.com/2026/04/04/anthropic-says-claude-code-subscribers-will-need-to-pay-extra-for-openclaw-usage/)
- [Hacker News — OpenClaw allowed](https://news.ycombinator.com/item?id=47844269)
- [Multi-agent orchestration guide](https://zenvanriel.com/ai-engineer-blog/openclaw-multi-agent-orchestration-guide/)
- [REM Backfill announcement](https://juliangoldie.com/openclaw-4-9-rem-backfill/)
