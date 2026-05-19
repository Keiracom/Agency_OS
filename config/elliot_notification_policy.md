# Elliot → Dave Notification Policy

_Last ratified: 2026-05-19_

> This document is the source of truth for what elliot proactively surfaces to Dave in Slack #ceo. The elliot stop hook reads it on every turn-end and decides whether to post. Dave can edit this file to tune the behaviour — no code change required.

## Always post to #ceo

- **Task completion** — when I finish something Dave asked for. One bullet block describing what's done + what's next.
- **Blocker** — I hit something requiring Dave's decision or input. Describe the blocker and the choice.
- **Major architectural proposal** — I'm proposing a design change that needs Dave's sign-off before execution.
- **Critical state change** — a service going down, a key indexer stalling, a fleet incident.
- **Merge eligible** — a PR has reached dual-concur and is ready for me to merge.
- **Bootstrap milestone** — reaching a numbered stage milestone in the roadmap (e.g. "Stage 4 complete — step-away unlocked").

## Sometimes post (subject to cool-down)

- **Multi-step progress milestone** — only if a long-running task has crossed a meaningful threshold and Dave has been waiting more than 5 minutes.
- **Background process state change** — service started/stopped, indexer catch-up reached a round number.

## Never post

- Routine acknowledgements like "acknowledged", "starting", "noted", "got it", "waiting".
- Tool call narration like "running command", "checking file", "querying database".
- Self-noted internal thoughts that don't have an outcome attached.
- Wake hello (the wake hook handles that separately on session start).
- Auto-generated status that the live state probe already captures.
- Any message I posted to Slack manually within the same turn (no double-post).

## Cool-down

- **Maximum one auto-post per 60 seconds** — if multiple events fire within the window, coalesce to a single summary at the end of the window.
- The cool-down does NOT apply to blockers or critical state changes — those bypass the throttle.

## Format

- **Bold category header** (`**Category**`) at line start.
- Bullets only (`- ` prefix on each item).
- Plain English, no jargon, no internal codenames without spelling out.
- Lead with outcome + business meaning, not technical detail.
- **Never include in a #ceo post**: PR numbers, commit SHAs, file paths, env vars, PIDs, code fences, raw command output. Technical detail belongs in tool calls visible to me, not in Dave's read surface.
- If technical detail is essential, summarise in plain English (e.g. "five files changed across the indexers" not "5 files / 277 insertions").

## Verbosity dial

- **Default** = balanced. Completions + blockers + decisions all post; routine progress stays silent.
- **Chatty** = post on every meaningful step including progress milestones.
- **Quiet** = post only on completions and blockers; suppress decision proposals (queue them for batch summary).
- **Heads-down** = post only when something needs Dave's decision; everything else stays silent.

Dave can toggle by setting the verbosity at the top of this file (default = `balanced`).

VERBOSITY: balanced

## Notes for the hook implementation

- Keyword classifier for the simple cases (markers like "completion", "blocker", "merge eligible").
- If classification is ambiguous, default to silent. Better to under-post than spam.
- If the last assistant turn already contained a slack_relay call that posted to #ceo, suppress the auto-post (no double-post).
- Cool-down state at `/tmp/elliot_notify_state.json`.
