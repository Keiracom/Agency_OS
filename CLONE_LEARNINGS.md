# CLONE_LEARNINGS.md — ORION working journal

Per-clone working journal. Persists across `/clear` context resets between tasks.
Complements `public.agent_memories` (tagged `callsign=orion`) for cross-clone
pattern sharing.

## Format

One entry per learning. Newest at top. Each entry:

```
### <YYYY-MM-DD> — <one-line summary>
**Task:** <task-ref>
**Context:** <what you were doing>
**Learning:** <the pattern — what to do / what to avoid>
**Why:** <root cause or rationale — makes the rule judgment-friendly>
```

## When to write

- After a task completes, if you encountered a non-obvious failure mode or
  discovered a pattern that future clone tasks should respect.
- After parent peer-correction, when the correction reveals a rule you didn't know.
- After a stall you recovered from, documenting what caused it and how to avoid.

## When NOT to write

- Information already in `CLAUDE.md` or `~/.claude/CLAUDE.md` (don't duplicate).
- Purely task-specific details the next task won't hit.
- Facts derivable from git log, code, or the project docs.

## Cross-clone sharing

For patterns that would help ATLAS too, additionally write to
`public.agent_memories` via MCP bridge tagged `callsign=orion, source_type=pattern`.
Keep the one-liner summary here; the full pattern lives in memory.

---

## Entries

<!-- Newest first. No entries yet. -->
