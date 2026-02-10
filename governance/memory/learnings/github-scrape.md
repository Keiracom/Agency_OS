# GitHub Trending Scrape - AI Agent Tools
*Scraped: 2026-01-29*

## Summary
Found 10 high-value tools/libraries that could enhance AI agent capabilities. Focus: CLI tools, MCP servers, and immediately-usable libraries.

---

## Top Picks for Immediate Use

### 1. **mohsen1/yek** ⭐2,403
**What:** Fast Rust-based tool to serialize text files in a repo for LLM consumption.  
**Why useful:** Instantly prepare any codebase or directory for context injection. Much faster than manual file concatenation.  
**Install:** `cargo install yek` or download binary  
**Use case:** Before asking questions about a codebase, run `yek .` to get clean serialized output.

---

### 2. **upstash/context7** ⭐44,092
**What:** MCP Server providing up-to-date code documentation for LLMs.  
**Why useful:** Get accurate, current library docs instead of hallucinated or outdated info. Queries package registries directly.  
**Install:** Add to MCP config: `npx -y @upstash/context7-mcp`  
**Use case:** When coding with unfamiliar libraries, Context7 provides real-time accurate documentation.

---

### 3. **microsoft/playwright-mcp** ⭐26,412
**What:** Official Playwright MCP server for browser automation.  
**Why useful:** Web scraping, form filling, and browser automation via natural language. Microsoft-maintained quality.  
**Install:** `npx @playwright/mcp@latest`  
**Use case:** Automate web research, data extraction, and testing tasks.

---

### 4. **github/github-mcp-server** ⭐26,463
**What:** GitHub's official MCP Server.  
**Why useful:** Direct GitHub API access - create issues, PRs, search code, manage repos via agent commands.  
**Install:** Via MCP config with GitHub PAT  
**Use case:** Automated PR reviews, issue triage, code search across orgs.

---

### 5. **oraios/serena** ⭐19,455
**What:** Coding agent toolkit with semantic retrieval and editing capabilities.  
**Why useful:** Provides semantic code search and precise editing without full file reads. Integrates as MCP server.  
**Install:** `pip install serena-mcp` or via Docker  
**Use case:** Navigate large codebases semantically - find related functions, classes, usages.

---

### 6. **tadata-org/fastapi_mcp** ⭐11,462
**What:** Expose FastAPI endpoints as MCP tools automatically.  
**Why useful:** Turn any existing FastAPI service into MCP tools with minimal code. Includes auth support.  
**Install:** `pip install fastapi-mcp`  
**Use case:** Make internal APIs accessible to agents without writing custom MCP code.

---

### 7. **apify/apify-mcp-server** ⭐735
**What:** MCP server connecting to Apify's scraping/automation ecosystem.  
**Why useful:** Access thousands of ready-made scrapers for social media, search engines, e-commerce.  
**Install:** `npx @apify/mcp-server-apify`  
**Use case:** Extract data from LinkedIn, Twitter, Google, Amazon without building custom scrapers.

---

### 8. **hangwin/mcp-chrome** ⭐10,165
**What:** Chrome extension MCP server for browser control.  
**Why useful:** Direct Chrome tab access - read page content, click elements, semantic search within pages.  
**Install:** Chrome extension + local MCP server  
**Use case:** Interact with authenticated pages, complex SPAs that require real browser.

---

### 9. **badlogic/lemmy** ⭐1,427
**What:** Lightweight wrapper around tool-using LLMs for agentic workflows.  
**Why useful:** Minimal abstraction layer for building quick agentic pipelines. No heavy framework overhead.  
**Install:** Check repo for installation  
**Use case:** Quick agentic scripts without full framework complexity.

---

### 10. **thedotmack/claude-mem** ⭐15,364
**What:** Claude Code plugin for session memory capture and injection.  
**Why useful:** Automatically compresses session context and injects relevant history into future sessions.  
**Install:** Claude Code plugin installation  
**Use case:** Maintain long-term memory across coding sessions without manual MEMORY.md updates.

---

## Honorable Mentions

| Repo | Stars | Quick Note |
|------|-------|------------|
| BeehiveInnovations/pal-mcp-server | 10.9k | Multi-model support (Gemini/OpenAI/etc) for Claude Code |
| wshobson/agents | 27.2k | Multi-agent orchestration patterns for Claude Code |
| charmbracelet/crush | 19.1k | Beautiful agentic coding CLI (Charm team) |
| mcp-use/mcp-use | 9k | Simplest way to interact with MCP servers |
| idosal/git-mcp | 7.5k | MCP server for any GitHub project - prevents code hallucinations |
| VectifyAI/PageIndex | 10.6k | Vectorless reasoning-based RAG for documents |
| anthropics/skills | - | Official Anthropic agent skills repo |

---

## Not Recommended (But Popular)

- **Fosowl/agenticSeek** (24k⭐) - Requires significant compute, local Manus-style
- **bytedance/UI-TARS-desktop** (25k⭐) - Requires GPU for multimodal agent
- **0x4m4/hexstrike-ai** (6.4k⭐) - Security tools, needs careful ethical consideration

---

## Quick Install Commands

```bash
# Yek - file serializer
cargo install yek

# Context7 MCP
npx -y @upstash/context7-mcp

# Playwright MCP  
npx @playwright/mcp@latest

# Serena (semantic code toolkit)
pip install serena-mcp

# FastAPI to MCP
pip install fastapi-mcp
```

---

## Next Actions
1. Try `yek` for codebase context preparation
2. Add Context7 to MCP config for better library docs
3. Evaluate Serena for semantic code navigation
4. Consider Playwright MCP for browser automation needs
