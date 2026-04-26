# Engineering Workforce Updates — April 7–26, 2026

**Date:** 2026-04-26
**Callsign:** scout
**Scope:** Anthropic product line + Claude Code + OpenClaw releases relevant to AI engineering bots
**Status:** tentative — awaiting peer review

---

## The Big Three

Three releases from this window materially change how Agency OS should build and run its AI workforce.

### 1. Claude Managed Agents (April 8 — Public Beta)

Anthropic launched a fully managed harness for long-running autonomous agent workflows. This is the official replacement for roll-your-own agent loops. Session state is separated from execution — durable state, tool isolation, and error recovery are handled by the platform. Pricing: $0.08/session-hour plus standard token rates. Early production users include Notion, Rakuten, and Asana. Access via API header `managed-agents-2026-04-01` (SDK auto-applies).

**What this means for Agency OS:** Managed Agents offer what Elliottbot currently builds manually — stable session model, sub-agent isolation, meta-harness architecture. The $0.08/hr overhead is cheap compared to the engineering cost of maintaining custom session management. Immediate evaluation needed: can Elliottbot's EVO protocol (Decompose → Execute → Verify → Report) run inside a Managed Agent session instead of raw Claude Code sub-agents?

**Source:** https://platform.claude.com/docs/en/managed-agents/overview

### 2. Claude Opus 4.7 (April 16 — GA)

The new top-tier model. SWE-bench Verified jumped from 80.8% to 87.6%. CursorBench went from 58% to 70%. First Claude model with high-resolution vision (2,576px / 3.75MP, up from 1,568px / 1.15MP). Pricing unchanged from 4.6: $7.75 AUD/M input, $38.75 AUD/M output.

**Regression flagged:** BrowseComp (web search capability) dropped from 83.7% to 79.3%. Web search tasks are measurably worse on 4.7 vs 4.6.

**What this means for Agency OS:** Opus 4.7 should be the default for architect-0 and any vision-dependent work. Research agents (research-1) that rely on web search should stay on 4.6 or Haiku until the BrowseComp regression is addressed. The +7% SWE-bench gain is real — build agents will produce better code.

**Source:** https://www.anthropic.com/news/claude-opus-4-7

### 3. Prompt Caching TTL Fix (April 20 — Bug Fix)

On March 6, Anthropic silently changed the default prompt cache TTL from 1 hour to 5 minutes. The cleanup logic was also broken — old thinking was cleared every turn instead of once per session, causing memory loss and cache misses. This inflated costs 30–60% for workloads with >5-minute pauses between turns. Fixed in Claude Code v2.1.116 (April 20). Current state: 5-minute TTL is the default; 1-hour TTL available at higher cost.

**What this means for Agency OS:** This explains any cost spikes observed since early March. Elliottbot's ScheduleWakeup delays should respect the 5-minute cache window (delays under 270s keep cache warm; delays over 300s pay the full cache-miss penalty). The fix in v2.1.116 resolves the memory-loss bug but doesn't restore the 1-hour default.

**Source:** https://github.com/anthropics/claude-code/issues/46829

---

## Claude Code Harness Updates (v2.1.69–v2.1.117)

Over 30 releases shipped in this window. The ones that matter for engineering bots:

### Session Recap (`/recap`)

New command (April 14) that reads full session history and produces a context summary. Auto-fires when returning after an idle threshold. Eliminates the cold-start problem for long-paused sessions. Configurable via `CLAUDE_CODE_ENABLE_AWAY_SUMMARY`.

**Application:** Elliottbot's session startup protocol currently queries Supabase memories + ceo_memory. `/recap` could supplement this with in-session context recovery, reducing reliance on external memory for within-session continuity.

### Skill Tool Access

Built-in slash commands (`/init`, `/review`, `/security-review`) are now discoverable and invocable as tools by the model. Sub-agents can programmatically invoke skills rather than requiring manual `/command` triggers. Controllable via `disable-model-invocation: true`.

**Application:** Scout, Elliot, and Aiden sub-agents can now call skills like `/review` or `/security-review` programmatically during EVO Step 4 (Verify). No more manual invocation.

### MCP Tool Hooks (type: `mcp_tool`)

Hooks can now invoke MCP tools directly. Integrates with PreToolUse, PostToolUse, SessionStart, SessionEnd, and UserPromptSubmit events. This is the native integration point for MCP servers in the hooks system.

**Application:** Agency OS's 11 MCP servers (Prefect, Railway, Supabase, etc.) can now be triggered automatically via hooks — e.g., a PostToolUse hook that logs every Supabase write to the memory store, or a SessionEnd hook that triggers the three-store save.

### Ultraplan (Early Preview)

Cloud-based planning with local or remote execution. Draft plans in-browser with inline comments and emoji reactions. Requires v2.1.101+, GitHub repo, Pro/Max subscription. Cloud container runtime (up to 30 minutes).

**Application:** Potential replacement for EVO Step 1 (Decompose) + Step 2 (Present). Dave could review decomposition plans in-browser with inline comments before approving execution. Currently early preview — monitor for GA.

### Enterprise CA Trust (April 10)

OS CA certificate store trusted by default. Enterprise TLS proxies (CrowdStrike, Zscaler) work without extra configuration. Configurable via `CLAUDE_CODE_CERT_STORE`.

**Application:** If Agency OS ever runs behind a corporate proxy, this removes a class of connectivity bugs.

### Quality Bug Fixes (April 20 Postmortem)

Three bugs confirmed by Anthropic that degraded Claude Code quality over two months:
1. Default reasoning effort dropped to medium on Opus 4.6 (reverted April 7)
2. Caching bug (March 26–April 20): old thinking cleared every turn, causing context loss
3. System prompt edit (April 16): 25-word/100-word limits on inter-tool text caused 3% coding quality drop

**Impact:** If Elliottbot experienced degraded output quality between March 6 and April 20, these three bugs are the likely cause. All fixed in v2.1.116+.

---

## Claude Routines + OpenClaw

### Routines (April 14)

Repeatable Claude Code jobs, scheduled or triggered externally. Supports API triggers, GitHub event triggers, and cron schedules. Runs from Anthropic's managed web environment.

**Application:** Direct replacement for Elliottbot's cron-based directive loops and callback-poller. Routines with webhook triggers could replace the current Prefect + cron architecture for scheduled agent tasks.

### OpenClaw Memory Consolidation ("Dreaming")

OpenClaw (third-party headless Claude Code extension) shipped a "REM Backfill" feature — replaying historical notes for memory consolidation during idle periods. This is analogous to human memory consolidation during sleep.

**Application:** Inspiration for session-end memory compaction. Currently Elliottbot writes a daily_log on session end. A Dreaming-style approach would re-read and consolidate the last N daily_logs into higher-level core_facts, reducing memory noise over time. Directly addresses the listener quality problem (noisy corpus of daily_logs drowning out core facts).

**Note:** OpenClaw is community-maintained, not Anthropic-supported. The pattern is valuable; the tool itself lacks enterprise SLA.

---

## Other Releases

### Claude Design (April 17)

Anthropic Labs visual design tool at claude.ai/design. Powered by Opus 4.7 vision. Creates designs, prototypes, slide decks with conversational refinement. Exports to PDF/PPTX/HTML/Canva. Has structured handoff to Claude Code for design-to-implementation workflow.

**Application:** Low immediate relevance for engineering bots. Relevant if Dave wants to design the Phase 2.1 dashboard visually before building. No API — web-only SaaS.

### Claude Mythos Preview (April 7 — Gated)

Codename Capybara. SWE-bench 93.9%, USAMO 97.6%. Gated for defensive cybersecurity research only (Project Glasswing, 40+ partner orgs). Not available on public Claude or APIs.

**Application:** Not accessible. Flag for future — if Mythos opens broadly, it would be a step-change for complex coding tasks.

### Batch API — 300K Output Tokens (April 2026)

Message Batches API now supports 300K max output tokens (header: `output-300k-2026-03-24`). 50% cost reduction vs. synchronous API. Most batches complete within 1 hour.

**Application:** Cost optimization for high-volume enrichment work. Batch API at 50% off is better than sync for any bulk processing (e.g., batch CIS scoring, batch email generation). 300K output enables long-form synthesis without chunking.

### Rate Limits API (April 2026)

Programmatic query of rate limits per API key, workspace, and organization. Monitors RPM, TPM, TPD. Charts on Usage page show headroom and cache hit rates.

**Application:** Elliottbot should query rate limits before spawning batch sub-agent work. Prevents quota spillover and surprise 429 errors.

### MCP Governance (April 8)

New core maintainers announced. Horizontal scaling roadmap published (stateless servers, `.well-known` discovery). Security design flaw reported (200K servers potentially affected) but requires explicit user permission — acknowledged by Anthropic/Google/Microsoft as known limitation, not CVE.

**Application:** Low immediate impact. Horizontal scaling roadmap is relevant for future MCP bridge load. Security flag is non-blocking for standard usage.

---

## Recommended Actions for Agency OS

| Priority | Action | Rationale |
|----------|--------|-----------|
| P0 | Upgrade to Claude Code v2.1.116+ | Fixes caching bug, reasoning effort, quality regression |
| P0 | Set architect-0 model to `claude-opus-4-7` | +7% SWE-bench, vision capability |
| P0 | Keep research-1 on Haiku (or 4.6 for web search) | Opus 4.7 BrowseComp regressed |
| P1 | Evaluate Managed Agents for EVO protocol | Could replace custom sub-agent harness |
| P1 | Implement MCP tool hooks for session-end | Auto-trigger three-store save via PostToolUse hook |
| P1 | Query Rate Limits API before batch spawns | Prevent quota spillover |
| P2 | Evaluate Routines for cron replacement | Could replace Prefect-based scheduled flows |
| P2 | Prototype Dreaming pattern for memory consolidation | Consolidate daily_logs → core_facts during idle |
| P2 | Use Batch API for bulk enrichment | 50% cost reduction on high-volume work |
| P3 | Monitor Ultraplan for EVO Step 1-2 replacement | Cloud planning with inline review |
| P3 | Track Mythos availability | Step-change if it opens broadly |

---

## Sources

- [Anthropic — Claude Opus 4.7](https://www.anthropic.com/news/claude-opus-4-7)
- [GitHub Blog — Opus 4.7 GA](https://github.blog/changelog/2026-04-16-claude-opus-4-7-is-generally-available)
- [Claude API — Managed Agents](https://platform.claude.com/docs/en/managed-agents/overview)
- [SiliconANGLE — Managed Agents Launch](https://siliconangle.com/2026/04/08/anthropic-launches-claude-managed-agents-speed-ai-agent-development)
- [Claude Code — What's New](https://code.claude.com/docs/en/whats-new)
- [Releasebot — Claude Code Releases](https://releasebot.io/updates/anthropic/claude-code)
- [GitHub #46829 — Cache TTL Regression](https://github.com/anthropics/claude-code/issues/46829)
- [DEV Community — Prompt Caching TTL](https://dev.to/whoffagents/claude-prompt-caching-in-2026-the-5-minute-ttl-change-that-costs-you-money-4363)
- [Anthropic — Claude Design](https://www.anthropic.com/news/claude-design-anthropic-labs)
- [red.anthropic.com — Mythos Preview](https://red.anthropic.com/2026/mythos-preview/)
- [MCP Blog — Maintainer Update](https://blog.modelcontextprotocol.io/posts/2026-04-08-maintainer-update)
- [9to5Mac — Claude Cowork Enterprise](https://9to5mac.com/2026/04/09/anthropic-scales-up-with-enterprise-features-for-claude-cowork-and-managed-agents)
- [Releasebot — OpenClaw](https://releasebot.io/updates/openclaw)
- [Claude API — Batch Processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing)
- [Claude API — Rate Limits](https://platform.claude.com/docs/en/api/rate-limits)
- [VentureBeat — Quality Postmortem](https://venturebeat.com/technology/mystery-solved-anthropic-reveals-changes-to-claudes-harnesses-and-operating-instructions-likely-caused-degradation)
