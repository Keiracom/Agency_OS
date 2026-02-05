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

## 🔌 MCP Servers (LAW VI: Use First)

**Location:** `/home/elliotbot/clawd/mcp-servers/`

When an MCP exists for a service, USE IT instead of exec/curl. MCPs provide type-safe, error-handled, native tool access.

### Ready to Deploy (Existing)

| MCP | Package | Status |
| :--- | :--- | :--- |
| Supabase | `@supabase/mcp-server` | ✅ Ready |
| GitHub | `@modelcontextprotocol/server-github` | ✅ Ready |
| Redis | `@modelcontextprotocol/server-redis` | ✅ Ready |
| Brave Search | `brave/brave-search-mcp-server` | ✅ Ready |

### Custom Built (Infrastructure)

| MCP | Tools | Use Instead Of |
| :--- | :--- | :--- |
| `prefect-mcp` | list_flows, trigger_run, get_failed_runs, etc. | `exec + curl` to Prefect API |
| `railway-mcp` | list_projects, get_logs, redeploy, rollback, etc. | `exec + curl` to Railway GraphQL |
| `vercel-mcp` | list_deployments, create_deployment, promote, etc. | `exec + vercel` CLI |

### Custom Built (Enrichment)

| MCP | Tools | Use Instead Of |
| :--- | :--- | :--- |
| `apollo-mcp` | search_people, enrich_person, get_credits, etc. | `python tools/enrichment_master.py` |
| `prospeo-mcp` | find_email, verify_email, linkedin_to_email, etc. | `python tools/enrichment_master.py` |
| `hunter-mcp` | domain_search, email_finder, email_verifier | ⚠️ Needs `HUNTER_API_KEY` |
| `dataforseo-mcp` | serp_google, keyword_data, backlinks, etc. | `exec + curl` |

### Custom Built (Outreach)

| MCP | Tools | Use Instead Of |
| :--- | :--- | :--- |
| `salesforge-mcp` | list_campaigns, create_campaign, add_leads, etc. | `exec + curl` to Salesforge |
| `vapi-mcp` | list_assistants, start_call, get_transcript, etc. | `exec + curl` to Vapi |
| `telnyx-mcp` | send_sms, list_phone_numbers, make_call, etc. | `exec + curl` to Telnyx |
| `unipile-mcp` | search_profiles, send_connection, send_message, etc. | Manual LinkedIn |
| `resend-mcp` | send_email, list_domains, get_analytics, etc. | `exec + curl` to Resend |

### Custom Built (Memory)

| MCP | Tools | Use Instead Of |
| :--- | :--- | :--- |
| `memory-mcp` | search, save, bulk_save, get_stats, etc. | `python tools/memory_master.py` |

### Missing API Keys

| Key | Service | Get From |
| :--- | :--- | :--- |
| `HUNTER_API_KEY` | Hunter.io | https://hunter.io/api (free tier: 25/mo) |
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

# Railway
curl -H "Authorization: Bearer $Railway_Token" https://backboard.railway.app/graphql/v2
```
