# P12 — Enderfga/openclaw-claude-code Fork Evaluation

**Date:** 2026-04-26
**Author:** SCOUT (research clone)
**Branch:** `scout/p12-enderfga-fork-eval`
**Mission:** Evaluate whether the [Enderfga/openclaw-claude-code](https://github.com/Enderfga/openclaw-claude-code) fork supplements our Claude Code setup with features we don't have. Earlier OpenClaw deep dive flagged this fork as more relevant to Agency OS than upstream OpenClaw.
**Verdict (TL;DR):** **Do not adopt the fork as a runtime. Cherry-pick four ideas; ignore the rest.** Most of v2.13.0's marquee features are pass-throughs of native Claude Code 2.1.111 flags — and we already run Claude Code **2.1.119** (newer). The fork's *unique* contributions (Council, Ultraplan, Ultrareview, ISession multi-engine) are interesting patterns to mirror but not worth the runtime swap.

---

## 1. Fork Capability Catalog

### 1.1 Project metadata ([repo](https://github.com/Enderfga/openclaw-claude-code))

| Field | Value |
|---|---|
| Latest version | **v2.13.0** (2026-04-16) |
| License | MIT |
| Language | TypeScript (96.8%) |
| Stars / Forks | 400 / 61 |
| Open issues | 0 |
| Required runtimes | Node.js ≥ 22, Claude Code CLI ≥ 2.1, optional OpenClaw ≥ 2026.3.0 / Codex / Gemini / Cursor |
| Tagline | "OpenClaw plugin — turn Claude Code CLI into a programmable, headless coding engine with plenty of tools, agent teams, and multi-model proxy" |

### 1.2 v2.13.0 — "Claude Code CLI 2.1.111 feature sync" ([release notes](https://github.com/Enderfga/openclaw-claude-code/releases))

| Feature | What it adds |
|---|---|
| `--include-hook-events` | Streams PreToolUse / PostToolUse lifecycle events |
| `--permission-prompt-tool <tool>` | Delegate permission prompts to an MCP tool (non-interactive) |
| `--exclude-dynamic-system-prompt-sections` | Move cwd/env/git context to user message → better prompt cache hits (auto-enabled with `--bare`) |
| 1-hour prompt cache auto-enabled when `bare: true` | `ENABLE_PROMPT_CACHING_1H=1` |
| `--from-pr <n|url>` | Resume a session bound to a GitHub PR |
| MCP Channels (research preview) | `--channels <spec>` for CI-pushed event injection |
| API retry tracking | `retries`, `lastRetryError` in session stats |
| Smart defaults | Auto-enable cache optimisations |
| Test count | 438 passing |

**Critical observation:** every flag in this list is a **Claude Code 2.1.111 native flag**. The fork wraps them through its `ISession` interface so non-Claude engines also see them. We already run **Claude Code 2.1.119** (a week newer than 2.1.111) — these flags are available to us *without* the fork.

### 1.3 Earlier releases (April 2026 cadence)

| Version | Date | Theme |
|---|---|---|
| v2.13.0 | 2026-04-16 | Claude Code 2.1.111 sync |
| v2.12.2 | 2026-04-16 | OpenAI-compat latency fixes |
| v2.12.1 | 2026-04-14 | Configurable Anthropic base URL (proxy / MiniMax) |
| v2.12.0 | 2026-04-13 | `BaseOneShotSession` refactor; `OPENCLAW_LOG_LEVEL`; circuit breaker |
| v2.11.1 | 2026-04-11 | Function-calling robustness |
| v2.11.0 | 2026-04-10 | OpenAI tool-use protocol via `/v1/chat/completions` |
| v2.10.0 | 2026-04-10 | `engine: 'custom'` for any CLI |
| v2.9.4 | 2026-04-09 | System-prompt injection for non-Claude engines |

### 1.4 Council — multi-agent orchestration ([council.md](https://github.com/Enderfga/openclaw-claude-code/blob/main/skills/references/council.md))

- Default trio: **Planner / Generator / Evaluator**, each in an isolated git worktree (`.worktrees/Architect/`, `.worktrees/Engineer/`, …).
- Two-phase protocol: Plan First (in isolation) → execute with `[CONSENSUS: YES]` / `[CONSENSUS: NO]` voting per round.
- Continues until unanimous, max-rounds, or explicit abort.
- Transcripts at `~/.openclaw/council-logs/council-<timestamp>.md`; results queryable for 30 min post-completion.
- Mixed engines per agent (Claude / Codex / Gemini / Cursor).
- Tool surface: `council_start`, `council_status`, `council_review`, `council_accept`, `council_reject` (5 of the 27 tools).

### 1.5 Ultraplan ([ultra.md](https://github.com/Enderfga/openclaw-claude-code/blob/main/skills/references/ultra.md))

- Dedicated **Opus plan-mode** session, up to **30 min** (default `1_800_000` ms timeout).
- `manager.ultraplanStart('task', { cwd, model, timeout })` → polled via `ultraplan_status(id)`.
- Plans persist 30 min post-completion.

### 1.6 Ultrareview

- Builds on Council; spawns **5–20 reviewer agents in parallel**, each in its own worktree.
- Council runs **2 rounds** (discovery + cross-review).
- 20 review angles: security, logic, performance, APIs, testing, typing, concurrency, errors, dependencies, readability, validation, config, scalability, docs, a11y, i18n, networking, auth, crypto, memory.
- Per-agent timeout 5–25 min (default 10).

### 1.7 ISession multi-engine

`ISession` is the unified interface that drives Claude Code, OpenAI Codex, Google Gemini, Cursor Agent, or any custom CLI through a SessionManager. v2.10.0 added `engine: 'custom'`. Persistent or one-shot sessions, per-engine model selection, system-prompt injection for non-Claude engines.

---

## 2. Comparison vs Our Current Setup

| Dimension | Agency OS (today) | Fork v2.13.0 |
|---|---|---|
| Claude Code version | **2.1.119** | wraps 2.1.111 (1 wk behind upstream) |
| Worktree-per-agent | ✅ 5 worktrees (`Agency_OS`, `-aiden`, `-atlas`, `-orion`, `-scout`) | ✅ Council scaffolds `.worktrees/<role>/` per run |
| Multi-bot peer review | ✅ DSAE-DELAY + dual-concur authority + clone queue board | ✅ Council with `[CONSENSUS: YES/NO]` voting |
| Sub-agent definitions | ✅ 32 agents in `.claude/agents/` | ⚠️ 3-role default; configurable |
| MCP servers wired | ✅ 13+ (Supabase, Redis, Prefect, Railway, Prospeo, DataForSEO, Vercel, Salesforge, Vapi, Telnyx, Unipile, Resend, Memory) | ⚠️ Inherits from Claude Code; no curated list |
| Permission mode | `bypassPermissions` (we don't prompt) | `--permission-prompt-tool` MCP delegation |
| Hooks | ❌ none in `settings.json` | ✅ PreToolUse / PostToolUse streaming |
| Prompt cache 1h | ❌ not enabled | ✅ auto with `--bare` |
| GitHub PR sessions | ❌ manual `gh pr` + paste | ✅ `--from-pr <n|url>` |
| Multi-provider failover | ❌ Claude-only | ✅ ISession routes Claude/Codex/Gemini/Cursor |
| Parallel deep review | ❌ single review-5 + 2 human bots | ✅ Ultrareview 5-20 agents × 20 angles |
| Long planning sessions | ⚠️ Plan tool (~minutes) | ✅ Ultraplan up to 30 min |
| Council runtime dependency | n/a | Node ≥ 22 + fork install |

**Headline:** the fork's worktree + consensus protocol mirrors what we already do organically through DSAE. Where it surpasses us is **parallel deep review** (Ultrareview), **provider failover** (ISession), **30-min plan mode** (Ultraplan), and **hook event streaming** for runtime gates.

---

## 3. Per-Feature Adopt / Defer / Skip

| # | Feature | Verdict | Reasoning |
|---|---|---|---|
| 1 | Hook event streaming (`--include-hook-events`) | **ADOPT NATIVELY** | Available in our Claude Code 2.1.119 directly. Write `PreToolUse`/`PostToolUse` hooks in `settings.json` for GOV-12 Gates-as-Code (Step-0 RESTATE check, callsign verification, four-store completion gate). No fork dependency. |
| 2 | Permission delegation (`--permission-prompt-tool`) | **SKIP** | We run `defaultMode: bypassPermissions`. Irrelevant. |
| 3 | `--exclude-dynamic-system-prompt-sections` + 1-hour cache | **ADOPT NATIVELY** | Set `ENABLE_PROMPT_CACHING_1H=1` and enable the flag. Token savings on long EVO loops likely 20–40%. |
| 4 | `--from-pr <n|url>` | **ADOPT NATIVELY** | Useful for review-5 agent and PR-bound work; reduces context paste. Native flag. |
| 5 | MCP Channels (research preview) | **DEFER** | Telegram relay + outbox covers CI-pushed events today. Revisit when Anthropic GA's Channels and we have a CI surface that benefits. |
| 6 | API retry tracking (`retries`, `lastRetryError`) | **DEFER** | Operationally useful but not load-bearing. Surface natively if Claude Code exposes; otherwise pass. |
| 7 | ISession multi-engine (Claude/Codex/Gemini/Cursor/Custom) | **DEFER** | Real capability gap — we have zero provider failover. But our cost is dominated by enrichment APIs, not LLM tokens, and our orchestration already routes work to specialised Claude agents. Revisit only after a >2-hour Anthropic outage stalls a directive. |
| 8 | Council (Planner/Generator/Evaluator + worktree + consensus voting) | **MIRROR PATTERN, DO NOT ADOPT RUNTIME** | The worktree-per-role pattern is already ours (5 worktrees). Borrow the `[CONSENSUS: YES/NO]` voting marker as a DSAE-protocol discipline (Aiden + Elliot post explicit consensus token at end of agreement). No fork install needed. |
| 9 | Ultraplan (Opus 30-min plan mode) | **DEFER** | We use Plan tool + general-purpose agent for this. 30-min sessions are rare in our workflow; when they happen, the existing plan flow is sufficient. |
| 10 | Ultrareview (5-20 parallel reviewers × 20 angles) | **CONSIDER FOR MAJOR RELEASES** | Most concrete win. 20-angle parallel review on `release/*` PRs would catch more than dual-concur. **Cost:** 20 concurrent Claude sessions burns subscription usage fast. Pilot only on quarterly major releases, not every PR. |
| 11 | Custom engine (`engine: 'custom'`) | **DEFER** | We don't have a non-Claude CLI to wire in today. |
| 12 | OpenAI-compatible `/v1/chat/completions` | **SKIP** | We don't expose Claude as a service for external clients. |
| 13 | Configurable Anthropic base URL (proxy / MiniMax) | **DEFER** | Same theme as #7; not load-bearing. |
| 14 | Structured logging (`OPENCLAW_LOG_LEVEL`) | **SKIP** | Telegram relay + LAW XIV raw-output mandate cover. |

**Summary:** 4 ADOPT (all native, no fork dependency), 1 MIRROR PATTERN, 6 DEFER, 3 SKIP. **Zero items require installing the fork.**

---

## 4. Recommendation — Decline Fork as Runtime; Absorb Four Ideas

### 4.1 Decision

**Do not adopt the Enderfga fork as a runtime.** Three reasons:

1. **The marquee v2.13.0 features are native Claude Code flags.** We already run a newer Claude Code (2.1.119 vs the fork's 2.1.111 sync target). Wrapping a stable upstream in a third-party plugin to get flags we already have is pure cost.
2. **The fork's *unique* features (Council, Ultraplan, Ultrareview, ISession) are not load-bearing for us today.** We have multi-bot peer review through DSAE and 5 worktrees. We have Plan tool. We don't have provider failover need yet. Our cost per directive is dominated by enrichment, not LLM tokens.
3. **Bus-factor regression.** Single maintainer (Enderfga), 400 stars, 0 open issues — could mean polished or could mean low-traffic. Either way, gating our orchestration on a third-party fork lagging upstream by ~1 week is a worse position than depending on Anthropic directly.

### 4.2 What to absorb (no fork install required)

- **Hooks for Gates-as-Code (GOV-12).** Write `PreToolUse`/`PostToolUse` hooks in `~/.claude/settings.json` to enforce Step-0 RESTATE, callsign discipline, four-store completion at runtime — not in prompt. Native Claude Code 2.1.119 feature.
- **Prompt cache 1h + `--exclude-dynamic-system-prompt-sections`.** Free token savings on long sessions. Set in env.
- **`--from-pr` for review-5.** Cleaner PR-bound review sessions.
- **`[CONSENSUS: YES]` / `[CONSENSUS: NO]` markers.** Adopt as an explicit DSAE-protocol token (today we use `[AGREE:<callsign>]` / `[DIFFER:<callsign>]` — equivalent semantics; consider whether the Council wording is clearer).

### 4.3 What to revisit later

- **Ultrareview** as an opt-in tool for `release/*` PR gates only. Pilot 1× on a major release; measure findings vs cost.
- **ISession multi-engine** when (and only when) Anthropic has a >2-hour outage that stalls a directive. Provider failover then becomes worth ~10 engineer-days of integration.

### 4.4 Suggested follow-up directives

- **P12-A** — Native Claude Code optimisation pass: enable `ENABLE_PROMPT_CACHING_1H=1`, write `PreToolUse`/`PostToolUse` hooks for Step-0 RESTATE + callsign + four-store enforcement. Estimate: 1 day.
- **P12-B** — Pilot Ultrareview on next major release branch (when one exists). Compare 20-angle parallel review against current dual-concur. Estimate: 2 days investigation + measured run.
- **P12-C** — Defer fork adoption indefinitely; revisit only if a multi-provider failover need materialises.

---

## Sources

- [Enderfga/openclaw-claude-code (repo)](https://github.com/Enderfga/openclaw-claude-code)
- [Releases page (v2.9.x → v2.13.0)](https://github.com/Enderfga/openclaw-claude-code/releases)
- [Council reference](https://github.com/Enderfga/openclaw-claude-code/blob/main/skills/references/council.md)
- [Ultraplan / Ultrareview reference](https://github.com/Enderfga/openclaw-claude-code/blob/main/skills/references/ultra.md)
- [CLI flag reference](https://github.com/Enderfga/openclaw-claude-code/blob/main/skills/references/cli.md)
- Local: `/home/elliotbot/.claude/settings.json` (13+ MCP servers, `bypassPermissions`, no hooks)
- Local: `claude --version` → 2.1.119
- Local: `/home/elliotbot/clawd/.claude/agents/` (32 sub-agent definitions)
