---
name: llm-orchestration
description: Use when coordinating multiple sub-agents, deciding what to delegate, or optimizing parallel task execution under constraints.
source: "LLMs as Orchestrators: Constraint-Compliant Multi-Agent Optimization" (arXiv:2601.19121)
---

# LLM Orchestration Patterns

Principles for using LLMs as high-level coordinators that adaptively manage specialized agents, balancing exploration and exploitation while respecting hard constraints.

## Key Concepts

### 1. Dual-Agent Architecture
Decompose complex work into two complementary agent types:

| Agent Type | Focus | Strategy |
|------------|-------|----------|
| **Exploitation Agent** | Refine known-good approaches | Prioritize quality within constraints, conservative mutations |
| **Exploration Agent** | Discover novel solutions | Ignore constraints initially, aggressive exploration, higher mutation |

**Why it works:** Single-population approaches converge prematurely. Specialization allows parallel optimization of different search strategies.

### 2. Constraint Domination Principle (CDP)
When evaluating agent outputs under constraints:
1. **Feasible solutions always dominate infeasible ones**
2. Among infeasible: prefer lower total constraint violation
3. Among feasible: use quality metrics to rank

### 3. Adaptive ε-Relaxation
Start with relaxed constraints, tighten over time:
```
ε_t = ε_0 × γ^(t/T_max)
```
- **Early phase:** ~20% of solutions can violate constraints (enables exploration)
- **Late phase:** Zero tolerance (guarantees feasibility)
- **Decay rate:** γ = 0.8 balances exploration vs convergence

### 4. Knowledge Transfer
Elite solutions flow bidirectionally between agents:
- Select transfers by **crowding distance** (sparse regions = high value)
- Exploitation agent receives novel discoveries from exploration
- Exploration agent gets guidance from high-quality feasible solutions

### 5. Dynamic Resource Allocation
The orchestrator adjusts agent ratios (α) based on:
- Optimization progress (hypervolume improvement rate)
- Constraint satisfaction ratio
- Stagnation detection

**Default pattern:**
| Phase | α (Exploitation %) | Trigger |
|-------|-------------------|---------|
| Early | 60% | Initial state |
| Middle | 72% | Constraints stabilizing |
| Late | 80% | Convergence phase |
| Violation detected | 55% | Feasibility < 80% |

## When to Apply

✅ **Use this pattern when:**
- Task has multiple competing objectives (accuracy vs speed vs cost)
- Hard constraints exist (budget, time, policy compliance)
- Search space is large with risk of local optima
- Need both quality refinement AND novel discovery

❌ **Don't use when:**
- Single-objective, well-defined task
- No constraints to balance
- Task is simple enough for single-agent execution
- Real-time latency requirements (<100ms)

## Patterns for Sub-Agent Spawning

### Pattern 1: Parallel Specialized Agents
```
Task: Research + Implementation

Spawn:
- Exploration Agent: "Research all approaches, ignore time constraints initially"
- Exploitation Agent: "Implement most promising known approach under deadline"

Coordinate: Transfer findings from exploration → exploitation when quality threshold met
```

### Pattern 2: Constraint-Aware Delegation
```
Before spawning, classify constraints:
- HARD: Must never violate (security, compliance, user instructions)
- SOFT: Can relax early, tighten later (formatting, optimization targets)

Agent instructions:
- Exploitation agents: Enforce all constraints from start
- Exploration agents: Enforce HARD only, ignore SOFT initially
```

### Pattern 3: Adaptive Rebalancing
Monitor spawned agents and reallocate:
```python
if feasibility_rate < 0.8:
    increase_exploration()  # α → 0.55
elif hypervolume_stagnating:
    increase_exploration()  # Escape local optima
elif constraints_stable and converging:
    increase_exploitation()  # α → 0.80
```

### Pattern 4: Elite Solution Transfer
When one agent finds a breakthrough:
1. Evaluate against constraints
2. If feasible: share with exploitation agents
3. If promising but infeasible: share with exploration agents
4. Use crowding distance to prioritize diverse solutions

### Pattern 5: Phased Constraint Tightening
```
Phase 1 (0-30%): Allow constraint violations, maximize discovery
Phase 2 (30-70%): Gradually tighten constraints
Phase 3 (70-100%): Strict enforcement, refinement only
```

## Practical Examples for Elliot

### Example 1: Multi-Source Research Task
```
User: "Research competitor pricing strategies"

Orchestration:
1. Spawn exploration agent: "Search broadly - news, forums, SEC filings, job postings"
2. Spawn exploitation agent: "Deep-dive on top 3 known competitors"
3. Coordinate: Share findings every N iterations
4. Final: Exploitation agent synthesizes with quality constraints
```

### Example 2: Code Generation Under Constraints
```
Constraints: Must pass tests, <100 lines, use existing patterns

Orchestration:
1. Exploration agent: Generate diverse approaches (ignore line limit)
2. Exploitation agent: Refine best approach to meet all constraints
3. Transfer: When exploration finds passing tests, send to exploitation
4. Output: Exploitation agent's constrained refinement
```

### Example 3: Content Creation Pipeline
```
Constraints: Brand voice, factual accuracy, word limit

Phase 1 (ε=0.8): Exploration generates creative variations
Phase 2 (ε=0.5): Filter for brand voice compliance
Phase 3 (ε=0): Final polish meeting all constraints
```

## Anti-patterns

### ❌ Single-Agent Overload
**Problem:** Giving one agent all objectives and constraints
**Result:** Premature convergence to mediocre solutions
**Fix:** Separate exploration and exploitation responsibilities

### ❌ Fixed Resource Allocation
**Problem:** Static 50/50 split between agent types
**Result:** Wasted compute when one strategy dominates
**Fix:** Monitor metrics, adjust α dynamically

### ❌ Hard Constraints From Start
**Problem:** Enforcing all constraints immediately
**Result:** Narrow feasible region, poor solution diversity
**Fix:** Use ε-relaxation - start loose, tighten progressively

### ❌ No Knowledge Transfer
**Problem:** Agents working in isolation
**Result:** Duplicate work, missed synergies
**Fix:** Periodic elite solution exchange based on crowding distance

### ❌ Ignoring Stagnation
**Problem:** Continuing exploitation when hypervolume plateaus
**Result:** Stuck in local optima
**Fix:** Increase exploration ratio when improvement rate drops

## Coordination Prompts

### For Exploitation Agent
```
You are the exploitation agent. Your role:
- Work within ALL constraints strictly
- Refine and improve existing high-quality solutions
- Prioritize feasibility over novelty
- Use conservative, targeted improvements
```

### For Exploration Agent  
```
You are the exploration agent. Your role:
- Prioritize discovery and diversity
- Only enforce HARD constraints (security, compliance)
- Use aggressive, creative approaches
- Share promising solutions even if imperfect
```

### For Orchestrator Decision
```
Current state:
- Feasibility rate: {x}%
- Recent improvement: {y}%
- Generations remaining: {z}

Decide exploitation ratio α ∈ [0.5, 0.9]:
- Low feasibility → decrease α (more exploration)
- Stagnating → decrease α (escape local optima)  
- Stable & converging → increase α (refine)
```

## Key Metrics to Monitor

| Metric | Meaning | Action Threshold |
|--------|---------|------------------|
| Feasibility Rate | % solutions meeting constraints | < 80% → increase exploration |
| Hypervolume | Pareto front coverage | Stagnant 3+ iterations → increase exploration |
| Crowding Distance | Solution diversity | Low → prioritize diverse transfers |
| Constraint Violation | Sum of violations | Rising → tighten ε faster |

## Summary

The orchestrator's job is **resource allocation and coordination**, not execution:

1. **Spawn specialized agents** (exploration + exploitation)
2. **Set initial constraint tolerance** (ε-relaxation)
3. **Monitor progress** (feasibility, hypervolume, stagnation)
4. **Reallocate resources** (adjust α based on metrics)
5. **Transfer knowledge** (elite solutions between agents)
6. **Tighten constraints** (ε → 0 as optimization progresses)
7. **Return best feasible solution** from exploitation agent
