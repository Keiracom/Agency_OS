# Phase 6: Agents (Pydantic AI)

**Status:** ✅ Complete  
**Tasks:** 4  
**Dependencies:** Phase 5 complete

---

## Overview

Create AI agents using Pydantic AI framework for intelligent decision-making.

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| AGT-001 | Base agent | Pydantic AI base | `src/agents/base_agent.py` | M |
| AGT-002 | CMO agent | Orchestration decisions | `src/agents/cmo_agent.py` | L |
| AGT-003 | Content agent | Copy generation | `src/agents/content_agent.py` | M |
| AGT-004 | Reply agent | Intent classification | `src/agents/reply_agent.py` | M |

---

## Agent Responsibilities

### CMO Agent
- Campaign strategy decisions
- Channel mix optimization
- Budget allocation recommendations
- Performance analysis

### Content Agent
- Email subject lines
- Email body copy
- SMS messages
- LinkedIn messages
- Personalization

### Reply Agent
- Intent classification (meeting_request, interested, question, not_interested, etc.)
- Sentiment analysis
- Response suggestions
- Escalation routing

---

## Pydantic AI Pattern

```python
from pydantic_ai import Agent

class ContentAgent(Agent):
    """Generate personalized outreach content."""
    
    model = "claude-3-sonnet"
    
    @tool
    async def get_lead_context(self, lead_id: UUID) -> LeadContext:
        """Retrieve lead information for personalization."""
        ...
    
    async def generate_email(
        self, 
        lead_id: UUID, 
        template_type: str
    ) -> EmailContent:
        """Generate personalized email content."""
        context = await self.get_lead_context(lead_id)
        return await self.run(
            f"Generate {template_type} email for {context}"
        )
```

---

## Intent Types

```python
class IntentType(Enum):
    MEETING_REQUEST = "meeting_request"
    INTERESTED = "interested"
    QUESTION = "question"
    NOT_INTERESTED = "not_interested"
    UNSUBSCRIBE = "unsubscribe"
    OUT_OF_OFFICE = "out_of_office"
    AUTO_REPLY = "auto_reply"
```

---

## Technology Choice

**Use:** Pydantic AI  
**NOT:** LangChain, CrewAI, custom agents

Rationale: Type-safe validation, contract enforcement, simpler patterns.
