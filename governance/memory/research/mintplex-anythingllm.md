# AnythingLLM - All-in-One AI Application

**Source:** https://github.com/Mintplex-Labs/anything-llm
**Stars:** 53,986 | **Language:** JavaScript
**Researched:** 2026-01-30

## Summary
Full-stack desktop & Docker AI application with built-in RAG, AI agents, no-code agent builder, and MCP compatibility. Turn any document into context for LLMs with multi-user support.

## Key Features

### Core Capabilities
- **Document Chat** - RAG with any doc type (PDF, TXT, DOCX, etc.)
- **Workspaces** - Containerized document contexts (like threads)
- **Multi-User** - Instance support with permissions (Docker)
- **Multi-Modal** - Both closed and open-source LLMs

### Agent Features (Relevant to Us)
- **Custom AI Agents** - Build specialized agents
- **No-Code Agent Builder** - Visual agent creation
- **MCP Compatibility** - Model Context Protocol support
- **Workspace Agents** - Browse web, use tools

### Embeddable Widget
- Custom chat widget for websites
- Docker version feature

## Supported Integrations

### LLM Providers (Extensive)
- OpenAI, Azure OpenAI
- Anthropic
- AWS Bedrock
- Google Gemini
- Ollama, LM Studio, LocalAI
- Together AI, Fireworks AI, Perplexity
- OpenRouter, DeepSeek, Mistral, Groq
- xAI, Cohere, Novita AI
- 30+ more providers

### Vector Databases
- LanceDB (default)
- PGVector, Pinecone, Chroma
- Weaviate, Qdrant, Milvus, Zilliz

### Audio/Speech
- Built-in transcription
- OpenAI Whisper
- ElevenLabs TTS
- PiperTTS (local)

## Architecture

### Monorepo Structure
```
frontend/    - ViteJS + React UI
server/      - NodeJS Express (vectorDB, LLM)
collector/   - Document processing
docker/      - Deployment configs
embed/       - Web widget submodule
browser-extension/ - Chrome extension
```

### Deployment Options
- Desktop (Mac, Windows, Linux)
- Docker
- AWS, GCP, Digital Ocean, Railway, Render
- Self-hosted bare metal

## Agency OS Relevance

### Interesting Patterns
1. **Workspace Isolation** - Context containerization
2. **Provider Abstraction** - 30+ LLM backends
3. **No-Code Agent Builder** - Visual configuration
4. **MCP Compatibility** - Standard tool protocol

### Potential Uses
- Reference for multi-provider LLM integration
- Workspace pattern for context management
- Widget embedding approach

### Not Directly Applicable
- More end-user focused than infrastructure
- Desktop-first vs our headless approach

## Key Insight
AnythingLLM succeeds by being **radically inclusive** - supporting every LLM, every vector DB, desktop + cloud. The workspace concept for context isolation is clever and widely adopted (54K stars).

## Quick Links
- Site: https://anythingllm.com
- Docs: https://docs.anythingllm.com
- MCP Docs: https://docs.anythingllm.com/mcp-compatibility/overview
