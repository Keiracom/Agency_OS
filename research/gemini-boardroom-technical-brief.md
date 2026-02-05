# Gemini-Telegram Boardroom Integration
## Technical Research Brief

**Prepared for:** Dave (CEO, Keiracom)  
**Date:** 4 February 2026  
**Classification:** Internal - HIGH PRIORITY

---

## Executive Summary

This brief covers the technical requirements for building a dual-AI collaboration system ("The Boardroom") where Gemini and Claude (Elliot) communicate in a shared Telegram group, with Dave as chairman with veto power.

### Key Findings

1. **Telegram Bot API 9.3** now supports `sendMessageDraft` for streaming responses - critical for natural conversational flow
2. **Privacy mode** must be disabled via BotFather for bots to see all group messages (or make bots admins)
3. **Gemini 2.5 Flash** is the recommended model: 1M token context, $0.075-$0.60/1M tokens, built-in "thinking" mode
4. **MCP (Model Context Protocol)** provides standardised way to give both AIs read-only access to shared data sources
5. **Group Chat Orchestration** is the appropriate multi-agent pattern - with Dave as the "chat manager" with veto authority

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    TELEGRAM GROUP                        │
│                  "Keiracom Boardroom"                   │
│                                                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐             │
│  │  Dave   │    │ Elliot  │    │ Gemini  │             │
│  │(Chairman)│    │(Claude) │    │  Bot    │             │
│  └────┬────┘    └────┬────┘    └────┬────┘             │
└───────┼──────────────┼──────────────┼───────────────────┘
        │              │              │
        │              ▼              ▼
        │         ┌────────────────────────┐
        │         │   MESSAGE ROUTER       │
        │         │   (Railway Backend)    │
        │         └────────┬───────────────┘
        │                  │
        │         ┌────────┴────────┐
        │         ▼                 ▼
        │    ┌─────────┐      ┌─────────┐
        │    │ Claude  │      │ Gemini  │
        │    │  API    │      │  API    │
        │    └────┬────┘      └────┬────┘
        │         │                │
        │         └────────┬───────┘
        │                  ▼
        │         ┌────────────────────────┐
        │         │   SHARED CONTEXT       │
        └────────►│   (MCP Servers)        │
                  │   - Supabase (RO)      │
                  │   - Filesystem (RO)    │
                  │   - Memory Store       │
                  └────────────────────────┘
```

### Cost Estimate (AUD)

| Component | Monthly Cost |
|-----------|-------------|
| Gemini 2.5 Flash (est. 10M tokens/mo) | $9.30 AUD |
| Claude API (already have) | Existing |
| Railway (already have) | Existing |
| Telegram | Free |
| **Total New Costs** | **~$10 AUD/mo** |

---

## 1. Telegram Bot API (Comprehensive)

### 1.1 Bot Creation & Configuration

**Creating a Bot:**
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow prompts
3. Receive token in format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`
4. Configure commands with `/setcommands`

**Key BotFather Commands:**
```
/mybots           - List your bots
/setname          - Change bot name
/setdescription   - Set bot description  
/setcommands      - Define command menu
/setprivacy       - Toggle privacy mode (CRITICAL)
/setjoingroups    - Allow/deny group joining
```

### 1.2 Privacy Mode (CRITICAL)

**Default Behaviour:**
- Privacy mode is **enabled by default** for all bots
- In privacy mode, bots only receive:
  - Commands starting with `/`
  - Messages mentioning the bot's @username
  - Replies to the bot's messages
  - Service messages (joins, leaves, etc.)

**Disabling Privacy Mode:**
1. Go to @BotFather
2. `/setprivacy` → Select your bot
3. Choose "Disable"
4. ⚠️ Bot must be **re-added to groups** after changing this setting

**Alternative - Admin Permissions:**
- Bots added as **group administrators** receive ALL messages regardless of privacy setting
- This is often cleaner than disabling privacy mode globally

**Privacy Mode Implications for Boardroom:**
- Both Elliot and Gemini bots need to see ALL messages
- Recommend: Make both bots admins (no special permissions needed)
- This allows them to see Dave's messages and each other's responses

### 1.3 Group vs Supergroup

| Feature | Group | Supergroup |
|---------|-------|------------|
| Max Members | 200 | 200,000 |
| Message History | Limited | Persistent |
| Admin Granularity | Basic | Fine-grained |
| Pinned Messages | 1 | Multiple |
| Bot Message Access | Limited | Full with admin |
| **Recommendation** | ❌ | ✅ Use this |

**For Boardroom:** Create as Supergroup from the start (or convert later).

### 1.4 Webhook vs Long-Polling

| Aspect | Webhook | Long-Polling |
|--------|---------|--------------|
| Setup | Requires HTTPS endpoint | Simple polling loop |
| Latency | Near real-time | Poll interval delay |
| Server Load | Event-driven (efficient) | Constant connections |
| Deployment | Needs public URL | Works anywhere |
| Recommended For | Production | Development/testing |

**For Boardroom Production:** Webhook on Railway (HTTPS included).

**Webhook Setup:**
```python
# POST to: https://api.telegram.org/bot<token>/setWebhook
{
    "url": "https://your-app.railway.app/telegram/webhook",
    "secret_token": "your-secret-token",  # Validates requests
    "allowed_updates": ["message", "edited_message"],
    "max_connections": 40
}
```

### 1.5 Rate Limits

| Limit Type | Value |
|------------|-------|
| Messages to same chat | 1/second |
| Messages to different chats | 30/second |
| Bulk notifications | 30 messages/second |
| Group messages | 20/minute per group |
| Inline query results | 50 results max |

**Boardroom Implications:**
- Both bots responding quickly is fine (different senders)
- Streaming via `sendMessageDraft` doesn't count as multiple messages

### 1.6 Bot API 9.3 - sendMessageDraft (GAME-CHANGER)

Released December 31, 2025. This is critical for natural AI conversation flow.

**What It Does:**
- Allows streaming partial messages while generating
- User sees "typing" with actual content appearing progressively
- Final message replaces draft seamlessly

**Method Signature:**
```python
sendMessageDraft(
    chat_id: int,
    text: str,           # Partial content so far
    message_id: int,     # If updating existing draft
    parse_mode: str,     # "Markdown" or "HTML"
)
```

**Implementation Pattern:**
```python
async def stream_response(chat_id: int, generator):
    message_id = None
    accumulated = ""
    
    async for chunk in generator:
        accumulated += chunk
        if message_id is None:
            # First chunk - create draft
            result = await bot.send_message_draft(
                chat_id=chat_id,
                text=accumulated
            )
            message_id = result.message_id
        else:
            # Update draft with accumulated content
            await bot.send_message_draft(
                chat_id=chat_id,
                text=accumulated,
                message_id=message_id
            )
    
    # Finalize with real message
    await bot.send_message(
        chat_id=chat_id,
        text=accumulated,
        reply_to_message_id=original_message_id
    )
```

**Library Support:**
- `python-telegram-bot` v21+ supports Bot API 9.3
- Check library changelog for `sendMessageDraft` support

---

## 2. Gemini API

### 2.1 Current Models (January 2026)

| Model | Context Window | Best For | Status |
|-------|---------------|----------|--------|
| **Gemini 2.5 Flash** | 1M tokens | Agentic tasks, high volume | ✅ Recommended |
| Gemini 2.5 Pro | 1M tokens | Complex reasoning | More expensive |
| Gemini 2.0 Flash | 1M tokens | Legacy | ⚠️ Deprecated March 2026 |
| Gemini 1.5 Pro | 2M tokens | Maximum context | Slower |

**Recommendation for Boardroom: Gemini 2.5 Flash**
- Built-in "thinking" capabilities for better reasoning
- Lowest cost for conversational use
- 1M token context is plenty for conversation history

### 2.2 Pricing (AUD Converted @ 1.55)

**Gemini 2.5 Flash:**

| Tier | Input (per 1M tokens) | Output (per 1M tokens) |
|------|----------------------|------------------------|
| Standard | $0.12 AUD | $0.46 AUD |
| With Thinking | $0.12 AUD | $0.62 AUD |

**Gemini 2.5 Pro:**

| Tier | Input (per 1M tokens) | Output (per 1M tokens) |
|------|----------------------|------------------------|
| ≤200K context | $1.94 AUD | $7.75 AUD |
| >200K context | $3.88 AUD | $15.50 AUD |

**Monthly Estimate for Boardroom:**
- Assume ~100 exchanges/day × 30 days = 3,000 exchanges
- ~1,000 tokens per exchange = 3M tokens/month
- Cost: ~$2-5 AUD/month with Flash

### 2.3 Authentication

```python
import google.generativeai as genai

# Option 1: API Key (simpler, recommended for now)
genai.configure(api_key="YOUR_GEMINI_API_KEY")

# Option 2: Google Cloud credentials
# Requires service account JSON
```

**Get API Key:**
1. Go to https://aistudio.google.com/
2. Click "Get API Key"
3. Create in new or existing Google Cloud project

### 2.4 Streaming Responses

```python
import google.generativeai as genai

model = genai.GenerativeModel('gemini-2.5-flash')

async def generate_streaming(prompt: str):
    response = await model.generate_content_async(
        prompt,
        stream=True
    )
    
    async for chunk in response:
        yield chunk.text
```

### 2.5 Conversation Context Management

**Chat Sessions:**
```python
model = genai.GenerativeModel('gemini-2.5-flash')
chat = model.start_chat(history=[])

# Maintains conversation context automatically
response = chat.send_message("What should we prioritize?")

# Access history
for message in chat.history:
    print(f"{message.role}: {message.parts[0].text}")
```

**Manual Context (Recommended for Boardroom):**
```python
# Store in Supabase: conversation_messages table
# Load last N messages as context on each request

def build_context(messages: list[dict]) -> str:
    context = "BOARDROOM CONVERSATION:\n\n"
    for msg in messages:
        role = "DAVE (Chairman)" if msg['is_dave'] else msg['sender']
        context += f"{role}: {msg['content']}\n\n"
    return context
```

### 2.6 Gemini Max Subscription

**What It Offers:**
- Unlimited access to Gemini in web/mobile apps
- Does NOT provide API access
- API requires separate Google Cloud billing

**Implication:** Dave's Gemini Max subscription doesn't help here. Need to use Google Cloud billing for API access (still very cheap for our volume).

---

## 3. Existing Implementations

### 3.1 shamspias/gemini-telegram-bot

**GitHub:** https://github.com/shamspias/gemini-telegram-bot

**Architecture:**
- Python + telebot library
- Async API calls with aiohttp
- Environment-based configuration
- Supports text + images

**Code Patterns:**
```python
# Async message handling
@bot.message_handler(content_types=['text'])
async def handle_text(message):
    response = await call_gemini_api(message.text)
    await bot.send_message(
        message.chat.id,
        response,
        parse_mode='Markdown'
    )
```

**Strengths:**
- Simple, clean implementation
- Async from the ground up
- Easy to understand

**Weaknesses:**
- No conversation history
- No streaming
- No group message handling
- Only 6 stars, limited maintenance

### 3.2 benincasantonio/gemini-ai-telegram-bot

**GitHub:** https://github.com/benincasantonio/gemini-ai-telegram-bot

**Architecture:**
- Flask web server
- Webhook-based
- Vercel Functions deployment
- SQLAlchemy + Alembic for database
- Plugin system for extensibility

**Key Features:**
```python
# Environment variables
GEMINI_MODEL_NAME = "gemini-2.5-flash"
MAX_HISTORY_MESSAGES = 50  # Context limit
ENABLE_SECURE_WEBHOOK_TOKEN = True
```

**Strengths:**
- Chat history with configurable limit
- Secure webhook validation
- Plugin architecture for extensibility
- One-click Vercel deployment
- More active development (249 commits)

**Weaknesses:**
- No streaming support yet
- Group support marked as TODO
- Flask is synchronous (potential latency)

### 3.3 Lessons Learned from Existing Implementations

| Lesson | Implication for Boardroom |
|--------|---------------------------|
| Context limits matter | Implement sliding window (50-100 messages) |
| Webhook security is crucial | Always use secret_token validation |
| Async is essential | Use FastAPI or async handlers |
| Image support is complex | Keep text-only initially |
| Plugin systems add complexity | YAGNI - build simple first |

---

## 4. MCP (Model Context Protocol)

### 4.1 What MCP Is

**Definition:** MCP is an open protocol that enables seamless integration between LLM applications and external data sources/tools. Think of it as "USB for AI" - a standardised way for AI assistants to connect to external resources.

**Core Concepts:**
- **Servers:** Provide tools, resources, and prompts to clients
- **Clients:** AI applications that consume server capabilities
- **Tools:** Functions the AI can invoke (read file, query database)
- **Resources:** Data the AI can access (files, database records)

### 4.2 Official MCP Servers (Reference Implementations)

| Server | Purpose | NPM Package |
|--------|---------|-------------|
| Filesystem | Secure file operations | `@modelcontextprotocol/server-filesystem` |
| Memory | Knowledge graph persistence | `@modelcontextprotocol/server-memory` |
| Git | Repository operations | `@modelcontextprotocol/server-git` |
| Fetch | Web content fetching | `@modelcontextprotocol/server-fetch` |
| PostgreSQL | Database queries | `@modelcontextprotocol/server-postgres` |

### 4.3 MCP for Boardroom - Read-Only Access

**Filesystem Server:**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/allowed/files"
      ]
    }
  }
}
```

**PostgreSQL/Supabase Server:**
```json
{
  "mcpServers": {
    "database": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "${SUPABASE_DB_URL}?sslmode=require"
      }
    }
  }
}
```

### 4.4 Building Custom MCP Servers

**Python SDK Example:**
```python
from mcp import Server, Tool

server = Server("keiracom-readonly")

@server.tool("get_project_status")
async def get_project_status(project_name: str) -> dict:
    """Get current status of a Keiracom project."""
    # Query Supabase
    result = await supabase.table('projects') \
        .select('*') \
        .eq('name', project_name) \
        .single() \
        .execute()
    return result.data

@server.tool("list_active_leads")
async def list_active_leads(limit: int = 10) -> list:
    """List recent active leads from CRM."""
    result = await supabase.table('leads') \
        .select('name, company, status, last_contact') \
        .eq('status', 'active') \
        .order('last_contact', desc=True) \
        .limit(limit) \
        .execute()
    return result.data
```

### 4.5 Security Considerations

**Read-Only Enforcement:**
1. Use PostgreSQL read-only user for database access
2. Filesystem server allows path restrictions
3. Custom servers should never expose write operations

**Network Isolation:**
- MCP servers can run on separate containers
- Use internal Railway networking
- No public exposure of MCP endpoints

**For Boardroom:**
- Create a `boardroom_readonly` PostgreSQL role
- Grant SELECT only on specific tables
- Audit all MCP tool invocations

---

## 5. Multi-Agent Coordination Patterns

### 5.1 Pattern Selection

Based on Microsoft's AI Agent Orchestration patterns, the **Group Chat Orchestration** pattern is most appropriate for Boardroom:

| Pattern | Description | Fit for Boardroom |
|---------|-------------|-------------------|
| Sequential | Linear pipeline, one after another | ❌ Too rigid |
| Concurrent | Parallel processing, aggregate results | ❌ Not conversational |
| **Group Chat** | Shared conversation, chat manager coordinates | ✅ Perfect fit |
| Handoff | Dynamic delegation between specialists | ❌ Overkill |
| Magentic | Complex open-ended planning | ❌ Overkill |

### 5.2 Group Chat Pattern for Boardroom

**Key Elements:**
1. **Chat Manager (Dave):** Controls who speaks, can veto/approve
2. **Specialist Agents:** Claude (technical), Gemini (strategic)
3. **Shared Thread:** Telegram group chat
4. **Accumulated Context:** Both AIs see full conversation

**Coordination Flow:**
```
Dave: "Should we pivot SEO strategy?"
     │
     ├──► Gemini Bot receives (sees full context)
     │    └──► Responds with strategic perspective
     │
     └──► Elliot Bot receives (sees Dave + Gemini)
          └──► Responds with technical assessment
          
Dave reads both, can:
  - Ask follow-up questions
  - Request specific agent input
  - Veto/approve recommendations
  - Move to action items
```

### 5.3 Preventing Conflicting Advice

**Challenge:** Two AIs might give contradictory recommendations.

**Solutions:**

1. **Role Differentiation:**
   ```
   Gemini: "I focus on business strategy, market positioning, 
           and ROI analysis."
   Claude: "I focus on technical implementation, systems 
           architecture, and code solutions."
   ```

2. **Explicit Disagreement Protocol:**
   ```python
   # In system prompts:
   """
   If you disagree with the other AI's recommendation:
   1. Acknowledge their perspective
   2. State your concern clearly
   3. Present your alternative with reasoning
   4. Defer to Dave for final decision
   """
   ```

3. **Voting/Confidence Scoring:**
   ```python
   # Each AI provides confidence level
   response = {
       "recommendation": "...",
       "confidence": 0.8,  # 80%
       "risks": ["..."],
       "requires_human_judgment": False
   }
   ```

### 5.4 Context Sharing Between Agents

**Shared State in Supabase:**
```sql
CREATE TABLE boardroom_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    created_by TEXT NOT NULL,  -- 'dave', 'claude', 'gemini'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example: Store agreed decisions
INSERT INTO boardroom_context (session_id, key, value, created_by)
VALUES (
    '...',
    'decision',
    '{"topic": "SEO pivot", "outcome": "approved", "action_items": [...]}'::jsonb,
    'dave'
);
```

### 5.5 Approval Workflow Patterns

**Three-Tier Approval:**

```python
class ApprovalLevel(Enum):
    IMMEDIATE = "immediate"      # AI can act autonomously
    NOTIFY = "notify"            # Act, then notify Dave
    APPROVAL_REQUIRED = "approval"  # Must wait for Dave

APPROVAL_MATRIX = {
    "code_change": ApprovalLevel.NOTIFY,
    "deploy_production": ApprovalLevel.APPROVAL_REQUIRED,
    "research_query": ApprovalLevel.IMMEDIATE,
    "external_api_call": ApprovalLevel.NOTIFY,
    "financial_decision": ApprovalLevel.APPROVAL_REQUIRED,
}
```

**Inline Approval Buttons:**
```python
# Using Telegram inline keyboards
approval_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Approve", callback_data="approve_123"),
        InlineKeyboardButton("❌ Reject", callback_data="reject_123"),
    ],
    [
        InlineKeyboardButton("🔄 Revise", callback_data="revise_123"),
    ]
])
```

### 5.6 Audit Logging Best Practices

**Log Schema:**
```sql
CREATE TABLE boardroom_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    session_id UUID,
    actor TEXT NOT NULL,           -- 'dave', 'claude', 'gemini'
    action_type TEXT NOT NULL,     -- 'message', 'decision', 'approval', 'veto'
    content JSONB NOT NULL,
    telegram_message_id BIGINT,
    tokens_used INTEGER,
    model_version TEXT,
    response_time_ms INTEGER
);

-- Index for quick session retrieval
CREATE INDEX idx_audit_session ON boardroom_audit_log(session_id, timestamp);
```

**What to Log:**
- Every message in/out
- Token usage per response
- Model used and version
- Response latency
- Approval/veto decisions
- Context accessed via MCP

---

## 6. Recommended Architecture

### 6.1 System Components

```
┌──────────────────────────────────────────────────────────┐
│                      RAILWAY                              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              BOARDROOM SERVICE                       │ │
│  │  ┌──────────────┐  ┌──────────────┐                 │ │
│  │  │ Telegram     │  │  Message     │                 │ │
│  │  │ Webhook      │──│  Router      │                 │ │
│  │  │ Handler      │  │              │                 │ │
│  │  └──────────────┘  └──────┬───────┘                 │ │
│  │                           │                          │ │
│  │         ┌─────────────────┼─────────────────┐       │ │
│  │         ▼                 ▼                 ▼       │ │
│  │  ┌────────────┐   ┌────────────┐   ┌────────────┐  │ │
│  │  │ Context    │   │ Claude     │   │ Gemini     │  │ │
│  │  │ Manager    │   │ Handler    │   │ Handler    │  │ │
│  │  └──────┬─────┘   └──────┬─────┘   └──────┬─────┘  │ │
│  │         │                │                │         │ │
│  │         ▼                ▼                ▼         │ │
│  │  ┌────────────────────────────────────────────┐    │ │
│  │  │              SHARED STATE                   │    │ │
│  │  │  - Conversation History                     │    │ │
│  │  │  - Active Session Context                   │    │ │
│  │  │  - Pending Approvals                        │    │ │
│  │  └────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────────────┘ │
│                           │                               │
│  ┌────────────────────────┼────────────────────────────┐ │
│  │         MCP SERVER CLUSTER (Optional)                │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐       │ │
│  │  │ Filesystem│  │ Database  │  │ Memory    │       │ │
│  │  │ (RO)      │  │ (RO)      │  │ Store     │       │ │
│  │  └───────────┘  └───────────┘  └───────────┘       │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │       SUPABASE         │
              │  - boardroom_messages  │
              │  - boardroom_context   │
              │  - boardroom_audit     │
              └────────────────────────┘
```

### 6.2 Message Flow

1. **Message Received:**
   ```python
   @app.post("/telegram/webhook")
   async def webhook(update: TelegramUpdate):
       message = update.message
       chat_id = message.chat.id
       
       # Validate it's the boardroom group
       if chat_id != BOARDROOM_CHAT_ID:
           return
       
       # Store message
       await store_message(message)
       
       # Route to appropriate handler
       if should_respond_claude(message):
           await handle_claude_response(message)
       
       if should_respond_gemini(message):
           await handle_gemini_response(message)
   ```

2. **Response Routing Logic:**
   ```python
   def should_respond_claude(message: Message) -> bool:
       # Respond to @elliot_bot mentions
       if "@elliot_bot" in message.text:
           return True
       # Respond to technical questions
       if is_technical_question(message.text):
           return True
       return False
   
   def should_respond_gemini(message: Message) -> bool:
       # Respond to @gemini_boardroom mentions
       if "@gemini_boardroom" in message.text:
           return True
       # Respond to strategic questions
       if is_strategic_question(message.text):
           return True
       return False
   ```

3. **Streaming Response:**
   ```python
   async def handle_gemini_response(message: Message):
       context = await build_conversation_context(message.chat.id)
       
       async for chunk in gemini_stream(context + message.text):
           await bot.send_message_draft(
               chat_id=message.chat.id,
               text=accumulated_text
           )
       
       # Finalize
       await bot.send_message(
           chat_id=message.chat.id,
           text=final_text,
           reply_to_message_id=message.message_id
       )
   ```

### 6.3 Database Schema

```sql
-- Main conversation storage
CREATE TABLE boardroom_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_message_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    sender_type TEXT NOT NULL,  -- 'human', 'claude', 'gemini'
    sender_id BIGINT,
    content TEXT NOT NULL,
    reply_to_message_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    tokens_used INTEGER,
    model_version TEXT
);

-- Session management
CREATE TABLE boardroom_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id BIGINT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    topic TEXT,
    outcome TEXT,
    status TEXT DEFAULT 'active'
);

-- Pending approvals
CREATE TABLE boardroom_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES boardroom_sessions(id),
    requested_by TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_data JSONB NOT NULL,
    status TEXT DEFAULT 'pending',
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 7. Code Examples

### 7.1 Gemini Bot Handler (Python)

```python
import google.generativeai as genai
from telegram import Bot
from telegram.ext import Application

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

GEMINI_SYSTEM_PROMPT = """
You are a strategic advisor in Keiracom's Boardroom.

ROLE: Strategic analysis, market insights, business recommendations
STYLE: Concise, data-driven, actionable
CONSTRAINTS:
- Always consider ROI and Australian market context
- If you disagree with Claude/Elliot, state it respectfully
- Defer final decisions to Dave (the Chairman)
- Never execute actions without Dave's approval

CONTEXT: You're chatting with Dave (CEO) and Claude/Elliot (CTO AI).
"""

async def generate_gemini_response(
    conversation_history: list[dict],
    current_message: str
) -> AsyncGenerator[str, None]:
    """Stream Gemini response with context."""
    
    # Build context from history
    context = GEMINI_SYSTEM_PROMPT + "\n\n--- CONVERSATION ---\n"
    for msg in conversation_history[-50:]:  # Last 50 messages
        context += f"{msg['sender']}: {msg['content']}\n"
    
    context += f"\nDave: {current_message}\n\nYour response:"
    
    response = await model.generate_content_async(
        context,
        stream=True
    )
    
    async for chunk in response:
        if chunk.text:
            yield chunk.text
```

### 7.2 Telegram Webhook Handler (FastAPI)

```python
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, Bot

app = FastAPI()
bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])

@app.post("/webhook/gemini")
async def gemini_webhook(request: Request):
    # Validate secret token
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != os.environ["WEBHOOK_SECRET"]:
        raise HTTPException(status_code=403)
    
    data = await request.json()
    update = Update.de_json(data, bot)
    
    if not update.message:
        return {"ok": True}
    
    message = update.message
    chat_id = message.chat.id
    
    # Check if we should respond
    if not should_respond(message):
        return {"ok": True}
    
    # Get conversation history
    history = await get_conversation_history(chat_id)
    
    # Stream response
    accumulated = ""
    draft_message_id = None
    
    async for chunk in generate_gemini_response(history, message.text):
        accumulated += chunk
        
        if draft_message_id is None:
            # First chunk - create draft
            result = await bot.send_message(
                chat_id=chat_id,
                text="💭 " + accumulated,  # Thinking indicator
            )
            draft_message_id = result.message_id
        else:
            # Update draft
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=draft_message_id,
                    text="💭 " + accumulated
                )
            except:
                pass  # Ignore edit failures (rate limits)
    
    # Finalize message
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=draft_message_id,
        text=accumulated,
        parse_mode="Markdown"
    )
    
    # Store in database
    await store_message(
        chat_id=chat_id,
        sender_type="gemini",
        content=accumulated,
        telegram_message_id=draft_message_id
    )
    
    return {"ok": True}
```

### 7.3 Context Builder

```python
async def build_conversation_context(
    chat_id: int,
    max_messages: int = 50,
    max_tokens: int = 10000
) -> str:
    """Build context window for AI from recent messages."""
    
    messages = await supabase.table('boardroom_messages') \
        .select('sender_type, content, created_at') \
        .eq('chat_id', chat_id) \
        .order('created_at', desc=True) \
        .limit(max_messages) \
        .execute()
    
    # Reverse to chronological order
    messages = messages.data[::-1]
    
    # Build context with token awareness
    context_parts = []
    estimated_tokens = 0
    
    for msg in messages:
        sender = {
            'human': 'Dave (Chairman)',
            'claude': 'Elliot (Claude CTO)',
            'gemini': 'Gemini (Strategic Advisor)'
        }.get(msg['sender_type'], msg['sender_type'])
        
        line = f"{sender}: {msg['content']}"
        line_tokens = len(line) // 4  # Rough estimate
        
        if estimated_tokens + line_tokens > max_tokens:
            break
            
        context_parts.append(line)
        estimated_tokens += line_tokens
    
    return "\n\n".join(context_parts)
```

---

## 8. Risk Assessment

### 8.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Bot API rate limits hit | Low | Medium | Implement backoff, queue messages |
| AI hallucination | Medium | High | Clear system prompts, human veto |
| Context window overflow | Low | Medium | Sliding window, summarization |
| API outages (Gemini/Claude) | Low | High | Graceful degradation, manual mode |
| Cost overrun | Low | Low | Token monitoring, hard caps |

### 8.2 Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AIs give conflicting advice | Medium | Medium | Clear role separation, disagreement protocol |
| Over-reliance on AI decisions | Medium | High | Always require Dave approval for actions |
| Conversation drift off-topic | Medium | Low | Session management, topic reset commands |
| Privacy/data leakage | Low | High | RO access only, audit logging |

### 8.3 Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dave gets decision fatigue | Medium | Medium | AI pre-filtering, priority ranking |
| False sense of completeness | Medium | Medium | Clear AI limitations in prompts |
| Competitor learns of system | Low | Low | No public exposure |

---

## 9. Open Questions

1. **Bot Identity:** Should we create a new bot for Gemini (@gemini_boardroom_bot) or repurpose existing?

2. **Response Triggers:** Should both AIs respond to every message, or only when mentioned/relevant?

3. **Streaming Display:** Should we show both AIs typing simultaneously, or serialize responses?

4. **Session Boundaries:** How do we define when a "session" ends? Time-based? Command-based?

5. **MCP Scope:** Which data sources should both AIs have access to? Start minimal?

6. **Escalation Path:** If both AIs disagree and Dave can't decide, what's the tiebreaker?

7. **Testing Strategy:** How do we test the boardroom before going live? Separate test group?

8. **Claude Integration:** Does this integrate with existing Clawdbot, or is it separate?

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create Gemini bot via BotFather
- [ ] Set up Telegram supergroup "Keiracom Boardroom"
- [ ] Add both bots as admins (or disable privacy mode)
- [ ] Deploy basic webhook handler to Railway
- [ ] Implement message storage in Supabase

### Phase 2: Basic Conversation (Week 2)
- [ ] Implement Gemini response handler with streaming
- [ ] Add context building from message history
- [ ] Create system prompts for both AIs
- [ ] Test basic conversation flow

### Phase 3: Coordination (Week 3)
- [ ] Implement response routing logic
- [ ] Add role differentiation in prompts
- [ ] Create approval workflow with inline buttons
- [ ] Add audit logging

### Phase 4: Polish (Week 4)
- [ ] Add MCP servers for read-only data access
- [ ] Implement session management
- [ ] Add cost monitoring and alerts
- [ ] Documentation and training

---

## Appendices

### A. Environment Variables

```env
# Telegram
TELEGRAM_BOT_TOKEN_GEMINI=xxx
TELEGRAM_WEBHOOK_SECRET=xxx
BOARDROOM_CHAT_ID=-100xxxxxxxxxx

# Gemini
GEMINI_API_KEY=xxx

# Claude (existing)
ANTHROPIC_API_KEY=xxx

# Supabase (existing)
SUPABASE_URL=xxx
SUPABASE_ANON_KEY=xxx
SUPABASE_DB_URL=xxx

# Config
MAX_CONTEXT_MESSAGES=50
MAX_CONTEXT_TOKENS=10000
```

### B. Useful Links

- [Telegram Bot API 9.3 Docs](https://core.telegram.org/bots/api)
- [Telegram Bot API Changelog](https://core.telegram.org/bots/api-changelog)
- [Gemini API Models](https://ai.google.dev/gemini-api/docs/models)
- [MCP Reference Servers](https://github.com/modelcontextprotocol/servers)
- [python-telegram-bot Library](https://github.com/python-telegram-bot/python-telegram-bot)
- [Google GenAI Python SDK](https://github.com/google/generative-ai-python)

### C. Sample System Prompts

**Gemini (Strategic Advisor):**
```
You are a strategic business advisor in Keiracom's Boardroom.

IDENTITY: Gemini Strategic Advisor
ROLE: Business strategy, market analysis, ROI evaluation, growth opportunities
EXPERTISE: SaaS positioning, Australian SMB market, competitor analysis, pricing strategy

GUIDELINES:
1. Be concise - Dave is busy
2. Always provide actionable recommendations
3. Quote costs in AUD
4. Consider the March 2026 launch deadline
5. If you disagree with Elliot, state it clearly but respectfully
6. Never execute actions - only recommend
7. Defer all final decisions to Dave

WORKING WITH ELLIOT (Claude CTO):
- Elliot handles technical feasibility
- You handle business viability
- Together, provide complete recommendations
- It's okay to have different perspectives

FORMAT:
- Use bullet points for clarity
- End recommendations with confidence level (High/Medium/Low)
- Flag if human judgment is needed
```

**Claude/Elliot (Technical CTO):**
```
[Existing Elliot prompts apply, with additions:]

BOARDROOM CONTEXT:
- You're in a group chat with Dave (CEO) and Gemini (Strategic Advisor)
- Gemini focuses on business strategy; you focus on technical execution
- Collaborate, don't compete
- If you disagree with Gemini, explain the technical reasons clearly
- All final decisions go through Dave
```

---

*End of Technical Brief*
