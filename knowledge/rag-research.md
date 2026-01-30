# RAG & Knowledge System Best Practices Research

> **Research Date:** January 2026  
> **Sources:** GitHub repos, Reddit (r/LocalLLaMA, r/Rag), Hacker News, Academic papers, Production blog posts  
> **Purpose:** Inform major knowledge system build

---

## Executive Summary

RAG systems remain the dominant approach for grounding LLMs in external knowledge, but production deployments reveal consistent failure patterns. Key findings:

1. **Chunking strategy matters more than embedding model choice** (Anyscale research)
2. **Rerankers are transformative** - "The highest value 5 lines of code you'll add" (HN Production RAG)
3. **Retrieval gets WORSE with more data** without proper architecture (Google research)
4. **pgvector works for <500M vectors** but dedicated DBs win at scale
5. **Hybrid search (BM25 + vectors) beats either alone** consistently
6. **Contextual Retrieval reduces failures by 67%** when combined with reranking (Anthropic)

---

## 1. Chunking Strategies

### What Works

#### Optimal Chunk Sizes (Research-Backed)
| Chunk Size | Best For | Trade-offs |
|------------|----------|------------|
| 256-512 tokens | Fine-grained retrieval, Q&A | Higher precision, may lack context |
| 512-1024 tokens | Balanced general use | Sweet spot for most applications |
| 1024-2048 tokens | Complex topics, narratives | Better context, lower precision |

**Key Finding (Fudan University study):** 512 tokens with sliding window achieved 97.59% faithfulness and 97.41% relevancy.

#### Chunking Techniques Ranked by Effectiveness

1. **Semantic Chunking** (Best for dense, unstructured text)
   - Embeds sentences, finds semantic breakpoints via similarity analysis
   - Preserves complete ideas/topics
   - Higher compute cost but superior coherence

2. **Recursive Chunking** (Best general-purpose default)
   - Hierarchical separators: `\n\n` → `\n` → `.` → ` ` → character
   - Respects document structure
   - Good balance of simplicity and quality

3. **Document-Based Chunking** (Best for structured docs)
   - Split by format: Markdown headers, HTML tags, code functions
   - Maintains logical organization
   - Requires format-specific logic

4. **LLM-Based Chunking** (Best for high-value documents)
   - Use LLM to identify propositions/key points
   - Highest quality but expensive
   - Anthropic's Contextual Retrieval approach

5. **Fixed-Size Chunking** (Baseline only)
   - 10-20% overlap recommended
   - Fast but destroys semantic boundaries
   - Use only for prototyping

### What Fails

❌ **No overlap between chunks** - Critical context gets split  
❌ **Chunk sizes >2048 tokens** - "Lost in the middle" effect degrades LLM attention  
❌ **Ignoring document structure** - Tables, headers, lists need special handling  
❌ **Same strategy for all content** - PDFs, code, prose all need different approaches  
❌ **Token-level splitting mid-word** - Destroys semantic meaning

### Production Recommendations

```python
# Recommended default: Recursive with overlap
chunk_size = 512  # tokens
chunk_overlap = 50  # ~10% overlap
separators = ["\n\n", "\n", ". ", " ", ""]

# For complex documents: Semantic chunking
# Use embedding similarity to find natural break points
# Split when cosine similarity drops below threshold (0.7-0.85)
```

**Advanced: Anthropic's Contextual Retrieval**
```
Prepend context to each chunk before embedding:
"This chunk is from [document title] discussing [section topic]. [Original chunk content]"

Results: 67% reduction in retrieval failures when combined with reranking
```

---

## 2. Embedding Model Comparison

### Top Performers (2025-2026 MTEB Benchmarks)

| Model | MTEB Score | Dimensions | Cost | Best For |
|-------|------------|------------|------|----------|
| Cohere embed-v4 | 65.2 | 1024 | $0.35/1M | Enterprise, multilingual |
| OpenAI text-embedding-3-large | 64.6 | 3072 | $0.13/1M | General purpose, API simplicity |
| Voyage AI voyage-3 | ~64 | 1024 | $0.06/1M | Code, technical docs |
| BGE-M3 | 63.0 | 1024 | Free (self-host) | Multilingual, cost-sensitive |
| OpenAI text-embedding-3-small | ~62 | 1536 | $0.02/1M | Budget, high volume |

### Real-World Insights

**From r/Rag community:**
> "When choosing embedding model, consider your data's domain. For general text use text-embedding-3-small from OpenAI; for medical, try biomedBERT; for financial, use FinBERT."

**From HN Production RAG discussion:**
> "We found the embedding model matters less than people think once you add reranking. Grab text-embedding-3-large and move on."

**Cost vs Quality Trade-off:**
- OpenAI 3-large is 6x cost of 3-small
- Quality difference is marginal for most use cases
- **Recommendation:** Start with 3-small, upgrade only if recall metrics suffer

### Dimension Reduction
- OpenAI 3-large can be reduced from 3072 → 256 dimensions with ~5% quality loss
- Significant storage and latency savings
- Use Matryoshka Representation Learning (MRL) for flexible dimensions

---

## 3. Common Retrieval Failures and Fixes

### The Seven RAG Pitfalls (Barnett et al. 2024)

| Failure | Cause | Fix |
|---------|-------|-----|
| **Missing Content** | Answer doesn't exist in corpus | Enrich knowledge base, human-in-loop validation |
| **Missing Top Ranked** | Relevant doc ranked too low | Fine-tune reranker, adjust top-K |
| **Not in Context** | Right doc found but truncated | Adjust chunking, increase context window |
| **Failed Extraction** | LLM misses answer in noise | Dedupe, clean data, optimize prompts |
| **Wrong Format** | Output format incorrect | Structured outputs, schema enforcement |
| **Incorrect Specificity** | Too broad/narrow response | Query preprocessing, example questions |
| **Incomplete Answer** | Partial coverage of question | Multi-query, query decomposition |

### Semantic Search-Specific Failures

**From Zero Entropy analysis of 1000s of RAG queries:**

1. **Negated Queries**
   > "Which articles do NOT mention X?"
   - Both keyword and semantic search return docs that DO mention X
   - **Fix:** Query understanding layer, explicit negative filtering

2. **Multi-Hop Queries**
   > "If company fails to hold meeting, what is the penalty?"
   - Requires chaining: failure → termination → penalty
   - **Fix:** Agentic RAG with iterative search, query decomposition

3. **Fuzzy Filtering**
   > "Papers with sample size over 2000"
   - Metadata (sample size) and content (methods) in different chunks
   - **Fix:** Metadata extraction, hybrid structured + semantic search

### The Reranking Solution

**Critical insight from HN:**
> "The retriever is an idiot, never trust it. Retrieve k=25 and let a reranker actually pick the relevant contexts."

**Reranker Performance:**
- Cross-encoder reranking improves accuracy 20-35%
- Adds 200-500ms latency
- **Sweet spot:** Retrieve 50 → Rerank to 15-20

**Top Rerankers:**
1. Cohere Rerank 4 (pro and fast variants)
2. Voyage AI Reranker
3. BGE Reranker (open source)
4. Jina AI v2

**Implementation Pattern:**
```python
# Recommended pipeline
results = vector_search(query, k=50)  # Cast wide net
results += bm25_search(query, k=50)   # Hybrid retrieval
results = deduplicate(results)
results = reranker.rerank(query, results, top_k=15)  # Precision filter
```

---

## 4. Vector Database Considerations

### pgvector vs Dedicated Vector DBs

#### When pgvector Works (✓)
- < 500 million vectors
- Sub-100ms latency acceptable
- Already running PostgreSQL
- Hybrid relational + vector queries needed
- Budget-constrained (40-60% lower TCO)
- Moderate write velocity

#### When pgvector Fails (✗)
- Billions of vectors
- Sub-20ms latency required
- Heavy concurrent write load
- GPU-accelerated search needed
- Complex filtered vector search at scale

### pgvector Production Gotchas

**From "The Case Against pgvector" (Alex Jacobs):**

1. **Index Memory Spikes**
   - HNSW index build can consume 10+ GB RAM
   - Blocks production database during multi-hour builds
   - No throttling mechanism

2. **Real-time Indexing Issues**
   - IVFFlat: Clusters don't rebalance without full rebuild
   - HNSW: Lock contention under heavy writes
   - Neither designed for high-velocity ingestion

3. **Pre/Post Filter Dilemma**
   - Pre-filter: Great for selective filters, terrible otherwise
   - Post-filter: Can miss relevant results (ask for 10, get 3 after filter)
   - Postgres query planner wasn't built for this

4. **Workarounds Required**
   - Query rewriting per user type
   - Partitioning into separate tables
   - CTE optimization fences
   - Over-fetching and application filtering

### Vector DB Comparison

| Database | Billion Scale | Hybrid Search | Cloud Native | Best For |
|----------|---------------|---------------|--------------|----------|
| **Milvus** | ✓ | ✓ | ✓ | Full-featured, self-host |
| **Qdrant** | ✓ | ✓ | ✓ | Performance, Rust-based |
| **Pinecone** | ✓ | ✓ | ✓ | Managed, simplicity |
| **Weaviate** | ✗ | ✓ | ✓ | GraphQL, hybrid |
| **pgvector** | ✗ | Manual | ✗ | PostgreSQL users |
| **Chroma** | ✗ | ✓ | ✓ | Prototyping, local |

### Recommendation Matrix

| Scenario | Choice |
|----------|--------|
| Startup, <10M vectors, PostgreSQL shop | pgvector |
| Production, 10M-500M vectors, need hybrid search | Qdrant or Milvus |
| Enterprise, managed preference, budget available | Pinecone |
| Self-host, maximum control | Milvus |
| Prototype, local development | Chroma |

---

## 5. Production Gotchas Discovered

### Retrieval Degrades at Scale

**From Google Research (via HN):**
> "Retrieval gets WORSE with more data. As your corpus grows, the probability of retrieving irrelevant but semantically similar content increases."

**Mitigations:**
- Hierarchical retrieval (coarse → fine)
- Domain partitioning
- Metadata pre-filtering
- Aggressive reranking

### The "Lost in the Middle" Problem

LLMs struggle with information buried in middle of context:
- Beginning and end of context are used well
- Middle content is often missed
- **Fix:** Reorder retrieved chunks - most relevant first AND last

### Multi-Agent Hallucination Cascades

> "Multi-agent systems create hallucination cascades where one agent's error compounds through the chain."

**Mitigations:**
- Verification agents
- Confidence scoring at each step
- Citation/source tracking

### Agentic RAG is the New Default

**HN consensus:**
```
Classic RAG: User → Search → LLM → User
Agentic RAG: User ↔ LLM ↔ Search

Key differences:
- LLM can search multiple times
- LLM adjusts search queries
- LLM uses multiple tools
```

> "This combination has solved a majority of classic RAG problems. It improves user queries, maps abbreviations, corrects bad results on its own."

### Evaluation is Neglected but Critical

**From Zero Entropy:**
> "Retrieval evaluation is often overlooked, despite the impact on hallucination rate. Few have a method of associating 'thumbs down' with what went wrong."

**Recommended Metrics:**
- Recall@K (did we retrieve the right docs?)
- MRR (Mean Reciprocal Rank)
- Precision@K (after reranking)
- Faithfulness (is response grounded?)
- Answer relevancy

**Tools:** RAGAS, Braintrust, LangSmith

### Preprocessing is Underrated

> "Chunking strategy takes the most effort. You'll spend most of your time on it." (HN)

**Critical preprocessing steps:**
1. PDF → Markdown conversion (before chunking)
2. OCR for scanned documents
3. Table extraction and formatting
4. Metadata extraction (dates, authors, sections)
5. Deduplication across documents

### Synthetic Query Generation

**From Microsoft/Azure team:**
> "Users have very poor queries. Generate 3 synthetic query variants, parallel search, use reciprocal rank fusion to combine results."

```python
# Pattern: Query expansion
variants = llm.generate_query_variants(original_query, n=3)
all_results = []
for q in [original_query] + variants:
    all_results.extend(hybrid_search(q))
final = reciprocal_rank_fusion(all_results)
```

---

## 6. Recommended Production Architecture

### Minimal Viable RAG
```
Document → Chunk (recursive, 512 tokens, 10% overlap)
         → Embed (text-embedding-3-small)
         → Store (pgvector or Qdrant)
         
Query → Embed → Vector Search (k=25)
      → BM25 Search (k=25)
      → Dedupe + RRF
      → Rerank (top 10)
      → LLM Generate
```

### Advanced RAG
```
Document → Parse (PDF→MD, tables, metadata)
         → Chunk (semantic or LLM-based)
         → Contextualize (Anthropic method)
         → Embed (Voyage or text-3-large)
         → Store (Milvus/Qdrant + metadata)
         
Query → Query Expansion (3 variants)
      → Hybrid Search (vector + BM25)
      → Metadata Filter
      → Rerank (Cohere)
      → Context Reorder (most relevant first+last)
      → LLM Generate with citations
      → Verify/Ground check
```

### Key Metrics to Track
1. Retrieval latency (p50, p99)
2. Recall@K per query type
3. Reranker effectiveness (before/after)
4. End-to-end response quality (RAGAS)
5. Hallucination rate (citation verification)
6. User feedback correlation with retrieval quality

---

## 7. Quick Reference: Do's and Don'ts

### DO ✓
- Use hybrid search (vectors + BM25)
- Always rerank retrieved results
- Add context to chunks before embedding
- Test chunk sizes on YOUR data
- Track retrieval metrics separately from generation
- Use agentic search for complex queries
- Preprocess documents thoroughly
- Start simple, add complexity based on metrics

### DON'T ✗
- Trust embeddings alone for technical terms
- Skip reranking to save latency
- Use fixed-size chunks for all document types
- Assume pgvector scales infinitely
- Ignore the "lost in the middle" problem
- Ship without retrieval evaluation
- Over-engineer before validating basics work

---

## Sources

1. Fudan University - "Searching for Best Practices in RAG" (arXiv 2407.01219)
2. Anthropic - "Contextual Retrieval in AI Systems"
3. Chroma Technical Report - "Evaluating Chunking Strategies"
4. Weaviate Blog - "Chunking Strategies for RAG"
5. Stack Overflow Blog - "Practical tips for RAG"
6. Alex Jacobs - "The Case Against pgvector"
7. Zero Entropy - Analysis of 1000s of RAG queries
8. Barnett et al. 2024 - "Seven Failure Points in RAG"
9. Hacker News - Production RAG discussions
10. r/LocalLLaMA, r/Rag - Community experiences
11. Azure AI Search team - Query rewriting patterns
12. Agenta - "Ultimate Guide to Chunking Strategies"

---

*Last Updated: January 2026*
