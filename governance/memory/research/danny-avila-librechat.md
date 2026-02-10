# LibreChat - Enhanced ChatGPT Clone

**Source:** https://github.com/danny-avila/LibreChat
**Stars:** 33,470 | **Language:** TypeScript
**Researched:** 2026-01-30

## Summary
Self-hosted AI chat platform unifying all major AI providers in a single, privacy-focused interface. Features agents, MCP support, code interpreter, and enterprise-ready multi-user auth.

## Key Features

### AI Model Selection
- Anthropic (Claude), AWS Bedrock
- OpenAI, Azure OpenAI
- Google, Vertex AI
- OpenAI Responses API
- Custom endpoints for any OpenAI-compatible API

### Code Interpreter API
- Sandboxed execution: Python, Node.js, Go, C/C++, Java, PHP, Rust, Fortran
- File handling: upload, process, download
- Fully isolated security

### Agents & Tools
- **No-Code Custom Assistants** - Build specialized helpers
- **Agent Marketplace** - Community-built agents
- **Collaborative Sharing** - Share with users/groups
- **MCP Server Support** - Model Context Protocol tools
- **File search, code execution, more**

### Web Search Integration
- Combines search providers, content scrapers, result rerankers
- Customizable Jina Reranking

### Code Artifacts
- Generate React, HTML, Mermaid diagrams in chat
- Generative UI approach

### Image Generation
- GPT-Image-1, DALL-E (3/2)
- Stable Diffusion, Flux
- MCP server integration

### Multi-User & Enterprise
- OAuth2, LDAP, Email login
- Built-in moderation
- Token spend tools
- Multi-tab & multi-device sync
- Resumable streams

### Context Management
- Presets: create, save, share
- Switch endpoints mid-chat
- Conversation branching
- Fork messages & conversations

## Tech Highlights

### Resumable Streams
- Auto-reconnect on connection drop
- Multi-device sync
- Single-server to Redis-scaled deployments

### Multilingual UI
- 30+ languages supported

## Agency OS Relevance

### Useful Patterns
1. **Agent Marketplace** - Community sharing model
2. **MCP Support** - Standard tool protocol
3. **Code Interpreter** - Sandboxed execution
4. **Conversation Forking** - Context branching
5. **Resumable Streams** - Connection resilience

### Reference Value
- Multi-provider integration patterns
- Enterprise auth implementation
- Agent sharing/permissions model

### Less Applicable
- UI-focused (we're headless)
- Chat interface centric

## Key Insight
LibreChat succeeds by being the **"Swiss Army knife" of chat UIs** - supporting every provider, every feature. The MCP + Agents + Code Interpreter combination shows where self-hosted AI interfaces are heading. 33K stars validates the "unified interface" approach.

## Quick Links
- Site: https://librechat.ai
- Docs: https://docs.librechat.ai
- Agents: https://www.librechat.ai/docs/features/agents
