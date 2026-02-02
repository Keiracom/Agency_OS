---
name: elliot-memory
description: Remember information across chat sessions. Use when user says "remember this", "don't forget", "add to memory", corrects you, or shares important preferences/decisions. Also use at session end for summary.
---

# Elliot Memory System

## Memory Layers

| Layer | Location | Read When | Write When |
|-------|----------|-----------|------------|
| Core Understanding | MEMORY.md | Session start | Major learnings |
| Daily Log | memory/daily/YYYY-MM-DD.md | Session start | Events, decisions, todos |
| Learnings | .learnings/*.md | Before similar tasks | Errors, corrections |
| Vector Memory | Clawdbot LanceDB | Auto-recall on queries | Important facts |
| Knowledge DB | elliot_knowledge (Supabase) | Via knowledge pipeline | Scraped knowledge |

## When to Store

### ALWAYS Store:
1. User preferences: "I prefer X over Y"
2. User corrections: "Actually, that's wrong because..."
3. Decisions made: "Let's go with option A"
4. Important dates/deadlines
5. Project context changes
6. New capabilities learned
7. Errors and their fixes

### DON'T Store:
- Transient task details
- Sensitive credentials (use env vars)
- Duplicate information
- Unverified assumptions

## How to Store

### 1. Quick Facts (Vector Memory)
For facts I should recall automatically:
```
memory_store text="Dave prefers Railway over Heroku for deployments" importance=0.9
```

### 2. Core Understanding (MEMORY.md)
For fundamental knowledge that shapes behavior:
- Edit MEMORY.md directly
- Add to appropriate section
- Keep concise

### 3. Daily Events (Daily Log)
For session events, decisions, todos:
```
# memory/daily/2026-01-30.md

## Events
- 10:15 - Built knowledge scraping pipeline
- 11:30 - Fixed security vulnerabilities

## Decisions
- Use native YouTube scraper instead of Apify
- Store transcripts, not just metadata

## Tomorrow
- [ ] Run full knowledge scrape
- [ ] Review signoffs
```

### 4. Learnings (.learnings/)
For corrections and errors:
```
# .learnings/LEARNINGS.md

## [LRN-20260130-001] correction

**Logged**: 2026-01-30T12:00:00Z
**Priority**: high

### Summary
User corrected: Reddit API requires browser User-Agent

### Context
Was using bot User-Agent, got 403 errors

### Resolution
Use: Mozilla/5.0 (Windows NT 10.0; Win64; x64)...
```

## Triggers

When user says:
- "Remember this" → Store in appropriate layer
- "Don't forget" → Store with high importance
- "Add to memory" → Store in MEMORY.md
- "Actually..." / "No, that's wrong" → Log to .learnings/
- "For next time..." → Store preference

## Session End Protocol

Before session ends (context getting full, user says goodbye):
1. Summarize key events to daily log
2. Note any unfinished tasks
3. Store important learnings
4. Update MEMORY.md if major discoveries

## Recall Protocol

Before answering questions about:
- Past decisions → Check MEMORY.md Section 5
- User preferences → Check MEMORY.md Section 3, vector memory
- Previous work → Check daily logs, vector memory
- Errors/fixes → Check .learnings/

## Commands

User can explicitly trigger:
- "What do you remember about X?" → Recall from all layers
- "Remember: X" → Store X
- "Forget X" → Remove from memory (careful!)
- "Update memory with X" → Edit existing entry
