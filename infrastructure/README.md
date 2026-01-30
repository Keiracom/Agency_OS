# Elliot Persistent Learning System - Phase 1

Infrastructure for cross-session memory and automated knowledge acquisition.

## Overview

This system compensates for session-based memory loss by:
1. **Persisting knowledge** in Supabase with vector embeddings for semantic search
2. **Automating learning** via daily scrapes of HackerNews, ProductHunt, GitHub Trending
3. **Maintaining session state** in Redis for task continuity
4. **Bootstrapping context** at session start with relevant knowledge

## Components

### 1. Supabase Schema (`supabase/migrations/`)

**Tables:**
- `elliot_knowledge` - Persistent knowledge base with embeddings
- `elliot_session_state` - Key-value store for session continuity

**Functions:**
- `get_bootstrap_context()` - Retrieve recent high-confidence knowledge
- `search_knowledge_by_embedding()` - Semantic vector search

**Run migration:**
```bash
# Via Supabase CLI
supabase db push

# Or manually in SQL Editor
# Copy contents of supabase/migrations/001_elliot_learning_system.sql
```

### 2. Prefect Flow (`prefect/flows/learning_scrape.py`)

**Flow:** `daily_learning_scrape`

**Sources:**
- HackerNews API (top 30 stories)
- ProductHunt RSS feed (top 5)
- GitHub Trending page (top 10 repos)

**Features:**
- Rate-limited: 1 request per 5 seconds
- Automatic categorization
- Deduplication via content hashing
- Confidence scoring based on engagement

**Deploy:**
```bash
# Register with Prefect
cd infrastructure/prefect/flows
prefect deployment build learning_scrape.py:daily_learning_scrape \
    --name "Daily Learning Scrape" \
    --cron "0 6 * * *" \
    --timezone "UTC"
prefect deployment apply daily_learning_scrape-deployment.yaml

# Or run manually
python learning_scrape.py
```

### 3. State Manager (`state/state_manager.py`)

**Keys:**
- `elliot:current_task` - Active task with context
- `elliot:last_session` - Previous session summary + unfinished work
- `elliot:pending_todos` - Deferred task queue

**Usage:**
```python
from infrastructure.redis.state_manager import (
    set_current_task,
    get_current_task,
    add_todo,
    complete_todo,
    save_session_end,
    get_bootstrap_state
)

# Set current task
set_current_task("Building learning system", priority="high")

# Add a todo
todo_id = add_todo("Review PR #123", priority="medium")

# Get all state for bootstrap
state = get_bootstrap_state()
```

### 4. Bootstrap Context (`bootstrap_context.py`)

**Main function:** `get_bootstrap_context()`

Combines:
- Recent knowledge from Supabase
- Session state from Redis
- Optional semantic search

**Usage:**
```python
from infrastructure.bootstrap_context import (
    get_bootstrap_context,
    format_context_for_injection
)

# Get context
context = get_bootstrap_context(query="current priorities")

# Format for prompt injection
prompt_text = format_context_for_injection(context, max_chars=4000)
```

## Environment Variables

Required in `~/.config/agency-os/.env`:

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Redis (Upstash)
UPSTASH_REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379

# Prefect (for flow deployment)
PREFECT_API_URL=https://prefect-server.railway.app/api

# Optional: OpenAI for embeddings
OPENAI_API_KEY=sk-...
```

## Deployment Steps

### Manual Steps Required:

1. **Run Supabase Migration**
   ```bash
   # Option A: Supabase CLI
   supabase db push
   
   # Option B: Copy SQL to Supabase Dashboard > SQL Editor
   ```

2. **Install Python Dependencies**
   ```bash
   pip install supabase redis prefect httpx python-dotenv
   # For embeddings: pip install openai
   ```

3. **Deploy Prefect Flow**
   ```bash
   cd infrastructure/prefect/flows
   prefect deployment build learning_scrape.py:daily_learning_scrape \
       --name "Daily Learning Scrape" \
       --cron "0 6 * * *"
   prefect deployment apply daily_learning_scrape-deployment.yaml
   ```

4. **Test Components**
   ```bash
   # Test Redis
   python infrastructure/redis/state_manager.py
   
   # Test Bootstrap
   python infrastructure/bootstrap_context.py
   
   # Test Learning Scrape (manual run)
   python infrastructure/prefect/flows/learning_scrape.py
   ```

## Integration with Clawdbot

Add to session initialization (AGENTS.md or bootstrap):

```markdown
## Session Bootstrap

On session start, run:
```python
from infrastructure.bootstrap_context import get_bootstrap_context, format_context_for_injection
context = get_bootstrap_context()
print(format_context_for_injection(context))
```
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Session Bootstrap                        │
│  ┌─────────────────┐    ┌─────────────────────────────────┐│
│  │ Redis State     │    │ Supabase Knowledge              ││
│  │ - current_task  │    │ - elliot_knowledge (vector)     ││
│  │ - last_session  │    │ - elliot_session_state          ││
│  │ - pending_todos │    │                                 ││
│  └────────┬────────┘    └────────────────┬────────────────┘│
│           │                              │                  │
│           └──────────────┬───────────────┘                  │
│                          │                                  │
│                 ┌────────▼────────┐                         │
│                 │ bootstrap_      │                         │
│                 │ context.py      │                         │
│                 └────────┬────────┘                         │
│                          │                                  │
│                 ┌────────▼────────┐                         │
│                 │ Context         │                         │
│                 │ Injection       │                         │
│                 └─────────────────┘                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Automated Learning                         │
│                                                             │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐        │
│  │HackerNews│  │ ProductHunt  │  │ GitHub Trending│        │
│  └────┬─────┘  └──────┬───────┘  └───────┬────────┘        │
│       │               │                  │                  │
│       └───────────────┼──────────────────┘                  │
│                       │                                     │
│              ┌────────▼────────┐                            │
│              │ Prefect Flow    │  ← Runs daily @ 6am UTC   │
│              │ learning_scrape │                            │
│              └────────┬────────┘                            │
│                       │                                     │
│              ┌────────▼────────┐                            │
│              │ elliot_knowledge│                            │
│              │ (Supabase)      │                            │
│              └─────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

## Application Enforcement (Phase 1.5)

### The Contract

**"I add a tool, I tell you how I applied it."**

Knowledge isn't just collected—it must be **applied**. Every insight added to the system is tracked until it's used in a real task.

### How It Works

1. **Knowledge is scraped** daily from HackerNews, ProductHunt, GitHub Trending
2. **Decay starts immediately** for unapplied knowledge (-0.1 per day)
3. **Application resets decay** to 1.0 and records the context
4. **Pruning removes stale items** below 0.3 decay score

### Decay Mechanism

| Day | Decay Score | Status |
|-----|-------------|--------|
| 0   | 1.0         | Fresh  |
| 3   | 0.7         | Active |
| 5   | 0.5         | ⚠️ At Risk |
| 7   | 0.3         | 🔴 Prune Threshold |
| 10  | 0.0         | Deleted |

### Application Tracker Module

```python
from infrastructure.application_tracker import (
    get_unapplied_knowledge,
    apply_knowledge,
    get_session_learning_report,
    prune_stale_knowledge
)

# Get knowledge to apply this session
items = get_unapplied_knowledge(limit=5)

# Mark knowledge as applied with context
apply_knowledge(
    knowledge_id="uuid-here",
    context="Used vector DB comparison to recommend Pinecone for client X"
)

# Generate session report
report = get_session_learning_report()
```

### CLI Usage

```bash
cd infrastructure

# Show session report
python application_tracker.py report

# List unapplied knowledge
python application_tracker.py unapplied

# Mark knowledge as applied
python application_tracker.py apply <uuid> "How I used this knowledge"

# Manual decay (normally runs daily)
python application_tracker.py decay

# Prune stale knowledge
python application_tracker.py prune
```

### Prefect Flow: Knowledge Decay

**Flow:** `knowledge_decay`
**Schedule:** Daily at 7am UTC (after learning scrape)

```bash
# Deploy
prefect deployment build prefect/flows/knowledge_decay.py:knowledge_decay \
    --name "Knowledge Decay" \
    --cron "0 7 * * *" \
    --timezone "UTC"
prefect deployment apply knowledge_decay-deployment.yaml

# Manual run
python prefect/flows/knowledge_decay.py
```

### Database Functions

| Function | Purpose |
|----------|---------|
| `decay_unused_knowledge()` | Daily: reduce decay by 0.1 |
| `mark_knowledge_applied(id, context)` | Mark applied, reset decay |
| `get_unapplied_knowledge(limit, min_score)` | Fetch pending items |
| `prune_stale_knowledge(min_score)` | Remove items below threshold |
| `get_session_learning_stats(hours)` | Stats for reports |

### Good vs Bad Application Context

✅ **Good:**
- "Used HN insight about vector DBs to recommend Pinecone for client project"
- "Applied GitHub trending repo pattern to speed up image processing pipeline"
- "Referenced ProductHunt tool in Dave's workflow optimization discussion"

❌ **Bad:**
- "Read it"
- "Noted"
- "Will use later"
- "Interesting"

Be specific: **What task? What outcome?**

---

## Future Enhancements (Phase 2+)

- [ ] Embedding generation pipeline (batch process new knowledge)
- [x] ~~Knowledge decay scoring (time-sensitive info loses relevance)~~
- [ ] Cross-reference graph (link related knowledge items)
- [ ] Active learning triggers (identify knowledge gaps from conversations)
- [x] ~~Knowledge application tracking (mark when insights are used)~~
