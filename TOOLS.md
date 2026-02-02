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
