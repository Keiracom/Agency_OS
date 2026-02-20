# Agency OS — Delegated Access Requirements

**Purpose:** Complete access requirements for Elliottbot to operate Agency OS autonomously without Dave needing to log into platform consoles.

**Generated:** 2026-02-20 23:22 UTC  
**Source:** LAW I-A verified from `.env` files, `src/integrations/`, and MCP servers

---

## 1. Complete Platform List (Verified from SSOT)

### Core Infrastructure
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| Supabase | Database, Auth, Storage | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_ACCESS_TOKEN`, `SUPABASE_PROJECT_REF` |
| Railway | Backend deployment | `Railway_Token`, `Railway_Account_Token`, `Railway_Workspace_Token` |
| Vercel | Frontend deployment | `VERCEL_TOKEN` |
| Upstash Redis | Cache, rate limiting | `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` |
| Prefect | Workflow orchestration | `PREFECT_API_URL` |
| GitHub | Source control | `GITHUB_TOKEN` |

### AI / LLM Providers
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| Anthropic | Claude models | `ANTHROPIC_API_KEY` |
| OpenAI | GPT models, Whisper | `OPENAI_API_KEY` |
| OpenRouter | Multi-model gateway | `OPENROUTER_API_KEY` |
| Groq | Fast Llama inference | `GROQ_API_KEY` |
| RunPod | GPU compute | `RUNPOD_API_KEY` |

### Voice / Telephony
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| ElevenLabs | Voice AI, TTS | `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` |
| Vapi | Voice assistants | `VAPI_API_KEY`, `VAPI_PHONE_NUMBER_ID` |
| Twilio | SMS, Voice calls | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` |
| Telnyx | Communications | `TELNYX_API_KEY` |
| ClickSend | SMS gateway | `CLICKSEND_USERNAME`, `CLICKSEND_API_KEY` |

### Email
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| Resend | Transactional email | `RESEND_API_KEY` |
| Google Gmail | OAuth email send | `GOOGLE_GMAIL_CLIENT_ID`, `GOOGLE_GMAIL_CLIENT_SECRET` |
| Salesforge | Email sequences | `SALESFORGE_API_KEY`, `SALESFORGE_API_URL` |
| WarmForge | Email warming | `WARMFORGE_API_KEY`, `WARMFORGE_API_URL` |
| InfraForge | Email infrastructure | `INFRAFORGE_API_KEY`, `INFRAFORGE_API_URL` |

### LinkedIn / Outreach
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| Unipile | LinkedIn automation | `UNIPILE_API_KEY`, `UNIPILE_API_URL` |
| HeyReach | LinkedIn (legacy) | `HEYREACH_API_KEY` |

### Enrichment / Data
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| Hunter | Email finder | `HUNTER_API_KEY` |
| Prospeo | Email verification | `PROSPEO_API_KEY` |
| DataForSEO | SEO data, SERP | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` |
| Apify | Web scraping | `APIFY_API_KEY` |
| ABN Lookup | Australian business registry | `ABN_LOOKUP_GUID` |
| Brave | Web search | `BRAVE_API_KEY` |

### Proxies
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| BrightData | Residential proxies | `BRIGHTDATA_API_KEY` |
| Webshare | Datacenter proxies | `WEBSHARE_API_KEY` |

### Social / Content
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| YouTube | Video upload | `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` |
| Telegram | Bot notifications | `TELEGRAM_TOKEN` |
| HeyGen | AI video generation | (via integration) |

### Payments
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| Stripe | Billing, subscriptions | (via integration, keys in Supabase) |

### Design / UI
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| Plasmic | Visual design | `NEXT_PUBLIC_PLASMIC_PROJECT_ID`, `NEXT_PUBLIC_PLASMIC_PROJECT_API_TOKEN` |
| V0 | UI generation | `V0_API_KEY` |

### Mobile
| Platform | Purpose | Env Vars |
|----------|---------|----------|
| Expo | Push notifications | `EXPO_TOKEN` |

---

## 2. Per-Platform Access Requirements

### TIER 1: Simple API Keys (No 2FA, No Expiry)

| Platform | Access Method | 2FA | Token Expiry | Dave Action |
|----------|--------------|-----|--------------|-------------|
| **Anthropic** | API Key | No | Never | Console → API Keys → Create → Paste |
| **OpenAI** | API Key | No | Never | Platform → API Keys → Create → Paste |
| **OpenRouter** | API Key | No | Never | Dashboard → Keys → Create → Paste |
| **Groq** | API Key | No | Never | console.groq.com → API Keys → Paste |
| **ElevenLabs** | API Key | No | Never | Profile → API Keys → Copy |
| **Vapi** | API Key | No | Never | Dashboard → API → Copy |
| **Resend** | API Key | No | Never | Dashboard → API Keys → Create |
| **Hunter** | API Key | No | Never | Dashboard → API → Copy |
| **Prospeo** | API Key | No | Never | Settings → API → Copy |
| **Brave** | API Key | No | Never | API Dashboard → Keys → Create |
| **Apify** | API Key | No | Never | Settings → Integrations → API Token |
| **RunPod** | API Key | No | Never | Settings → API Keys → Create |
| **V0** | API Key | No | Never | Settings → API → Create |

### TIER 2: API Keys with 2FA on Account

| Platform | Access Method | 2FA | Token Expiry | Dave Action | Gotchas |
|----------|--------------|-----|--------------|-------------|---------|
| **Supabase** | Service Key + Access Token | TOTP | Never (service key) / 1yr (access token) | Dashboard → Settings → API → Copy service_role key | Access token for management API needs refresh yearly |
| **Railway** | API Tokens | TOTP | Never | Account Settings → Tokens → Create | Three token types: Account, Workspace, Project |
| **Vercel** | API Token | TOTP | Never | Settings → Tokens → Create | Scope to specific team if needed |
| **GitHub** | Personal Access Token | TOTP | Configurable | Settings → Developer → Tokens → Create (fine-grained) | Set repo scope; fine-grained tokens expire |
| **Twilio** | Account SID + Auth Token | SMS/TOTP | Never | Console → Account → API Credentials | **Trial account needs upgrade for unverified calls** |
| **Telnyx** | API Key | TOTP | Never | API Keys → Create | |
| **ClickSend** | Username + API Key | No | Never | Settings → API Credentials | |

### TIER 3: Username + Password Auth

| Platform | Access Method | 2FA | Token Expiry | Dave Action | Gotchas |
|----------|--------------|-----|--------------|-------------|---------|
| **DataForSEO** | Login + Password | No | Never | Account → API Access → Copy credentials | Basic auth, not API key |

### TIER 4: OAuth Platforms (Session/Token Required)

| Platform | Access Method | 2FA | Token Expiry | Dave Action | Automation Notes |
|----------|--------------|-----|--------------|-------------|------------------|
| **Google Gmail** | OAuth 2.0 | Yes (Google) | Access: 1hr / Refresh: 6mo | GCP Console → OAuth → Create credentials | Refresh token can be stored; access token auto-refreshes |
| **YouTube** | OAuth 2.0 | Yes (Google) | Access: 1hr / Refresh: 6mo | Same as Gmail | Needs YouTube Data API enabled |
| **Unipile** | OAuth via Unipile hosted | LinkedIn 2FA | Session-based | Unipile dashboard → Connect LinkedIn → Complete OAuth | Unipile handles LinkedIn session; API key is stable |
| **Stripe** | OAuth + API Key | TOTP | Never (restricted keys) | Dashboard → Developers → API Keys | Use restricted keys for security |

### TIER 5: Platform-Managed Sessions

| Platform | Access Method | 2FA | Token Expiry | Dave Action | Notes |
|----------|--------------|-----|--------------|-------------|-------|
| **Salesforge** | API Key | No | Never | Dashboard → Settings → API | API handles all email operations |
| **WarmForge** | API Key | No | Never | Dashboard → API | Email warming managed via API |
| **InfraForge** | API Key | No | Never | Dashboard → API | Infrastructure managed via API |
| **HeyReach** | API Key | No | Never | Settings → API | Legacy; migrating to Unipile |

---

## 3. OAuth Token Capture Approach

### Google OAuth (Gmail + YouTube)

**Token Types:**
- `access_token`: Short-lived (1 hour), used for API calls
- `refresh_token`: Long-lived (6 months inactive), used to get new access tokens

**Capture Method:**
1. Dave completes OAuth flow once in browser
2. Playwright captures the authorization code from redirect URL
3. Exchange code for tokens via Google OAuth endpoint
4. Store `refresh_token` in Supabase Vault (encrypted)
5. Application auto-refreshes `access_token` as needed

**Re-auth Triggers:**
- Refresh token expires (6 months of non-use)
- User revokes access in Google Account settings
- Scope changes require new consent

**Implementation:**
```python
# Token refresh flow (already in codebase)
async def refresh_google_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )
        return response.json()
```

### Unipile (LinkedIn)

**How it works:**
- Unipile provides hosted OAuth flow for LinkedIn
- User connects LinkedIn account via Unipile dashboard (one-time)
- Unipile maintains the LinkedIn session internally
- Elliottbot only needs Unipile API key (stable, no expiry)

**Re-auth Triggers:**
- LinkedIn password change
- LinkedIn security event (suspicious login)
- LinkedIn rate limit enforcement (rare)

**Dave Action:** If LinkedIn disconnects, reconnect via Unipile dashboard.

### Stripe

**How it works:**
- Stripe uses API keys, not OAuth for server operations
- OAuth only needed for Connect (multi-merchant) which we don't use
- Restricted API keys with specific permissions are recommended

**Implementation:**
- Create restricted key with only needed permissions
- Store in Vault
- No expiry, no re-auth needed

---

## 4. Supabase Vault Structure

### Naming Convention

```
secrets/
├── infra/
│   ├── supabase_service_key
│   ├── railway_token
│   ├── vercel_token
│   ├── github_token
│   └── upstash_redis_token
├── ai/
│   ├── anthropic_api_key
│   ├── openai_api_key
│   ├── openrouter_api_key
│   ├── groq_api_key
│   └── runpod_api_key
├── voice/
│   ├── elevenlabs_api_key
│   ├── vapi_api_key
│   ├── twilio_account_sid
│   ├── twilio_auth_token
│   ├── telnyx_api_key
│   └── clicksend_credentials
├── email/
│   ├── resend_api_key
│   ├── google_gmail_refresh_token
│   ├── salesforge_api_key
│   ├── warmforge_api_key
│   └── infraforge_api_key
├── linkedin/
│   ├── unipile_api_key
│   └── heyreach_api_key
├── enrichment/
│   ├── hunter_api_key
│   ├── prospeo_api_key
│   ├── dataforseo_credentials
│   ├── apify_api_key
│   ├── brightdata_api_key
│   ├── webshare_api_key
│   └── brave_api_key
├── social/
│   ├── youtube_refresh_token
│   └── telegram_token
├── payments/
│   └── stripe_restricted_key
└── design/
    ├── plasmic_tokens
    └── v0_api_key
```

### Encryption Approach

Supabase Vault provides:
- **Encryption at rest:** AES-256-GCM via `pgsodium`
- **Key management:** Vault master key stored in Supabase infrastructure
- **Access control:** Row-level security (RLS) policies

**Implementation:**

```sql
-- Create vault schema if not exists
CREATE SCHEMA IF NOT EXISTS vault;

-- Enable vault extension
CREATE EXTENSION IF NOT EXISTS supabase_vault;

-- Store a secret
SELECT vault.create_secret(
  'anthropic_api_key',
  'sk-ant-xxx...',
  'Anthropic Claude API key'
);

-- Retrieve a secret (only accessible by service role)
SELECT decrypted_secret 
FROM vault.decrypted_secrets 
WHERE name = 'anthropic_api_key';
```

### Access Control

```sql
-- RLS policy: Only service role can access vault
CREATE POLICY "Service role only" ON vault.secrets
  FOR ALL
  USING (auth.role() = 'service_role');

-- Audit log for credential access
CREATE TABLE vault.access_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  secret_name TEXT NOT NULL,
  accessed_by TEXT NOT NULL,
  accessed_at TIMESTAMPTZ DEFAULT NOW(),
  operation TEXT NOT NULL,
  ip_address INET
);

-- Trigger to log access
CREATE OR REPLACE FUNCTION vault.log_access()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO vault.access_log (secret_name, accessed_by, operation)
  VALUES (NEW.name, current_user, TG_OP);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## 5. DAVE ONLY Items (Cannot Be Delegated)

### 🔴 Biometric / Identity Verification

| Platform | Requirement | Why It Can't Be Delegated |
|----------|-------------|---------------------------|
| **Stripe Atlas** | Live selfie + Government ID | Australian Director verification |
| **Twilio Regulatory Bundle** | ID verification for AU numbers | Required for +61 numbers |
| **Australian Business Registry** | myGovID | Director authentication |

### 🔴 Account-Level Security Actions

| Action | Platform | Why |
|--------|----------|-----|
| Password changes | All | Security best practice |
| 2FA setup/recovery | All with 2FA | Requires authenticator app |
| Account recovery | All | Email/phone verification to Dave |
| Billing/payment updates | Stripe, Railway, etc. | Card holder verification |

### 🔴 Legal / Compliance

| Action | Platform | Why |
|--------|----------|-----|
| Terms acceptance | New platforms | Legal liability |
| GDPR data requests | Supabase, etc. | Data controller responsibility |
| Abuse report responses | Twilio, LinkedIn | Account holder responsibility |

### 🟡 One-Time OAuth Flows

| Platform | Action | Frequency |
|----------|--------|-----------|
| Google Gmail/YouTube | Initial OAuth consent | Once (refresh token stored) |
| LinkedIn (via Unipile) | Account connection | Once per LinkedIn account |

---

## 6. Handover Checklist

Dave completes this checklist once to enable full Elliottbot autonomy:

### Phase 1: Core Infrastructure (Do First)
- [ ] Supabase: Confirm service key and access token in vault
- [ ] Railway: Generate and paste all three token types
- [ ] Vercel: Generate team-scoped token
- [ ] GitHub: Generate fine-grained PAT with repo scope
- [ ] Upstash: Confirm REST URL and token

### Phase 2: AI Providers
- [ ] Anthropic: Generate API key, paste
- [ ] OpenAI: Generate API key, paste
- [ ] Groq: Generate API key, paste
- [ ] ElevenLabs: Copy API key and voice ID

### Phase 3: Communications
- [ ] Twilio: **Upgrade from trial account** (blocks test calls)
- [ ] Twilio: Copy Account SID + Auth Token
- [ ] Telnyx: Generate API key
- [ ] Vapi: Copy API key and phone number ID
- [ ] ClickSend: Copy username and API key

### Phase 4: Email
- [ ] Resend: Generate API key
- [ ] Google Gmail: Complete OAuth flow, store refresh token
- [ ] Salesforge: Copy API key
- [ ] WarmForge: Copy API key
- [ ] InfraForge: Copy API key

### Phase 5: LinkedIn
- [ ] Unipile: Connect LinkedIn account via Unipile dashboard
- [ ] Unipile: Copy API key

### Phase 6: Enrichment
- [ ] Hunter: Copy API key
- [ ] Prospeo: Copy API key
- [ ] DataForSEO: Copy login + password
- [ ] Apify: Copy API token
- [ ] BrightData: Copy API key
- [ ] Webshare: Copy API key

### Phase 7: Social
- [ ] YouTube: Complete OAuth flow, store refresh token
- [ ] Telegram: Confirm bot token

### Phase 8: Payments
- [ ] Stripe: Generate restricted API key with needed permissions

### Phase 9: Vault Migration
- [ ] Run vault setup SQL scripts
- [ ] Migrate all credentials from `.env` to Supabase Vault
- [ ] Update application to read from vault
- [ ] Remove credentials from `.env` files
- [ ] Confirm audit logging active

---

## 7. Ongoing Maintenance

### Automatic (No Dave Action)
- Google OAuth access token refresh (every hour)
- API key rotation alerts (if platform supports)
- Rate limit monitoring and alerting

### Periodic (Dave Action ~Yearly)
- Supabase access token refresh
- GitHub fine-grained PAT refresh (if expiry set)
- Google refresh token re-auth (if unused 6+ months)
- Security review of vault access logs

### Event-Driven (Dave Action When Triggered)
- LinkedIn reconnection (if session expires)
- Twilio compliance bundle updates
- Platform password changes after security events

---

*Document Version: 1.0*  
*Last Updated: 2026-02-20*  
*Maintainer: Elliottbot*
