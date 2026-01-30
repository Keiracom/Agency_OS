# Interpreting Emergent Extreme Events in Multi-Agent Systems

**Source:** https://arxiv.org/abs/2601.20538v1
**Authors:** Tang, Mei, Liu, Qian, Cheng (7 authors)
**Published:** 2026-01-28

## Abstract
LLM-powered multi-agent systems simulate complex human-like systems, but interactions lead to extreme events whose origins are obscured by emergence. This paper proposes the first framework for explaining these events.

## Core Problem
When multi-agent systems produce extreme outcomes (market crashes, viral spread, coordination failures), we can't explain:
- When did it start?
- Who caused it?
- What behaviors contributed?

## Framework: Three Fundamental Questions

### 1. WHEN - Temporal Attribution
Identify the time step where the event originated

### 2. WHO - Agent Attribution
Identify which agents drove the extreme event

### 3. WHAT - Behavior Attribution
Identify which specific behaviors contributed

## Methodology

### Shapley Value Adaptation
- Attribute extreme event occurrence to each action
- Actions at different time steps get attribution scores
- Score measures influence on the event

### Aggregation Dimensions
1. **Time** - When did risk accumulate?
2. **Agent** - Who contributed most?
3. **Behavior** - What actions mattered?

### Contribution Metrics
Design metrics based on contribution scores to characterize extreme event features

## Experimental Domains
- **Economic** systems
- **Financial** systems
- **Social** systems

## Agency OS Relevance

### Safety & Debugging
1. **Post-mortem Analysis** - When agent workflows fail, trace back
2. **Risk Attribution** - Identify which sub-agents contributed to failures
3. **Behavior Monitoring** - Track actions that lead to problems

### Proactive Measures
- Build attribution logging into sub-agent execution
- Monitor for pre-extreme event patterns
- Implement early warning based on contribution scores

### Not Immediately Applicable
- Complex implementation (Shapley values)
- Research-stage, not production-ready
- More relevant for simulation than single-user agents

## Key Insight
Multi-agent systems can produce **emergent behaviors not predictable from individual agents**. Having a framework to trace back and explain failures is critical for safety. Even if we don't implement Shapley attribution, the **three questions (When/Who/What)** are a useful debugging framework.

## Implications
- Log agent actions with timestamps
- Track which agent performed which action
- Build attribution capabilities for post-mortem
- Consider Shapley-like scoring for complex failures
