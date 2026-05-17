## Discovery Log — Standing Practice (KEI-50 + KEI-55 v2 format, ratified 2026-05-14)

When you make a significant discovery — an approach that failed and why, a gotcha, a key design decision, a constraint you found — write a discovery log immediately. Use `bd discover`. Six fields plus two auto-populated. One sentence per field. This is how the team learns from your experience.

**Format v2 — final (Dave ratify 2026-05-14 — "No further changes without a KEI"):**

```json
{
  "agent": "callsign",
  "kei": "KEI-XX",
  "context": "one-line description of the problem",
  "finding": "what is true about this system",
  "failed_path": "what approach was tried and why it failed",
  "verified_path": "what approach works and why",
  "tags": ["tag1", "tag2"],
  "context_version": {auto-populated from environment},
  "validation_tier": {1|2|3 — auto-classified by system}
}
```

**Field-by-field**:
- `agent` — your callsign from `./IDENTITY.md` (auto).
- `kei` — Linear KEI ID you were on when the discovery happened.
- `context` — one sentence on the problem (what you were trying to do).
- `finding` — one sentence on what's true about the system. The signal you extracted.
- `failed_path` — one sentence on what you tried and why it failed (NEGATIVE path).
- `verified_path` — one sentence on what works and why (POSITIVE path).
- `tags` — short keyword list for retrieval.
- `context_version` — auto-populated (vendor versions, kernel, env) — for staleness detection (KEI-56).
- `validation_tier` — auto-classified 1/2/3 — for promotion governance (KEI-53).

`failed_path` AND `verified_path` are both required. Negative-only instructions are weaker than positive+negative pairs — LLMs handle "do X instead of Y" better than "don't do Y".

**Example (Max's interim-ulimit lesson 2026-05-14):**

```json
{
  "agent": "max",
  "kei": "KEI-44",
  "context": "Cognee Streams 3+4 resume under memory cap",
  "finding": "ulimit -v limits virtual memory, not RSS. Python+numpy and graph DBs reserve large virtual ranges at startup that aren't backed by real RSS — the limit fires before any work begins.",
  "failed_path": "ulimit -v 3145728 (3GB virtual). Result: all chunks failed; Cognee graph DB couldn't reserve its ~4GB virtual mmap; OOM before ingest started.",
  "verified_path": "systemd-run --user --scope -p MemoryMax=3G. cgroup ceiling on RSS only; virtual reservations pass; kernel OOM-kills only if real memory exceeds. Landed in PR #846.",
  "tags": ["cognee", "memory", "cgroup", "ulimit", "oom"],
  "context_version": {"cognee": "1.0.9", "kernel": "6.8.0-111-generic"},
  "validation_tier": 2
}
```

**Two write moments:**
1. **Mid-task (agent-initiated):** the moment you hit the insight, while it's fresh. Don't wait for the task to end.
2. **Task completion (system-prompted):** `bd complete` prompts "What did you discover? (optional — press Enter to skip)". Skipping is fine if nothing new emerged.

**What counts as a discovery:**
- An approach that failed and you now know why (e.g. "ulimit -v false-OOMs on Python+numpy reservations; use cgroup MemoryMax instead").
- A gotcha that cost you >15 minutes to track down.
- A design decision that resolved a real tradeoff (not a routine choice).
- A constraint you found that wasn't documented anywhere (vendor limit, environment quirk, race condition).

**What does NOT count:**
- Standard task progress (`PR #N opened`). Use Slack `[STARTING]` / `[READY]` for that.
- The reasoning chain itself. Discoveries are the signal extracted from reasoning.
- Repeats of existing knowledge. Search Weaviate (`bd recall <terms>`) first if you suspect prior coverage.

**Validation tiers (KEI-53 — Dave ratify 2026-05-14):**
- **Tier 1 (routine technical finding):** auto-promotes from staging → permanent after 24h. No peer concur required.
- **Tier 2 (architecture / design decision):** requires peer `[CONCUR:<callsign>]` in #execution before promotion.
- **Tier 3 (contradicts ratified decision / changes governance):** requires Dave approval before promotion.

System auto-classifies. If you think a finding deserves tier 2 or 3 review, tag accordingly in `tags` for the classifier.

**Context injection ceiling (KEI-55 — Dave ratify 2026-05-14):**
When `bd claim` injects discoveries into your tmux pane, the brief is hard-capped at 500 tokens. Lower-priority findings drop entirely (not truncated mid-sentence); cited references preserved so you can `bd recall <tag>` for full content.

**Indexing pipeline:**
Discovery written → `staging` collection → validation tier check (KEI-53) → `permanent` collection on promotion → available to all agents within 5 seconds via `bd recall` and via `bd claim` auto-injection (≤500 tokens per KEI-55).

**Status (2026-05-14):** the standing instruction is live now. `bd discover` and `bd complete --prompt-discovery` commands ship after Dave's KEI-46 (Weaviate) and KEI-47 (LlamaIndex) land. Until then, log discoveries by appending to `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/discovery_log.jsonl` in the v2 JSON format above; Dave's KEI-48 auto-indexing pipeline backfills on Weaviate ready.

**Authoritative trace:** Dave verbatim #ceo 2026-05-14 — Keiracom Collective Intelligence Architecture + four governance KEIs (KEI-53/54/55/56 amendment). KEI-50 in Dave's logical numbering (Linear KEI-52).
