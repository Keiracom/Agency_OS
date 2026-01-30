# RAGFlow - RAG Engine with Agent Capabilities

**Source:** https://github.com/infiniflow/ragflow
**Stars:** 72,453 | **Language:** Python
**Researched:** 2026-01-30

## Summary
Leading open-source RAG engine that fuses cutting-edge retrieval with agent capabilities to create a superior context layer for LLMs. Features agentic workflows, MCP support, and production-grade document processing.

## Key Features

### 1. Deep Document Understanding
- Knowledge extraction from unstructured data with complex formats
- Handles PDF, Word, slides, excel, txt, images, scanned copies, web pages
- "Needle in a data haystack" of unlimited tokens

### 2. Template-Based Chunking
- Intelligent and explainable chunking
- Multiple template options
- Visualization for human intervention

### 3. Grounded Citations
- Reduced hallucinations via traceable citations
- Quick view of key references
- Citation visualization for verification

### 4. Agent Capabilities (Recent)
- Memory for AI agents (2025-12)
- Agentic workflow + MCP support (2025-08)
- Python/JavaScript code executor (2025-05)
- Cross-language query support

### 5. Data Synchronization
- Confluence, S3, Notion, Discord, Google Drive integration
- Orchestrable ingestion pipeline

## Architecture

### Components
- **Context Engine** - Converged RAG + agent orchestration
- **Pre-built Agent Templates** - Production-ready patterns
- **Vector Options** - Elasticsearch (default) or Infinity
- **Multi-Modal** - Image understanding within PDF/DOCX

### Tech Stack
```
Docker (required)
- Elasticsearch or Infinity (vector DB)
- MySQL
- Redis
- MinIO
- gVisor (for code sandbox)
```

### System Requirements
- CPU >= 4 cores
- RAM >= 16 GB
- Disk >= 50 GB
- Docker >= 24.0.0

## Recent Updates (Relevant)
- 2025-12-26: Memory for AI agents
- 2025-10-15: Orchestrable ingestion pipeline
- 2025-08-01: Agentic workflow and MCP
- 2025-05-23: Python/JS code executor in Agent

## Agency OS Relevance

### Potential Integration Points
1. **Document Processing** - Production-grade chunking/extraction
2. **Citation System** - Grounded, traceable responses
3. **Agent Memory** - Built-in memory patterns
4. **Code Executor** - Sandboxed execution

### Considerations
- Heavy infrastructure (16GB RAM minimum)
- Docker-centric deployment
- Strong for document-heavy use cases

## Key Insight
RAGFlow represents the **convergence of RAG and agents** - demonstrating that retrieval and agentic capabilities are complementary, not separate concerns. The 72K stars suggest this is where the industry is heading.

## Useful Links
- Demo: https://demo.ragflow.io
- Docs: https://ragflow.io/docs/dev/
