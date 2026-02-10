# Gemini Boardroom Integration Plan

**Priority:** HIGH  
**Status:** APPROVED by Dave  
**Created:** 2026-02-04 00:50 UTC  
**Decision Maker:** Dave (CEO)

---

## 1. The Vision

Dave wants a **dual-AI collaboration system** where:
- **Gemini** = Co-founder / Strategic oversight (read-only access)
- **Elliot** = CTO / Execution (full access)
- **Dave** = Chairman with veto power (final sign-off on everything)

Both AIs communicate in a shared Telegram group ("Keiracom Boardroom"). Dave observes, interjects, and approves/rejects decisions.

**Why:** Dave's session quality with me (Claude) varies. A second AI provides:
- Consistent strategic oversight
- Work-checking between both AIs
- Reduced single-point-of-failure risk

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│              TELEGRAM GROUP: Keiracom Boardroom         │
│                                                         │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐            │
│  │  Dave   │    │ Elliot  │    │ Gemini  │            │
│  │ (Human) │    │ (Claude)│    │ (Google)│            │
│  │ Chairman│    │   CTO   │    │Co-founder│           │
│  └─────────┘    └─────────┘    └─────────┘            │
│       │              │              │                  │
│       │      ┌───────┴───────┐     │                  │
│       │      │   Clawdbot    │     │                  │
│       │      │  (existing)   │     │                  │
│       │      └───────────────┘     │                  │
│       │                            │                  │
│       │              ┌─────────────┴─────────────┐    │
│       │              │  Gemini Bridge Service    │    │
│       │              │  (new - deploy Railway)   │    │
│       │              └───────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │         READ-ONLY ACCESS          │
              │                                   │
              │  • Filesystem (~/clawd/)          │
              │  • Railway (deployments, logs)    │
              │  • Supabase (schema, data)        │
              │  • Vercel (deployments, logs)     │
              └───────────────────────────────────┘
```

---

## 3. Access Model

| Entity | Filesystem | Railway | Supabase | Vercel | Execution |
|--------|------------|---------|----------|--------|-----------|
| Dave | FULL | FULL | FULL | FULL | APPROVE |
| Elliot | READ/WRITE | READ/WRITE | READ/WRITE | READ/WRITE | EXECUTE |
| Gemini | READ | READ | READ | READ | PROPOSE |

**Key constraint:** Gemini can SEE everything but cannot EXECUTE anything. If Gemini wants an action taken, it proposes → Dave approves → Elliot executes.

---

## 4. Telegram Technical Details

### 4.1 Bot API Fundamentals
- **Endpoint:** `https://api.telegram.org/bot<token>/METHOD_NAME`
- **Methods:** GET or POST, JSON responses
- **Updates:** Webhooks (recommended) or long-polling

### 4.2 Privacy Mode (CRITICAL)
By default, bots in groups only see:
- Messages that @mention the bot
- Commands (messages starting with /)

**Action Required:** Disable privacy mode via @BotFather for Gemini bot:
```
/setprivacy → @GeminiBotName → Disable
```

This allows Gemini to see ALL messages in the group.

### 4.3 Group Setup
1. Create **private** group (not supergroup yet)
2. Add Elliot bot (existing Clawdbot)
3. Add Gemini bot (new)
4. Promote both to admin (so they can see all messages)
5. Convert to supergroup if needed for persistence

### 4.4 New API Feature (Bot API 9.3, Dec 2025)
`sendMessageDraft` — allows streaming partial messages while being generated. Useful for showing Gemini's responses as they stream (better UX than waiting for full response).

---

## 5. Gemini Bridge Service

### 5.1 Reference Implementation
GitHub: `shamspias/gemini-telegram-bot`
- Python + telebot + aiohttp
- Handles text and photo messages
- Async API communication
- MIT licensed, 10 commits, simple codebase

### 5.2 Our Implementation Requirements
```
gemini-bridge/
├── main.py           # Telegram bot + Gemini API integration
├── context.py        # Read-only context providers
├── requirements.txt  # Dependencies
├── .env.example      # Environment template
└── Dockerfile        # Railway deployment
```

### 5.3 Environment Variables
```
TELEGRAM_BOT_TOKEN=<from BotFather>
GEMINI_API_KEY=<from Google AI Studio>
BOARDROOM_CHAT_ID=<Telegram group ID>
ELLIOT_BOT_USERNAME=<for @mentions>
```

### 5.4 Core Logic
1. Bot receives message in Boardroom
2. If addressed to Gemini (or @all), process
3. Inject read-only context (file contents, status, etc.) 
4. Call Gemini API with context + message
5. Post response to Telegram
6. If action proposed, await Dave's approval

---

## 6. Read-Only Context Providers

### 6.1 Phase 1 — On-Demand (via Elliot)
Gemini asks in chat → Elliot provides the info
- Simple, no infrastructure
- Works immediately after Telegram setup

### 6.2 Phase 2 — MCP Servers (Direct Access)
Proper MCP integration so Gemini can query directly:

| MCP Server | Data Exposed |
|------------|--------------|
| filesystem-mcp | ~/clawd/ file contents (read-only) |
| railway-mcp | Deployments, logs, env vars |
| supabase-mcp | Schema, tables, read-only queries |
| vercel-mcp | Deployments, preview URLs, logs |

**MCP is becoming standard:** Even GitHub now has an MCP Registry (https://github.com/mcp).

### 6.3 API Tokens Needed (Read-Only Scope)

| Service | Token Type | Scope |
|---------|------------|-------|
| Railway | API Token | Read deployments, logs |
| Supabase | Service Role Key (or read-only role) | Read schema, data |
| Vercel | API Token | Read deployments |
| Google | Gemini API Key | Model access |

---

## 7. Implementation Phases

### Phase 1 — Tonight/Tomorrow (Telegram Boardroom MVP)
**Owner:** Dave + Elliot
**Effort:** 2-3 hours

1. ✅ Dave creates Telegram group "Keiracom Boardroom"
2. ✅ Dave adds Elliot bot to group
3. ✅ Dave creates Gemini bot via @BotFather
4. ✅ Dave disables privacy mode for Gemini bot
5. ✅ Dave gets Gemini API key from Google AI Studio
6. ⏳ Elliot builds minimal bridge service (~50 lines Python)
7. ⏳ Deploy to Railway
8. ⏳ Test basic conversation flow

**Deliverable:** Both AIs can converse in Telegram, Dave can observe and interject.

### Phase 2 — This Week (Read-Only Integration)
**Owner:** Elliot (delegate to sub-agent for MCP server code)
**Effort:** 4-6 hours

1. Set up filesystem MCP server (read-only)
2. Set up Railway MCP server (read-only)
3. Set up Supabase MCP server (read-only)
4. Set up Vercel MCP server (read-only)
5. Connect Gemini bridge to MCP servers
6. Test full context flow

**Deliverable:** Gemini can query any system directly (read-only), no Elliot relay needed.

### Phase 3 — Next Week (Polish)
**Owner:** TBD
**Effort:** 2-4 hours

1. Approval workflow UI (inline buttons for Dave)
2. Audit logging (who said what, what was approved)
3. System prompt refinement for Gemini's role
4. Context window management (prevent bloat)

---

## 8. Safety Guardrails

### 8.1 Execution Control
- **Only Elliot executes.** Gemini proposes, Dave approves, Elliot implements.
- No shell access for Gemini under any circumstances.
- All destructive actions require Dave's explicit approval.

### 8.2 Hallucination Mitigation
- Gemini's access is READ-ONLY — hallucinated commands can't cause damage
- If Gemini proposes something, Elliot verifies feasibility before Dave is asked to approve
- "Verify before amplify" principle

### 8.3 Context Management
- Gemini's context window can bloat quickly
- Implement periodic context summaries
- Dave can trigger `/reset` for either AI if context degrades

### 8.4 Conflict Resolution
If Elliot and Gemini disagree:
1. Both present their case in Boardroom
2. Dave makes final call
3. Loser commits fully to the decision (no passive resistance)

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Dave's relay time | Reduce by 80% |
| Decision quality | Fewer reversals, better first-pass decisions |
| Shipping velocity | Alpha campaign live within 2 weeks |
| Context coherence | Both AIs aligned on project state |

---

## 10. Open Questions (For ADR Tomorrow)

1. Should Gemini have a distinct "persona" defined? (System prompt)
2. How do we handle timezone differences for async collaboration?
3. What's the escalation path if one AI is clearly malfunctioning?
4. Token budget for Gemini API (or is it truly "free" via Max subscription)?

---

## 11. Background: Why This Exists

Dave admitted he's been manually relaying between Gemini and Elliot. This caused:
- Massive token waste (Gemini's context bloating)
- Time drain (Dave as human USB cable)
- Context loss (nuance lost in relay)
- Frustration (for everyone)

The Boardroom solves this by giving both AIs direct communication with human oversight.

---

*Documented by Elliot, 2026-02-04*
*Approved by Dave via Telegram*
