# HEARTBEAT.md - Pulse Check

## 1. System Health

* **Context:** If >50% used, Warn. If >60%, SAVE & RESTART.

## 2. Memory Grooming (Incremental)

* **Scan:** Read today's `memory/daily/YYYY-MM-DD.md`.
* **Extract:** Move *new* Learnings/Decisions/Patterns to permanent files.
* **Tag:** Append `[PROCESSED]` to extracted lines in the daily log to prevent duplicates.

## 3. Proactive Scans (Pick ONE per beat, rotate)

| Check | What to Look For |
| :--- | :--- |
| GitHub | Stale PRs (>48h), failing CI, unreviewed code |
| Services | API health (Supabase, Railway, Prefect) |
| Blockers | $0 balances, expired trials, broken integrations |
| Opportunities | New leads, warm replies, hot prospects |
| Calendar | Upcoming meetings (next 24h), prep needed |

**Action:** If blocker found → surface immediately. If opportunity → add to daily log.

## 4. Delegation Audit (Weekly)

* Count `[DELEGATED]` vs `[SELF]` tags in daily logs.
* Target: 80% delegated. If below, flag for review.

## 5. Self-Improvement Triad (If significant work done)

* **Self-Questioning:** Did I answer what was actually asked?
* **Self-Navigating:** Was there a better approach I missed?
* **Self-Attributing:** What worked? What should I do differently?

**Action:** Save patterns to memory. Encode mistakes as rules. Update SOUL.md if needed.

## 6. Session Handoff (Before context restart)

* Write `HANDOFF.md` summarizing: current task, decisions made, next steps, blockers.
* Commit all changes to git.
* New session reads HANDOFF.md → deletes after loading.

## Output Protocol

* **No Action:** Reply `HEARTBEAT_OK` (SILENCE is golden).
* **Action/Update:** Brief, bulleted summary.
* **Urgent:** Mention @Dave immediately.
