# 2026-02-05 Session Summary

## Key Decisions Made

### 1. Maya Digital Employee (Spec'd)
- Maya = face of Agency OS (internal only, leads never see her)
- Dashboard hologram in bottom-right corner
- Pre-rendered video library for onboarding (~$100 one-time)
- Daily updates via LLM + Cartesia TTS (~$0.013/user/day)
- Support via text chat (LLM only)
- Need Midjourney for photorealistic face (DALL-E looked too fake)
- Full spec in MEMORY.md

### 2. Onboarding Simplified to Single Page
- ONE page only: Website URL + Connect CRM + Connect LinkedIn
- Email/Phone auto-provisioned from pre-warmed buffer (don't mention to user - "kitchen talk")
- User goes straight to dashboard after onboarding
- Maya does walkthrough on dashboard
- ICP extraction runs in background with progress bar

### 3. Campaign Lead Pool Allocation
- Sliders share 100% pool (can't exceed total)
- Tier determines max campaigns (Ignition = 5)
- AI suggests campaigns based on ICP extraction
- User adjusts allocation % before launch
- **LOCKED after launch** — machine turns on, can't adjust
- Channels determined by ALS, NOT user selection

### 4. HTML Prototypes Created
Location: `/home/elliotbot/clawd/agency-os-html/`

| File | Purpose |
|------|---------|
| `onboarding-simple.html` | Single page onboarding |
| `dashboard-v3.html` | Dashboard with ICP extraction bar + Maya |
| `campaigns-v4.html` | Lead allocation sliders, expandable sidebar |
| `campaign-customise.html` | Campaign editing form |

### 5. Outstanding Work
- **Industry dropdown**: Need searchable dropdown with ANZSIC-level industries (500+), not 8 checkboxes
- **Remove Channels from Customise**: ALS determines channels, not user
- **Maya face**: Need Midjourney prompts run for photorealistic result

## Infrastructure
- Telnyx API key saved to `.env`
- Onboarding flow analysis saved to `memory/2026-02-05-onboarding-flow-analysis.md`

## Next Session Pickup
1. Update campaign-customise.html with searchable industry dropdown
2. Remove Channels section from customise (ALS handles)
3. Generate Maya face via Midjourney
4. Review HTML prototypes with Dave
