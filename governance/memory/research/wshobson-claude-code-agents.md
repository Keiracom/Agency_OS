# Claude Code Plugins & Multi-Agent Orchestration

**Source:** https://github.com/wshobson/agents
**Stars:** 27,308 | **Language:** C# (Markdown plugins)
**Researched:** 2026-01-30

## Summary
Production-ready system combining 108 specialized AI agents, 15 workflow orchestrators, 129 agent skills, and 72 development tools organized into focused plugins for Claude Code.

## Architecture Highlights

### Granular Plugin System
- **72 Focused Plugins** - Single-responsibility, minimal token usage
- **Average 3.4 components per plugin** - Follows Anthropic's 2-8 pattern
- **Install only what you need** - Each plugin loads specific agents/tools

### Three-Tier Model Strategy ⭐
| Tier | Model | Use Case |
|------|-------|----------|
| Tier 1 | Opus 4.5 | Critical architecture, security, ALL code review |
| Tier 2 | Inherit | Complex tasks - user chooses model |
| Tier 3 | Sonnet | Support with intelligence (docs, testing) |
| Tier 4 | Haiku | Fast operational tasks (SEO, deployment) |

**Key Insight:** Opus 4.5's 65% token reduction on complex tasks often offsets higher rates.

### Progressive Disclosure (Skills)
Three-tier knowledge loading:
1. **Metadata** - Name + activation criteria (always loaded)
2. **Instructions** - Core guidance (loaded when activated)
3. **Resources** - Examples/templates (loaded on demand)

## Agent Categories (108 total)

| Category | Count | Examples |
|----------|-------|----------|
| Development | 4 | debugging, backend, frontend |
| Workflows | 4 | git, full-stack, TDD, Conductor |
| AI & ML | 4 | LLM apps, agent orchestration |
| Security | 4 | scanning, compliance |
| Languages | 7 | Python, JS/TS, systems, JVM |

## Workflow Orchestrators (15)

Multi-agent coordination systems:
- **Full-stack Feature Development** - 7+ agents coordinated
- **Security Hardening** - SAST, dependency scanning, review
- **ML Pipeline** - End-to-end orchestration

### Example Flow
```
Opus (architecture) → Sonnet (development) → Haiku (deployment)
```

## Agent Skills System ⭐

129 specialized knowledge packages:

**Language Development:**
- Python: async patterns, testing, packaging, UV
- JS/TS: advanced types, Node patterns, testing

**Infrastructure:**
- Kubernetes: manifests, Helm, GitOps, security
- Cloud: Terraform, multi-cloud, cost optimization

**LLM Applications (8 skills):**
- LangGraph
- Prompt engineering
- RAG
- Evaluation
- Embeddings
- Similarity search
- Vector tuning
- Hybrid search

## Agency OS Relevance

### High-Value Patterns
1. **Model Tiering** - Match model to task complexity
2. **Progressive Disclosure** - Load context only when needed
3. **Single-Responsibility Plugins** - Clean agent boundaries
4. **Orchestration over Execution** - Compose agents for workflows

### Implementation Ideas
- Adopt 3-tier model strategy for our agent spawning
- Implement progressive disclosure for knowledge loading
- Use orchestration patterns for complex tasks

## Key Insight
The system demonstrates that **careful categorization + model tiering + progressive disclosure** = production-ready multi-agent architecture. 27K stars validates this approach.
