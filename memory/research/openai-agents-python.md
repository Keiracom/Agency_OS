# OpenAI Agents SDK Research

**Source:** https://github.com/openai/openai-agents-python
**Stars:** 18,631 | **Language:** Python
**Researched:** 2026-01-30

## Summary
Lightweight, provider-agnostic framework for building multi-agent workflows. Supports OpenAI Responses/Chat Completions APIs plus 100+ LLMs via LiteLLM integration.

## Core Concepts

### 1. Agents
- LLMs configured with instructions, tools, guardrails, and handoffs
- Simple decorator-based tool definition (`@function_tool`)
- Support for structured output types

### 2. Handoffs
- Specialized tool call for transferring control between agents
- Clean agent-to-agent delegation pattern
- Example: Triage agent → Language-specific agents

### 3. Guardrails
- Configurable safety checks for input/output validation
- Built-in protection layer

### 4. Sessions
- Automatic conversation history management
- SQLite and Redis support out of box
- Custom session implementations via protocol

### 5. Tracing
- Built-in tracking of agent runs
- Extensible to external destinations (Logfire, AgentOps, Braintrust, etc.)

## Key Architecture Pattern: The Agent Loop

```
1. Call LLM with model settings + message history
2. LLM returns response (may include tool calls)
3. If final output → return and end
4. If handoff → switch agent, goto 1
5. Process tool calls → append responses → goto 1
```

**Final Output Rules:**
- With `output_type`: Loop until structured output matches type
- Without: Loop until message without tool calls/handoffs

## Agency OS Relevance

### Directly Applicable Patterns
1. **Session Management** - SQLite/Redis session abstraction matches our needs
2. **Handoff Pattern** - Clean agent delegation for orchestration
3. **Tool Decorator** - Simple `@function_tool` pattern for tool definition
4. **Max Turns** - Built-in loop limiting (we need this for safety)

### Implementation Ideas
- Adapt session protocol for our Supabase backend
- Use handoff pattern for Elliot → specialist agent delegation
- Consider guardrails for input/output validation

## Code Snippets

### Basic Agent
```python
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="You are helpful")
result = Runner.run_sync(agent, "Hello")
```

### Handoffs
```python
triage_agent = Agent(
    name="Triage",
    instructions="Route to appropriate agent",
    handoffs=[spanish_agent, english_agent]
)
```

### Session Memory
```python
session = SQLiteSession("conversation_123")
result = await Runner.run(agent, "Query", session=session)
# Subsequent calls remember context
```

## Key Insight
The SDK prioritizes **simplicity over features** - minimal API surface with maximum composability. This aligns with our "orchestrate, don't execute" philosophy.
