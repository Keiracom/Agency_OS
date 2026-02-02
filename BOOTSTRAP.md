# BOOTSTRAP.md — Next Session Priorities

**Created:** 2026-02-02 03:27 UTC
**Context:** Power-level upgrades identified, queued for implementation

---

## 🎯 PRIORITY UPGRADES (Execute in Order)

### 1. LiteLLM Cost Routing (2h)
- Route simple tasks → Haiku ($0.25/1M)
- Route complex tasks → Opus ($15/1M)
- Expected: 60% cost reduction
- Repo: github.com/BerriAI/litellm (34k⭐)

### 2. Self-Verification Loop (2h)
- Add `verify()` decorator to critical operations
- Review own output before returning to user
- Expected: 50% error reduction

### 3. Proactive Intel Sweep (3h)
- Schedule morning scan: HN, Reddit, ArXiv
- Auto-surface relevant developments
- Use existing action_engine + CTO filter

### 4. Multi-Agent Orchestration (8h)
- LangGraph supervisor pattern
- Spawn specialized agents in parallel
- Roles: Researcher, Scraper, Builder
- Expected: 3x throughput on complex tasks

---

## ✅ ALREADY DONE (Don't Re-implement)

- **Vector Memory** — `elliot_internal.memories` (1,376 items, pgvector)
- **MCP Integration** — Clawdbot skills system (50+ skills loaded)
- **Stealth Browser** — `tools/autonomous_browser.py` (215k proxies)
- **CTO Filter** — `infrastructure/action_engine.py` (LLM-powered)
- **Behavior Cache** — `tools/behavior_cache.py` (basic version)

---

## 📝 LESSONS LEARNED (This Session)

1. **Scraping Hierarchy:** JSON/API > RSS > old.* > Full browser
   - Reddit .json = 2s success
   - Reddit Playwright = 30s timeout

2. **Don't recommend buying what we own**
   - Skills system = MCP equivalent
   - Memory system already has vectors

---

**DELETE THIS FILE AFTER READING AND EXECUTING**
