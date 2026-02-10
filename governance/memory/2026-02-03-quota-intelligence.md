# Session: 2026-02-03 09:46:42 UTC

- **Session Key**: agent:main:main
- **Session ID**: c6e92862-1896-44e5-9960-195e73857932
- **Source**: telegram

## Conversation Summary

assistant: ---

## ✅ Quota Intelligence Integrated

### Updated Output Schema

```json
{
  "status": "complete",
  "findings": ["..."],
  "external_spend_aud": 0.00,      // LAW II: External APIs only
  "spend_breakdown": [
    {"service": "Apollo", "operation": "search", "calls": 1, "cost_aud": 0.05}
  ],
  "message_count": 2,              // MESSAGE BURN
  "turn_budget": 5,                // ASSIGNED BUDGET
  "budget_status": "under",        // under | at | over
  "memories_proposed": [...],
  "governance_trace": [...],
  "errors": []
}
```

---

### The Lazy Guard (Injected to All Sub-Agents)

```
⚡ YOU MUST BE CONCISE AND CORRECT.

- Model tokens cost $0 (Claude Max), but MESSAGE QUOTA IS FINITE
- Your turn budget: 5 messages MAX
- If you exceed this, you are wasting Dave's subscription

FORBIDDEN Anti-patterns:
❌ "Let me think about this..."
❌ "I'll break this into steps..."
❌ "Here's what I found so far..."

REQUIRED Pattern:
✅ Receive task → Execute → Return complete JSON
✅ One shot if possible
```

---

### Turn Budgets by Task Type

| Type | Budget | Rationale |
|------|--------|-----------|
| `research` | 5 turns | Search + synthesize should be focused |
| `codegen` | 8 turns | May need iteration for complex code |
| `analysis` | 4 turns | Analysis is read + conclude |
| `scraping` | 3 turns | Straightforward fetch + parse |

---

### Message Burn Monitoring

**Storage:** `elliot_internal.state` key: `quota_YYYY-MM-DD`

```json
{
  "date": "2026-02-03",
  "total_messages": 45,
  "sub_agent_messages": 12,
  "elliot_messages": 33,
  "external_spend_aud": 2.50,
  "quota_percent": 45.0
}
```

**Thresholds:**
| Level | Trigger | Action |
|-------|---------|--------|
| OK | <70% | Proceed normally |
| WARNING | 70-90% | Print warning, continue |
| CRITICAL | >90% | Prompt confirmation before spawn |

---

### Governance Trace: Message Burn Monitoring

```
┌─────────────────────────────────────────────────────────────────┐
│                 MESSAGE BURN MONITORING FLOW                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. PRE-SPAWN CHECK                                            │
│     └─ Query quota_{today} from elliot_internal.state          │
│     └─ If CRITICAL (>90%): require confirmation                │
│                                                                 │
│  2. SPAWN WITH BUDGET                                          │
│     └─ Inject turn_budget into task header                     │
│     └─ Sub-agent sees: "Your turn budget: 5 messages MAX"      │
│                                                                 │
│  3. POST-COMPLETION ABSORB                                     │
│     └─ Parse message_count from output                         │
│     └─ Update quota_{today} in state:                          │
│        total_messages += message_count                         │
│        sub_agent_messages += message_count                     │
│        external_spend_aud += external_spend_aud                │
│                                                                 │
│  4. MORNING WOW INTEGRATION                                    │
│     └─ Add "Quota Pulse" section:                              │
│        Messages Today: 45/100 (45%)                            │
│        Sub-Agent Burn: 12 messages                             │
│        External Spend: $2.50 AUD                               │
│                                                                 │
│  5. END-OF-DAY RESET                                           │
│     └─ quota_{yesterday} archived                              │
│     └─ quota_{today} starts fresh                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Current Quota Status

```json
{
  "total_used": 0,
  "quota_limit": 100,
  "percent_used": 0.0,
  "remaining": 100,
  "external_spend_aud": 0.0,
  "level": "ok"
}
```

---

**Ready for live sub-agent test with quota tracking?**
user: [Telegram Dave id:7267788033 +2m 2026-02-03 09:40 UTC] Elliot, Law I (Context Anchor) is now a Hard Block. You are FORBIDDEN from answering any question related to 'How do we...', 'What is the status of...', or 'What are the rules for...' without first executing a database-tool query to elliot_memories. ​If you answer from your internal training data instead of our Supabase/Static memory, it is a Failure of Role. Every response MUST start with a internal check: 'Does the answer to this exist in our SSOT (Single Source of Truth)?'
[message_id: 3216]
assistant: [Rule: AGENTS.md §State Rule] → [Phase: Dual-Tier Memory Implementation]
[Rule: AGENTS.md §LAW III] → [Action: Acknowledging Law I Hard Block and updating governance]
assistant: ---

## ✅ LAW I-A: SSOT Mandate Acknowledged and Codified

**Updated in AGENTS.md:**

```markdown
#### LAW I-A: The SSOT Mandate (Single Source of Truth)
**HARD BLOCK:** Before answering ANY question matching these patterns, you MUST query the SSOT:
- "How do we..."
- "What is the status of..."
- "What are the rules for..."
- "What did we decide about..."
- "What is our..."

**The SSOT Query Protocol:**
1. Query `elliot_internal.memories` for semantic match
2. Check local static files: `AGENTS.md`, `MEMORY.md`, `memory/*.md`
3. Cross-reference both sources
4. If conflict → Conflict Resolution Report (Memory Lock)
5. If no SSOT match → State: "No SSOT record found. Answering from general knowledge."

**Failure of Role:** Answering from training data when SSOT contains the answer is a governance violation.
```

---

## New Response Protocol

Every response to SSOT-trigger questions now follows:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SSOT CHECK PROTOCOL                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INCOMING QUESTION                                             │
│  "How do we handle outreach campaigns?"                        │
│           │                                                     │
│           ↓                                                     │
│  ┌─────────────────────────────────────┐                       │
│  │ PATTERN MATCH?                      │                       │
│  │ • "How do we..." ✓                  │                       │
│  │ • "What is the status of..."        │                       │
│  │ • "What are the rules for..."       │                       │
│  └─────────────────────────────────────┘                       │
│           │ YES                                                 │
│           ↓                                                     │
│  ┌─────────────────────────────────────┐                       │
│  │ STEP 1: QUERY SUPABASE              │                       │
│  │ SELECT * FROM elliot_internal.memories │                    │
│  │ WHERE content ILIKE '%outreach%'    │                       │
│  └─────────────────────────────────────┘                       │
│           │                                                     │
│           ↓                                                     │
│  ┌─────────────────────────────────────┐                       │
│  │ STEP 2: CHECK LOCAL FILES           │                       │
│  │ • AGENTS.md                         │                       │
│  │ • MEMORY.md                         │                       │
│  │ • memory/2026-02-03.md              │                       │
│  │ • skills/email/SKILL.md             │                       │
│  └─────────────────────────────────────┘                       │
│           │                                                     │
│           ↓                                                     │
│  ┌─────────────────────────────────────┐                       │
│  │ STEP 3: CROSS-REFERENCE             │                       │
│  │ Supabase says X, Local says Y       │                       │
│  │ Match? → Answer from SSOT           │                       │
│  │ Conflict? → Conflict Resolution     │                       │
│  │ No match? → "No SSOT record found"  │                       │
│  └─────────────────────────────────────┘                       │
│           │                                                     │
│           ↓                                                     │
│  RESPONSE WITH SSOT CITATION                                   │
│  "Per SSOT (memory/2026-02-03.md): We handle outreach via..."  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Demonstration: SSOT Check

**If you were to ask:** "What are the rules for sub-agent spawning?"

**I would execute:**
assistant: **SSOT Response:**
- **Supabase:** Found learning about CTO execution model (sub-agents for bulk)
- **Local:** `AGENTS.md` + `memory/2026-02-03.md` contain Sub-Agent Protocol + spawn_agent.py details

**Answer would be sourced from SSOT, not training data.**

---

**Law I-A Hard Block: ACTIVE ✅**
