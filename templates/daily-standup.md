# Daily Standup Template

## Purpose
Generate a daily standup summary by reviewing memory/daily/*.md log files.

## Input Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `DATE` | ❌ | Target date YYYY-MM-DD (default: today) |
| `LOOKBACK_DAYS` | ❌ | Days to review for context (default: 1) |
| `TEAM_MEMBER` | ❌ | Filter by person (default: all/Dave) |
| `PROJECT_FILTER` | ❌ | Focus on specific project |

## Instructions

### Step 1: Load Daily Logs
```bash
# Today's log
cat ~/clawd/memory/daily/$(date +%Y-%m-%d).md

# Yesterday's log (for context)
cat ~/clawd/memory/daily/$(date -d "yesterday" +%Y-%m-%d).md
```

### Step 2: Extract Key Information

Scan logs for:
- **Completed items** — Look for ✅, "done", "shipped", "merged", "completed"
- **In progress** — Look for 🔄, "working on", "started", "continuing"
- **Blockers** — Look for ❌, "blocked", "waiting", "need", "stuck"
- **Decisions made** — Look for "decided", "agreed", "confirmed"
- **Upcoming** — Look for "tomorrow", "next", "will", "planning to"

### Step 3: Categorize by Project/Area
Group findings by:
- Project name (Agency OS, Elliot, etc.)
- Area (Frontend, Backend, Infra, Outreach, etc.)
- Priority (P0/P1/P2)

### Step 4: Format Standup

## Expected Output Format

```markdown
# 📅 Daily Standup — [DATE]

**Generated:** [Timestamp]
**Period:** [DATE] (with context from [LOOKBACK_DAYS] days)

---

## ✅ Yesterday (Completed)

### [Project 1]
- Completed task 1
- Shipped feature X

### [Project 2]
- Fixed bug Y
- Merged PR #123

---

## 🔄 Today (In Progress)

### [Project 1]
- [ ] Task currently working on
- [ ] Planned for today

### [Project 2]
- [ ] Continuation of work

---

## 🚧 Blockers

| Blocker | Owner | Waiting On | Since |
|---------|-------|------------|-------|
| Issue 1 | @person | External API | 2 days |

---

## 📢 Announcements / Decisions

- **Decision:** [What was decided and why]
- **FYI:** [Important context]

---

## 📊 Metrics (if available)

| Metric | Value | Trend |
|--------|-------|-------|
| PRs Merged | X | ↑/↓/→ |
| Issues Closed | X | ↑/↓/→ |

---

## 🎯 Focus for Today

1. **Priority 1:** [Most important thing]
2. **Priority 2:** [Second priority]
3. **Priority 3:** [Third priority]

---

*Generated from memory/daily/ logs by Elliot*
```

## Example Usage
```
@elliot Generate daily standup for today
@elliot What did we do yesterday? Use daily-standup template
@elliot Standup for 2025-01-28 focusing on Agency OS
```

## Automation Hook
Can be triggered automatically via:
```bash
# Add to crontab for 9am AEST (22:00 UTC previous day)
0 22 * * * /path/to/generate-standup.sh
```

## Notes
- Works best with consistent logging in memory/daily/
- Cross-reference with GitHub activity for completeness
- Include any calendar events from that day
- For remote teams, aggregate multiple people's logs
- Keep standups under 2 minutes read time

## Log Format Expected
The daily logs should follow a pattern like:
```markdown
## YYYY-MM-DD

### Done
- ✅ Task completed

### In Progress  
- 🔄 Working on X

### Notes
- Observation or decision

### Blockers
- ❌ Stuck on Y
```
