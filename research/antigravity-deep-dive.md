# Google Antigravity — Comprehensive Deep Dive

**Research Date:** February 2026  
**Priority:** HIGH — Requested by Dave  

---

## Executive Summary: The Subscription Question

### 🎯 CRITICAL ANSWER: YES — Dave's Gemini Max/AI Pro subscription DOES provide enhanced Antigravity access

**The short answer:** If Dave has a Google One AI Pro subscription (which includes "Gemini Max"/Advanced), he gets:
- **Higher rate limits** in Antigravity (refreshing every 5 hours vs weekly for free users)
- **Priority access** to the platform
- **Access to Gemini 3 Pro** + Claude Sonnet 4.5 + GPT-OSS models
- **No additional API billing required** for standard usage

**Important Caveat:** There are documented bugs where Antigravity doesn't always recognize the subscription status. Multiple users report being stuck on "Free Plan" despite active AI Pro subscriptions. This is a known issue Google is working on.

### Cost Analysis (AUD)

| Scenario | Cost to Dave |
|----------|-------------|
| Already has Google AI Pro ($20 USD/~$31 AUD/month) | **$0 additional** — Antigravity included |
| Free tier only | $0 but weekly limits, less priority |
| Separate API billing (if he needed it) | $3.10/M input, $18.60/M output tokens AUD |

**Bottom Line:** Dave should NOT need separate API billing. His existing Gemini subscription covers Antigravity use with enhanced limits.

---

## 1. What IS Google Antigravity?

### Official Product Overview

Google Antigravity is an **agentic development platform** (not just an IDE) announced November 18, 2025, alongside Gemini 3. It's a VS Code fork that radically prioritizes AI agent management over traditional text editing.

### Key Facts

| Attribute | Details |
|-----------|---------|
| **Type** | Desktop IDE (VS Code fork) + Agent Manager |
| **Release Status** | Public Preview (free for individuals) |
| **Platforms** | macOS, Windows, Linux |
| **Official URL** | https://antigravity.google |
| **Download** | https://antigravity.google/download |
| **Origin** | Built by former Windsurf team (Google acquired Cognition/Windsurf for $2.4B) |

### Two Primary Interfaces

1. **Editor View** — Traditional AI-powered IDE with tab completions, inline commands
2. **Agent Manager (Mission Control)** — Dashboard to spawn, orchestrate, and observe multiple autonomous agents working in parallel

### What Makes It Different

Unlike Cursor/Copilot which are "chatbots in a sidebar," Antigravity:
- Treats agents as **autonomous actors** that can navigate editor, terminal, AND browser
- Supports **parallel agent execution** — dispatch 5 agents to 5 bugs simultaneously
- Uses **Artifacts** (task plans, screenshots, browser recordings) for verification instead of raw logs
- Has built-in **browser subagent** with full Chrome integration for testing/validation

---

## 2. Antigravity + Gemini Integration

### How Authentication Works

1. Sign in with **personal Gmail account** during setup
2. Antigravity checks your Google One/AI subscription status
3. Rate limits are determined by your subscription tier

### Subscription Tiers & Limits

| Tier | Rate Limits | Refresh Rate | Access |
|------|-------------|--------------|--------|
| **Free** | Large weekly quota | Weekly | Gemini 3 Pro, Claude Sonnet 4.5, GPT-OSS |
| **AI Pro** (~$20 USD/month) | Higher limits | Every 5 hours | Same models + priority access |
| **AI Ultra** (~$30 USD/month) | Highest limits | Every 5 hours | Same + experimental models |

**Source:** [Google Blog - Dec 5, 2025](https://blog.google/feed/new-antigravity-rate-limits-pro-ultra-subsribers/)

### Available Models Inside Antigravity

- **Gemini 3 Pro** (default, Google's flagship)
- **Claude Sonnet 4.5** (Anthropic)
- **GPT-OSS** (OpenAI's open model)
- Planning/Fast mode selection for each agent

### NO Separate API Keys Required

Antigravity does NOT require:
- Google Cloud API keys
- Vertex AI billing setup
- Separate Anthropic/OpenAI accounts

Everything runs through your Google account authentication.

### Known Issues (Bug Alert!)

Multiple users report Antigravity showing "Free Plan" despite active AI Pro subscriptions:
- [Forum thread](https://discuss.ai.google.dev/t/antigravity-not-recognizing-google-ai-pro-subscription/111302)
- [Another report](https://discuss.ai.google.dev/t/subscription-recognition-issue-antigravity-app-limited-to-free-tier/111865)

**Workaround:** Log out and back in, ensure email matches subscription email, check Google One status directly.

---

## 3. Antigravity + MCP (Model Context Protocol)

### Native MCP Support — YES

Antigravity has **full MCP support** for connecting to external tools and data sources.

### Configuration Location

```
$HOME/.gemini/antigravity/mcp_config.json
```

Or via UI: `... menu → MCP → Manage MCP Servers → View raw config`

### How to Add MCP Servers

1. Open Antigravity editor
2. Click `...` in prompt editor → MCP → Manage MCP Server
3. Edit `mcp.json` to add server configurations
4. Refresh and verify tools appear

### Example MCP Config

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token"
      }
    },
    "supabase": {
      "command": "npx", 
      "args": ["-y", "@supabase/mcp-server"]
    }
  }
}
```

### Google's Official MCP Integrations

Google provides pre-built MCP servers for:
- **BigQuery** — Direct database access
- **AlloyDB/Spanner/Cloud SQL** — Database connectivity
- **Firebase** — Project management
- **Looker** — Analytics integration

**Source:** [Google Cloud Blog - MCP Integration](https://cloud.google.com/blog/products/data-analytics/connect-google-antigravity-ide-to-googles-data-cloud-services)

### Third-Party MCP Aggregators

**Rube MCP** (Composio) — Single MCP that routes to 500+ tools:
- GitHub, Supabase, Notion, Gmail, Slack, Figma
- Dynamic tool loading without context window bloat
- [Setup Guide](https://composio.dev/blog/howto-mcp-antigravity)

---

## 4. Antigravity for Remote/Headless Use

### TL;DR: Desktop-Only, But Workarounds Exist

Antigravity is **primarily a desktop application** — no official headless/CLI-only mode for the agent functionality.

### What Works Remotely

| Method | Supported | Notes |
|--------|-----------|-------|
| SSH to remote code folder | ✅ Partial | Can mount remote dirs but agent features limited |
| Chrome Remote Desktop | ✅ Yes | Full functionality via virtual desktop |
| Cloud Workstations | ✅ Yes | Google's official guide exists |
| WSL Integration | ✅ Yes | Works with WSL extension |
| Pure CLI/headless agents | ❌ No | Not supported (use Gemini CLI instead) |

### Chrome Remote Desktop Setup (Best Option for VPS)

Detailed guide: [Medium - Running Antigravity on Cloud Workstations](https://medium.com/google-cloud/using-chrome-remote-desktop-to-run-antigravity-on-a-cloud-workstation-or-just-in-a-container-d00296425a0f)

Steps:
1. Install Antigravity on cloud VM with desktop environment (XFCE)
2. Install Chrome Remote Desktop
3. Connect from any browser

### For Headless AI Coding — Use Gemini CLI Instead

If Dave wants AI coding on VPS without GUI:
```bash
# Gemini CLI uses same account/subscription
npm install -g @google/gemini-cli
gemini-cli auth login
gemini-cli code "implement feature X"
```

---

## 5. Antigravity vs Other AI IDEs

### Comparison Table

| Feature | Antigravity | Cursor | Windsurf | GitHub Copilot |
|---------|------------|--------|----------|----------------|
| **Price** | Free (preview) + Pro tiers | $20/month Pro | $15/month Pro | $10/month |
| **Agent Mode** | Native, multi-agent | Single agent | Flow-based | No true agent |
| **Parallel Agents** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Browser Integration** | ✅ Built-in | ❌ No | ❌ No | ❌ No |
| **Artifacts/Reports** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **MCP Support** | ✅ Native | ✅ Yes | ✅ Yes | ❌ No |
| **Base IDE** | VS Code fork | VS Code fork | VS Code fork | VS Code ext |
| **SWE-bench Score** | ~76.2% | ~77% | Similar | Lower |

### When to Choose Antigravity

- **Need parallel agent execution** (multiple tasks simultaneously)
- **Browser-based testing/validation** is important
- **Already have Google AI Pro subscription** (essentially free)
- **Complex, multi-step tasks** that benefit from artifact-based review

### When to Choose Cursor/Others

- Need **most mature/stable** experience
- Prefer **predictable monthly pricing**
- Don't need browser integration
- Want **larger community/ecosystem**

---

## 6. Integration Possibilities: Dave's Use Case

### Scenario: Dave on Local Machine + VPS via MCP

**Can Dave use Antigravity locally, connected to our VPS resources via MCP?**

**Answer: YES — This is the ideal setup**

### Architecture

```
┌─────────────────────────┐
│   Dave's Local Machine  │
│   + Antigravity IDE     │
│   + Gemini AI Pro Sub   │
│                         │
│   ↓ MCP Connection ↓    │
└─────────────────────────┘
            │
            │ (stdio/HTTP)
            ▼
┌─────────────────────────┐
│   Keiracom VPS          │
│   + MCP Server(s)       │
│   + Supabase access     │
│   + Railway deployments │
│   + Code repos          │
└─────────────────────────┘
```

### What This Gives You

1. **Gemini 3 Pro access** — via Dave's subscription (no API billing)
2. **VPS tool access** — via MCP servers running on the VPS
3. **Database queries** — Supabase MCP server
4. **Deployments** — Railway/Vercel MCP integrations
5. **Git operations** — GitHub MCP server

### Limitations

1. **GUI Required** — Dave must run Antigravity on his local machine (not headless on VPS)
2. **Rate limits apply** — Even with AI Pro, heavy usage will hit limits (5-hour refresh)
3. **Bugs** — Subscription recognition issues may require workarounds
4. **MCP Server Hosting** — VPS needs to run MCP servers for this to work

---

## 7. Recommendation

### Can We Use Antigravity to Leverage Dave's Subscription?

# ✅ YES — Recommended Setup

### Step-by-Step Setup Guide

#### Phase 1: Local Antigravity Setup (Dave's Machine)

1. **Download Antigravity**
   ```
   https://antigravity.google/download
   ```

2. **Install and Launch**
   - Run installer
   - Choose "Fresh start" or import VS Code settings
   - Select Review-driven development mode (recommended)

3. **Sign In with Subscribed Google Account**
   - Use the Gmail tied to AI Pro subscription
   - Verify in Settings that "AI Pro" tier is recognized

4. **Verify Subscription Status**
   - Go to Settings → Account
   - Should show "AI Pro" with 5-hour refresh limits
   - If showing "Free Plan", try: logout → clear cache → login again

#### Phase 2: VPS MCP Server Setup

1. **Install MCP Server Framework on VPS**
   ```bash
   npm install -g @modelcontextprotocol/server-stdio
   ```

2. **Create Custom MCP Server for Keiracom Tools**
   ```bash
   # Example: Supabase access
   npm install -g @supabase/mcp-server
   
   # Example: GitHub
   npm install -g @modelcontextprotocol/server-github
   ```

3. **Configure SSH Tunnel or HTTP Proxy**
   - MCP servers can run over SSH tunnels
   - Or expose via authenticated HTTP endpoint

4. **Add to Antigravity's mcp_config.json**
   ```json
   {
     "mcpServers": {
       "keiracom-supabase": {
         "command": "ssh",
         "args": ["vps", "supabase-mcp-server"]
       }
     }
   }
   ```

#### Phase 3: Workflow

1. Open Antigravity locally
2. Create workspace pointing to project
3. Use Agent Manager to spawn agents
4. Agents can access VPS resources via MCP
5. All AI inference uses Dave's subscription (no extra cost)

---

## 8. Alternative Approaches (If Antigravity Doesn't Work)

### Option A: Gemini CLI on VPS

```bash
# Install on VPS
npm install -g @google/gemini-cli

# Auth with Dave's account (one-time)
gemini-cli auth login

# Use for coding tasks
gemini-cli code "implement X"
```
- Uses same subscription
- True headless
- Less sophisticated than Antigravity agents

### Option B: Gemini Code Assist in VS Code

- Install Gemini Code Assist extension
- Sign in with AI Pro account
- Traditional copilot-style assistance
- Works over Remote-SSH to VPS

### Option C: Direct Gemini API (Pay-As-You-Go)

If subscription limits are insufficient:
- Gemini 3 Pro: ~$3.10 AUD/M input, ~$18.60 AUD/M output
- Requires Google Cloud billing setup
- More flexible but adds cost

---

## Summary

| Question | Answer |
|----------|--------|
| Does Antigravity use Gemini Max subscription? | **YES** — AI Pro gives higher limits |
| Is there separate API billing? | **NO** — Subscription covers it |
| Can it run headless on VPS? | **NO** — Desktop only (use Remote Desktop for workaround) |
| Does it support MCP? | **YES** — Native support |
| Can Dave use local Antigravity + VPS tools? | **YES** — Via MCP connection |
| Is it ready for production use? | **Partial** — Still buggy, improving rapidly |

### Final Verdict

**Dave should install Antigravity locally and leverage his existing subscription.** The MCP integration allows full access to VPS resources. The only cost is his existing ~$31 AUD/month Google AI Pro subscription — which he already has.

---

*Research compiled: February 2026*  
*Sources: Google official docs, developer blogs, community forums*
