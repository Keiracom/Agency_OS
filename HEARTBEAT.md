# HEARTBEAT.md - Pulse Check

## 1. System Health

* **Context:** If >50% used, Warn. If >60%, SAVE & RESTART.

## 2. Memory Grooming (Incremental)

* **Scan:** Read today's `memory/daily/YYYY-MM-DD.md`.
* **Extract:** Move *new* Learnings/Decisions/Patterns to permanent files.
* **Tag:** Append `[PROCESSED]` to extracted lines in the daily log to prevent duplicates.

## 3. External Checks (Pick ONE per beat)

* [ ] Urgent Emails (Gmail/Salesforge)
* [ ] Calendar (Next 24h)
* [ ] GitHub Notifications (PRs/Issues)
* [ ] Project Status (Agency OS pipeline)

## Output Protocol

* **No Action:** Reply `HEARTBEAT_OK` (SILENCE is golden).
* **Action/Update:** Brief, bulleted summary.
* **Urgent:** Mention @Dave immediately.
