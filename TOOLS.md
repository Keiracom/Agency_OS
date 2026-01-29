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
| Voice | Vapi (Calls) | ElevenLabs (Synthesis) |

### Data & Intelligence
| Category | Services |
| :--- | :--- |
| Enrichment | Apollo (Leads), Prospeo (Emails), DataForSEO (SEO) |
| Scraping | Apify |
| AI | Anthropic (Primary), OpenRouter (Fallback) |

## 🚀 Projects & Deployment

| Project | Strategy | Live URL / Notes |
| :--- | :--- | :--- |
| elliot-mobile | `eas build --platform android --profile preview` | Expo: `elliotdave` |
| elliot-dashboard | Vercel (Auto-deploy) | elliot-dashboard.vercel.app |
| Agency_OS | Railway + Vercel | PRs Only (Dave merges) |

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
