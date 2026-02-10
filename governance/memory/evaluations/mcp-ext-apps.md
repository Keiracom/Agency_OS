# Tool Evaluation: MCP ext-apps (Model Context Protocol Apps)

**Evaluated:** 2026-01-30
**Source:** https://github.com/modelcontextprotocol/ext-apps

## What It Does
Official SDK/spec for MCP Apps Extension (SEP-1865):
- Allows MCP servers to display interactive UI elements in AI chatbots
- Standard for embedding UIs in conversational interfaces
- Bidirectional communication between host and embedded UI
- Examples: maps, charts, forms, video players, 3D viewers

```
Tool definition → LLM calls tool → Host renders UI → Bidirectional comms
```

## Pricing
- **Open Source** (Apache 2.0)
- Part of Model Context Protocol standard

## Integration Complexity with Our Stack
| Factor | Assessment |
|--------|------------|
| Stack | TypeScript SDK - would need JS/TS component |
| Relevance | MCP is Anthropic's protocol - we use Claude |
| Use Case | UI rendering in chat - not our current focus |

**Complexity: MEDIUM** - Interesting architecture, not immediately applicable

## Competitors/Alternatives
- **OpenAI Apps SDK** - Similar concept for ChatGPT
- **Artifacts (Claude)** - Built-in UI rendering
- **Streamlit** - Python UI for data apps
- **Gradio** - ML UI framework

## Analysis
MCP Apps is interesting for future reference:
- Shows direction of AI chatbot capabilities
- Could enable richer interactions in Elliot dashboard
- Not immediately relevant to B2B sales automation

The specification itself is worth reading for architectural patterns, but we don't have a use case for embedding interactive UIs in chat responses right now.

## Recommendation: **SKIP**

**Reasoning:**
1. Interesting technology but not relevant to Agency OS goals
2. We don't have MCP-enabled chat clients as a use case
3. Focus should remain on sales automation, not chatbot UIs
4. Could revisit if building conversational UI features

**Action:** Archive for reference. Revisit if building interactive chat features.
