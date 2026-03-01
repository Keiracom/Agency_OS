# TOOLS.md - Infrastructure & Access

## 🔐 Credentials

* **Env File:** `~/.config/agency-os/.env` (source to load)
* **GitHub:** User `Keiracom` (Full R/W access confirmed 2026-01-28)
* **Region:** AP-Southeast-1 (Singapore) matches DB/Backend
* **Timezone:** Dave = AEST (UTC+11). 9am Sydney = 22:00 UTC (previous day).

## 🛠 Service Stack

### Core Infrastructure
| Service | Endpoint/ID | Notes |
| :--- | :--- | :--- |
| Supabase | `jatzvazlbusedwsnqxzr.supabase.co` | DB (AP-SE-1) |
| Railway | `fef5af27-a022-4fb2-996b-cad099549af9` | Backend Hosting |
| Prefect | `prefect-server-production-f9b1.up.railway.app` | Self-hosted Orchestration |
| Redis | `clever-stag-35095.upstash.io` | Upstash |

### Communication & Outreach
| Channel | Primary Tool | Support/Alt |
| :--- | :--- | :--- |
| Cold Email | Salesforge Ecosystem | InfraForge (Domains), WarmForge (Warmup) |
| Transactional | Resend | - |
| LinkedIn | Unipile (Automation) | ~~HeyReach~~ (Deprecated) |
| SMS/Phone | Twilio (+61240126220) | ClickSend |
| Voice | Vapi (Orchestration) | Cartesia TTS + Groq LLM (90%) + Claude Haiku (10%) |

### Data & Intelligence
| Category | Services |
| :--- | :--- |
| Enrichment | Apollo (Leads), Prospeo (Emails), DataForSEO (SEO) |
| Scraping | **Autonomous Stealth Browser** (Primary) |
| AI | Anthropic (Primary), OpenRouter (Fallback) |

## 🔌 MCP Bridge (PRIMARY API ACCESS)

**⚠️ LAW VI MANDATE:** MCP Bridge is your FIRST access point for external services. See AGENTS.md LAW VI.

### Location
```
/home/elliotbot/clawd/skills/mcp-bridge/scripts/mcp-bridge.js
```

### Commands
```bash
cd /home/elliotbot/clawd/skills/mcp-bridge

# List all MCP servers
node scripts/mcp-bridge.js servers

# List tools from a server
node scripts/mcp-bridge.js tools <server>

# Call an MCP tool
node scripts/mcp-bridge.js call <server> <tool> [args_json]
```

### Available Servers (15 total)

| Server | Description | Status |
| :--- | :--- | :--- |
| **supabase** | Database queries, tables, SQL execution | ✅ npm |
| **redis** | Cache get/set, lists, pub/sub | ✅ npm |
| **prefect** | Workflows, flows, deployments, runs | ✅ Built |
| **railway** | Deployments, services, logs | ✅ Built |
| **vercel** | Projects, domains, deployments | ✅ Built |
| **apollo** | People search, company enrichment | ✅ Built |
| **prospeo** | Email finder, verification | ✅ Built |
| **hunter** | Domain search, email verification | ✅ Built |
| **dataforseo** | SERP, keywords, backlinks | ✅ Built |
| **salesforge** | Campaigns, sequences, leads | 🔄 Converting |
| **vapi** | Voice assistants, calls, transcripts | 🔄 Converting |
| **telnyx** | SMS, voice, phone numbers | 🔄 Converting |
| **unipile** | LinkedIn profiles, connections | 🔄 Converting |
| **resend** | Transactional email, domains | 🔄 Converting |
| **memory** | Semantic search, embeddings | 🔄 Converting |

### Key Examples

```bash
# Query Agency OS database
node scripts/mcp-bridge.js call supabase execute_sql \
  '{"project_id":"jatzvazlbusedwsnqxzr","query":"SELECT * FROM leads LIMIT 5"}'

# List Prefect flows
node scripts/mcp-bridge.js call prefect list_flows

# Search Apollo for contacts
node scripts/mcp-bridge.js call apollo search_people '{"domain":"acme.com","limit":10}'

# Get Railway deployment logs
node scripts/mcp-bridge.js call railway get_logs '{"deployment_id":"xxx"}'

# Trigger Prefect flow run
node scripts/mcp-bridge.js call prefect trigger_run '{"deployment_name":"daily-scrape"}'
```

### Agency OS Project ID
**Supabase:** `jatzvazlbusedwsnqxzr` (always use this for Agency OS queries)

### When to Use
- ✅ **ALWAYS** for Supabase/database queries
- ✅ **ALWAYS** for Prefect workflow operations
- ✅ **ALWAYS** for enrichment (Apollo, Prospeo, Hunter)
- ✅ **ALWAYS** for infrastructure (Railway, Vercel)
- ❌ **NEVER** use `exec + curl` when MCP exists
- ❌ **NEVER** use Python scripts for MCP-covered services

---

## 🕵️ Autonomous Stealth Browser (PRIMARY WEB ACCESS)

**⚠️ MANDATORY:** This is the ONLY approved method for web access. NEVER use `requests`, `urllib`, or raw HTTP calls for scraping.

### Tool Location
```
tools/autonomous_browser.py   # Main browser tool
tools/proxy_manager.py        # Proxy swarm management
```

### Capabilities
| Feature | Status |
| :--- | :--- |
| Proxy Rotation | 215,084 residential proxies (Webshare) |
| User-Agent Spoofing | Chrome/Firefox/Safari/Edge rotation |
| Fingerprint Randomization | Viewport, timezone, locale per request |
| Burner Protocol | Auto-retry on 403/429/503 with new identity |
| JavaScript Rendering | Full Chromium browser via Playwright |
| Anti-Detection | webdriver flag spoofed, chrome.runtime injected |

### Usage
```python
# Async (preferred)
from tools.autonomous_browser import autonomous_fetch
result = await autonomous_fetch("https://example.com", stealth=True)

# Sync wrapper
from tools.autonomous_browser import fetch_sync
result = fetch_sync("https://example.com")

# CLI
python tools/autonomous_browser.py fetch "https://example.com"
```

### When to Use
- ✅ **ALWAYS** for any website scraping
- ✅ **ALWAYS** for sites with bot protection
- ✅ **ALWAYS** for JavaScript-heavy pages
- ❌ **NEVER** use `requests.get()` for scraping
- ❌ **NEVER** use `urllib` for web content
- ❌ ~~Apify~~ (Deprecated - cost savings)

### Proxy Management
```bash
python tools/proxy_manager.py sync      # Refresh proxy list (auto-weekly)
python tools/proxy_manager.py verify    # Confirm IP is hidden
python tools/proxy_manager.py test      # Test random proxies
```

### Scraping Hierarchy (Check First!)
Before full browser automation, try in order:
1. **JSON/API endpoint** — e.g., Reddit: add `.json` to any URL
2. **RSS feed** — Structured XML, no JS
3. **Old/lite version** — `old.reddit.com`, mobile sites
4. **Full browser** — Last resort

*Lesson: Reddit Playwright = 30s timeout. Reddit JSON = 2s success.*

## 🔍 Web Search & Knowledge Retrieval

### Stack Clarification (SSOT)
| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Browser Engine** | Chromium via Playwright | JavaScript rendering, stealth scraping |
| **Proxy Layer** | Webshare (215k residential IPs) | IP rotation, anti-detection |
| **Web Search API** | Brave Search API | Knowledge retrieval, research queries |

**⚠️ IMPORTANT:** There is NO "Brave Browser" in this stack. Brave Search API is a REST endpoint for web queries — completely separate from browser automation.

### Brave Search API
- **Location:** `infrastructure/smart_context.py`
- **Function:** `brave_search(query)` 
- **Purpose:** Mid-session context retrieval when Supabase has no match
- **Env Var:** `BRAVE_API_KEY`
- **Cost:** Free tier available

### Architecture Flow
```
Scraping:    Request → Webshare Proxy → Chromium (Playwright) → Parse
Research:    Query → Brave Search API → JSON results → Context injection
```

*Corrected: 2026-02-03 — Audit revealed verbal "Brave browser" references were inaccurate.*

## 🚀 Projects & Deployment

| Project | Strategy | Live URL / Notes |
| :--- | :--- | :--- |
| elliot-mobile | `eas build --platform android --profile preview` | Expo: `elliotdave` |
| elliot-dashboard | Vercel (Auto-deploy) | elliot-dashboard.vercel.app |
| Agency_OS | Railway + Vercel | PRs Only (Dave merges) |

## 🛠️ Local Dev Tools

### yek (Codebase Context)
Fast file serializer for LLM ingestion. Generates tree + file contents in one pass.

```bash
# Direct usage
yek --max-size 100K --tree-header src/api

# Via wrapper script (recommended)
./scripts/yek-context.sh agency-os 100K    # Backend src/
./scripts/yek-context.sh frontend 50K      # Frontend src/
./scripts/yek-context.sh mobile 100K       # Elliot Mobile
./scripts/yek-context.sh src/api 200K      # Specific path
```

Output lands in `.context/` directory. Use for sub-agent context injection.

## 🔌 MCP Servers Reference

**⚠️ DEPRECATED SECTION** — Use the **MCP Bridge** at the top of this file.

All MCP access now goes through the unified bridge:
```bash
cd /home/elliotbot/clawd/skills/mcp-bridge
node scripts/mcp-bridge.js servers    # List all
node scripts/mcp-bridge.js tools <server>    # Discover tools
node scripts/mcp-bridge.js call <server> <tool> [args]    # Execute
```

See **🔌 MCP Bridge (PRIMARY API ACCESS)** section above for full documentation.

### Missing API Keys (Still Needed)

| Key | Service | Get From |
| :--- | :--- | :--- |
| `LEADMAGIC_API_KEY` | LeadMagic | https://leadmagic.io/ |
| `SLACK_BOT_TOKEN` | Slack | https://api.slack.com/apps |
| `NOTION_API_KEY` | Notion | https://www.notion.so/my-integrations |
| `LINEAR_API_KEY` | Linear | https://linear.app/settings/api |

## 🩺 Quick Diagnostics

```bash
# Supabase
curl -H "apikey: $SUPABASE_ANON_KEY" "$SUPABASE_URL/rest/v1/"

# Prefect
curl "$PREFECT_API_URL/health"

# Salesforge
curl -H "Authorization: Bearer $SALESFORGE_API_KEY" "$SALESFORGE_API_URL/health"

# Railway (GraphQL API)
# Docs: https://docs.railway.com/reference/public-api
# Endpoint: https://backboard.railway.com/graphql/v2 (NOTE: .com not .app)

# Token Types (create at https://railway.com/account/tokens):
# - Account token ("No workspace"): Can query `me`, but NOT workspace projects
# - Workspace token (select workspace): Can query projects/services, but NOT `me`
# - Project token: Scoped to one environment (use Project-Access-Token header instead)

# We have TWO tokens:
# - Railway_Token (workspace): a2d2460d-8447-4305-ad19-63328a25ab03 → for projects
# - Railway_Account_Token: 937acaed-f77e-431a-a19a-95b7d107255d → for account queries

# List projects (use workspace token):
curl --request POST \
  --url https://backboard.railway.com/graphql/v2 \
  --header "Authorization: Bearer $Railway_Token" \
  --header "Content-Type: application/json" \
  --data '{"query":"query { projects { edges { node { id name } } } }"}'

# Get services for Agency OS project:
curl --request POST \
  --url https://backboard.railway.com/graphql/v2 \
  --header "Authorization: Bearer $Railway_Token" \
  --header "Content-Type: application/json" \
  --data '{"query":"query { project(id: \"fef5af27-a022-4fb2-996b-cad099549af9\") { services { edges { node { id name } } } } }"}'

# Get deployments for a service:
curl --request POST \
  --url https://backboard.railway.com/graphql/v2 \
  --header "Authorization: Bearer $Railway_Token" \
  --header "Content-Type: application/json" \
  --data '{"query":"query { service(id: \"SERVICE_ID\") { deployments { edges { node { id status } } } } }"}'

# Agency OS Project ID: fef5af27-a022-4fb2-996b-cad099549af9
```
