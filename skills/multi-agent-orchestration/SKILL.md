---
name: Multi-Agent Orchestration with Swarm Pattern
description: "Use when: building multi-agent systems, designing agent handoffs, implementing agent coordination, or separating agent concerns"
source: https://github.com/openai/swarm
learned: 2026-01-30
score: 68
---

# Multi-Agent Orchestration (Swarm Pattern)

Lightweight, stateless multi-agent coordination using two primitives: **Agents** and **Handoffs**.

> **Note:** Swarm is now superseded by [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) for production use.

## Core Concepts

### Agent
Encapsulates:
- **Instructions** (system prompt)
- **Functions** (tools)
- Can hand off to another Agent

> Don't just think of agents as "someone who does X"—they can represent workflows, steps, data transformations, or retrieval tasks.

### Handoff
Transfer execution from one agent to another by returning an Agent from a function:

```python
sales_agent = Agent(name="Sales Agent")

def transfer_to_sales():
    return sales_agent

agent = Agent(functions=[transfer_to_sales])
```

## Key Architecture Properties

| Property | Description |
|----------|-------------|
| **Stateless** | No state stored between calls (like Chat Completions API) |
| **Client-side** | Runs entirely on client |
| **Composable** | Agents form networks of "agents", "workflows", "tasks" |

## Execution Loop

```
1. Get completion from current Agent
2. Execute tool calls, append results
3. Switch Agent if necessary
4. Update context variables
5. If no new function calls → return
```

## Context Variables

Pass shared state across agents without embedding in messages:

```python
def instructions(context_variables):
    user_name = context_variables["user_name"]
    return f"Help the user, {user_name}, do whatever they want."

response = client.run(
    agent=agent,
    messages=[{"role": "user", "content": "Hi!"}],
    context_variables={"user_name": "John"}
)
```

## Function Returns

| Return Type | Behavior |
|-------------|----------|
| `str` | Value appended to chat |
| `Agent` | Execution transfers to that Agent |
| `Result` | Can set value + agent + context_variables together |

```python
def talk_to_sales():
    return Result(
        value="Done",
        agent=sales_agent,
        context_variables={"department": "sales"}
    )
```

## Use Cases

Best suited for:
- **Large number of independent capabilities** hard to encode in single prompt
- **Customer service** with specialized agents (triage → sales/support/billing)
- **Complex workflows** with clear handoff points
- **Modular systems** where concerns should be separated

## Design Patterns

### Triage Agent
First agent assesses user intent, hands off to specialized agent:
```
User → Triage Agent → Sales Agent
                    → Support Agent
                    → Billing Agent
```

### Specialist Agents
Each agent handles narrow domain with focused instructions:
- Weather Agent (function: get_weather)
- Personal Shopper (functions: search_products, make_sale, refund)

### Error Recovery
- Function errors append error response to chat
- Agent can recover gracefully
- Multiple function calls execute in order

## Anti-Patterns

1. **Overloading single agent** - defeats the purpose of separation
2. **Circular handoffs** - agents bouncing user back and forth
3. **Stateful assumptions** - forgetting Swarm is stateless between calls
4. **Missing context** - not passing necessary context_variables through handoffs

## Function Schema Auto-Generation

Swarm converts Python functions to JSON Schema automatically:
- Docstrings → function description
- No default → required parameter
- Type hints → parameter type

```python
def greet(name, age: int, location: str = "New York"):
    """Greets the user. Make sure to get their name and age before calling.
    
    Args:
        name: Name of the user.
        age: Age of the user.
        location: Best place on earth.
    """
```

## Key Insight

> Swarm's power comes from its simplicity. Two primitives (Agents + Handoffs) can express rich dynamics between tools and networks of agents.
