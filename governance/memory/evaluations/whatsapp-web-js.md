# Tool Evaluation: whatsapp-web.js

**Evaluated:** 2026-01-30
**Source:** https://github.com/pedroslopez/whatsapp-web.js
**Stars:** 16,000+

## What It Does
A WhatsApp client library for Node.js that operates via WhatsApp Web browser automation:
- Send/receive messages, media, stickers, contacts, locations
- Group management (create, join, invite, manage participants)
- Message reactions, replies, polls
- Multi-device support
- Channels support

Uses Puppeteer to control WhatsApp Web interface.

## Pricing
- **Open Source** (Apache 2.0)
- Free to use

## Integration Complexity with Our Stack
| Factor | Assessment |
|--------|------------|
| Stack | Node.js - would need separate service |
| Risk | **HIGH** - WhatsApp ToS violation risk |
| Stability | Browser automation = fragile |
| Maintenance | Breaks when WhatsApp updates |

**Complexity: MEDIUM-HIGH** - Node.js service + ToS risk

## Competitors/Alternatives
- **Unipile** (what we use) - Official API approach, LinkedIn too
- **WhatsApp Business API** - Official, requires approval
- **Twilio WhatsApp** - Official channel, messaging limits
- **MessageBird** - Official WhatsApp partner

## Analysis
⚠️ **RISK ALERT**: WhatsApp explicitly prohibits bots/unofficial clients.

From their disclaimer:
> "It is not guaranteed you will not be blocked by using this method. WhatsApp does not allow bots or unofficial clients on their platform, so this shouldn't be considered totally safe."

We already have:
1. **Unipile** for LinkedIn automation (similar risk profile)
2. **Twilio** for SMS/calls (official)

WhatsApp automation risks:
- Account bans
- Phone number blacklisting  
- Legal/compliance issues for B2B outreach

## Recommendation: **SKIP**

**Reasoning:**
1. **ToS violation risk** - Could get accounts/numbers banned
2. We already have Unipile for similar functionality
3. WhatsApp Business API exists for legitimate use cases
4. B2B cold outreach via WhatsApp is legally questionable in many jurisdictions
5. Browser automation is inherently fragile

**Action:** If WhatsApp outreach becomes a priority, explore official WhatsApp Business API or Twilio's WhatsApp channel instead.
