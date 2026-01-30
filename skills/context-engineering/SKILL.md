---
name: Context Engineering for AI Agents
description: "Use when: building agents, optimizing prompts, managing long-running tasks, dealing with context limits, or designing tool systems"
source: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
learned: 2026-01-30
score: 100
---

# Context Engineering for AI Agents

Context engineering is the evolution of prompt engineering—managing the **entire context state** (system prompts, tools, MCP, external data, message history) rather than just crafting prompts.

## Core Principle

> Find the smallest possible set of high-signal tokens that maximize the likelihood of desired outcome.

Context is a **finite resource with diminishing returns**. LLMs have an "attention budget" that depletes with each token due to transformer architecture's n² pairwise relationships.

## The Anatomy of Effective Context

### System Prompts
Find the **Goldilocks altitude**:
- ❌ Too specific: Brittle if-else hardcoded logic
- ❌ Too vague: Assumes shared context that doesn't exist
- ✅ Just right: Specific enough to guide, flexible enough for heuristics

**Structure with clear sections:**
- `<background_information>`
- `<instructions>`
- `## Tool guidance`
- `## Output description`

### Tools
- Self-contained, robust to error, extremely clear on intended use
- **Minimal viable toolset** - avoid ambiguity about which tool to use
- If a human can't definitively say which tool, the agent can't either
- Return token-efficient information

### Examples (Few-Shot)
- Curate **diverse, canonical examples** portraying expected behavior
- ❌ Don't stuff laundry lists of edge cases
- ✅ Examples are "pictures worth a thousand words"

## Context Retrieval Strategies

### Just-in-Time Context
Instead of pre-loading all data:
1. Maintain lightweight identifiers (file paths, stored queries, URLs)
2. Dynamically load data at runtime using tools
3. Leverage progressive disclosure - let agent discover context through exploration

**Example:** Claude Code uses `grep`, `head`, `tail` to analyze large databases without loading full data into context.

### Hybrid Strategy
- Pre-retrieve some data for speed
- Allow autonomous exploration at agent's discretion
- `CLAUDE.md` files dropped in upfront + `glob`/`grep` for just-in-time navigation

## Long-Horizon Techniques

### 1. Compaction
Summarize context nearing window limit, reinitiate with summary:
- Preserve: architectural decisions, unresolved bugs, implementation details
- Discard: redundant tool outputs, stale messages
- **Safest light-touch:** Clear old tool call results

### 2. Structured Note-Taking (Agentic Memory)
Agent writes notes persisted **outside context window**, pulled back when needed:
- TODO lists
- `NOTES.md` files
- Progress tracking across complex tasks

**Example:** Claude playing Pokémon maintains precise tallies across thousands of steps, strategic notes, maps of explored regions.

### 3. Sub-Agent Architectures
- Main agent coordinates with high-level plan
- Sub-agents handle focused tasks with **clean context windows**
- Each sub-agent may use tens of thousands of tokens but returns only 1,000-2,000 token summary

**When to use:**
| Technique | Best For |
|-----------|----------|
| Compaction | Tasks requiring extensive back-and-forth |
| Note-taking | Iterative development with clear milestones |
| Multi-agent | Complex research, parallel exploration |

## Anti-Patterns

1. **Context rot** - accuracy decreases as tokens increase
2. **Bloated toolsets** with overlapping functionality
3. **Exhaustive edge case prompts** instead of good examples
4. **Pre-loading everything** instead of just-in-time retrieval
5. **Aggressive compaction** losing subtle but critical context

## Key Insight

> As models improve, the level of autonomy scales. "Do the simplest thing that works" remains the best advice.
