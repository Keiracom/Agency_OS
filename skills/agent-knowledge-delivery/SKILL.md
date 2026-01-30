---
name: Agent Knowledge Delivery - AGENTS.md vs Skills
description: "Use when: designing how to provide documentation to agents, building AGENTS.md files, deciding between passive context vs active retrieval"
source: https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
learned: 2026-01-30
score: 52
---

# Agent Knowledge Delivery: Passive Context vs Active Retrieval

Vercel's eval findings on teaching coding agents framework-specific knowledge.

## Key Finding

| Approach | Pass Rate |
|----------|-----------|
| Baseline (no docs) | 53% |
| Skills (default) | 53% (+0pp) |
| Skills + explicit instructions | 79% (+26pp) |
| **AGENTS.md docs index** | **100%** (+47pp) |

> A compressed 8KB docs index in AGENTS.md achieved 100% pass rate, while skills maxed at 79% even with explicit instructions.

## Why Passive Context Wins

### 1. No Decision Point
With AGENTS.md, there's no moment where agent must decide "should I look this up?" Information is already present.

### 2. Consistent Availability
Skills load asynchronously and only when invoked. AGENTS.md content is in system prompt for every turn.

### 3. No Ordering Issues
Skills create sequencing decisions (read docs first vs explore project first). Passive context avoids this entirely.

## The Skills Problem

In 56% of eval cases, skills were never invoked. Agents not reliably using available tools is a **known limitation** of current models.

### Instruction Wording Fragility

| Instruction | Behavior | Outcome |
|-------------|----------|---------|
| "You MUST invoke the skill" | Reads docs first, anchors on patterns | Misses project context |
| "Explore project first, then invoke skill" | Builds mental model first | Better results |

Same skill, same docs, different outcomes based on subtle wording changes.

## Compression Strategy

Initial docs injection: ~40KB
Compressed format: **8KB** (80% reduction)
Pass rate maintained: **100%**

### Format Example
```
[Next.js Docs Index]|root: ./.next-docs
|IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning
|01-app/01-getting-started:{01-installation.mdx,02-project-structure.mdx,...}
|01-app/02-building-your-application/01-routing:{01-defining-routes.mdx,...}
```

Agent knows where to find docs without full content in context. Reads specific files when needed.

## Critical Instruction

```
IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning
for any [Framework] tasks.
```

This tells agent to consult docs rather than rely on potentially outdated training data.

## When to Use Each

### AGENTS.md (Passive Context)
Best for: **Broad, horizontal improvements** across all tasks
- Framework knowledge
- Project conventions
- API documentation indexes
- Always-available guidance

### Skills (Active Retrieval)
Best for: **Vertical, action-specific workflows** that users explicitly trigger
- "Upgrade my Next.js version"
- "Migrate to App Router"
- "Apply framework best practices"
- Complex multi-step operations

## Implementation Guidelines

### For AGENTS.md
1. **Compress aggressively** - Index pointing to files works as well as full docs
2. **Include retrieval instruction** - Override pre-training bias
3. **Match project version** - Docs should reflect actual project state

### For Skills
1. Add explicit invocation instructions to AGENTS.md
2. Use "explore first, then invoke" pattern
3. Test with evals targeting APIs not in training data

## Anti-Patterns

1. **Waiting for skills to improve** - Results matter now
2. **Full docs in context** - Wasteful; index + retrieval is sufficient
3. **Relying on implicit skill invocation** - 56% failure rate
4. **Pre-training assumptions** - Models have outdated framework knowledge

## Eval Design

Test APIs **not in training data** - that's where doc access matters most.

## Key Insight

> The "dumb" approach (a static markdown file) outperformed sophisticated skill-based retrieval. Shift agents from pre-training-led reasoning to retrieval-led reasoning using passive context.
