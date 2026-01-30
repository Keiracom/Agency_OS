# Tool Evaluation: LobeHub

**Evaluated:** 2026-01-30
**Source:** https://github.com/lobehub/lobehub
**Stars:** 71,396

## What It Does
LobeHub is a multi-agent collaboration platform that provides:
- **Agent Builder** - Create personalized AI agents with auto-configuration
- **Multi-Agent Groups** - Agents collaborate like teammates (Pages, Schedule, Project, Workspace)
- **MCP Plugin System** - 10,000+ tools via Model Context Protocol
- **Personal Memory** - Transparent, editable memory for agent continuity
- **Multi-Model Support** - Works with OpenAI, Anthropic, local LLMs
- Desktop app, PWA, knowledge base, voice/TTS support

## Pricing
- **Open Source** (AGPLv3-like license)
- Self-hosted: Free
- Hosted: cloud.lobe.ai (pricing TBD)

## Integration Complexity with Our Stack
| Factor | Assessment |
|--------|------------|
| Stack | TypeScript/React frontend - incompatible with our FastAPI backend |
| Database | PostgreSQL support, but designed as standalone |
| Prefect | No integration - it's a complete platform, not a library |
| API | REST API available, could theoretically call as external service |

**Complexity: HIGH** - This is a competitor platform, not a component to integrate.

## Competitors/Alternatives
- **ChatGPT Teams** - OpenAI's collaboration product
- **Claude Teams** - Anthropic's team product  
- **Langflow** - Visual agent builder
- **Agency OS (Us)** - Our platform

## Analysis
LobeHub is impressive but solves a different problem than Agency OS:
- **LobeHub** = Consumer/prosumer multi-agent chat platform
- **Agency OS** = B2B sales automation with agentic capabilities

The MCP plugin architecture is worth studying for inspiration.

## Recommendation: **SKIP**

**Reasoning:**
1. Competes with, rather than complements, our architecture
2. Different target market (consumer vs B2B sales)
3. TypeScript codebase doesn't fit our Python/FastAPI stack
4. Would require major pivot to adopt

**Action:** Monitor for MCP plugin patterns we could adopt. Not for integration.
