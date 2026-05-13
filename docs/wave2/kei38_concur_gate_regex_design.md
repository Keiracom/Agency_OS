# KEI-38 Design — Concur-gate regex narrowing

**Author:** Aiden (design only — per Dave verbatim ts ~1778665450)
**Implementer:** Elliot (post-compact ratification + execute)
**Beads:** Agency_OS-7yk42y — P0
**Linear:** [KEI-38](https://linear.app/keiracom/issue/KEI-38)

## Problem

Current concur-gate regex matches too broadly — it catches the word `CONCUR` (or `[CONCUR` partial brackets, or governance-prose-style "CONCUR with EMPIRICAL CORRECTION") anywhere in a post and converts the post to a CONCUR-REQUEST stub. Effect: Max's direct factual posts are gate-held, requiring Elliot to relay as plain text. Dave sees Elliot tag instead of Max.

Today's case study: Dave asked "why can't I see Max in this post?" because Max's factual status answer landed via Elliot relay. Max cannot post directly until this is narrowed.

## Required match (gate FIRES)

The regex must match ONLY explicit governance concurrence actions, defined as bracketed tags with an explicit callsign:

| Pattern | Example | Gate action |
|---|---|---|
| `[CONCUR:callsign]` | `[CONCUR:elliot]` | Hold for peer release |
| `[BLOCK:callsign]` | `[BLOCK:max]` | Hold for peer review |

Callsigns are the lowercase set: `aiden | elliot | max | atlas | orion | scout | enforcer`. Future agents added via a single union extension.

## Required no-match (gate PASSES)

The regex must NOT match any of:

1. **Factual prose containing "concur" lowercased** — e.g. "I concur with the analysis" mid-sentence.
2. **`CONCUR with EMPIRICAL CORRECTION` review-pattern prefix** — Max + Aiden use this for empirical-probe-before-concur review prose.
3. **Direct factual answers to Dave queries** — e.g. "Status: Stream 2 sealed, ..." which doesn't contain governance tags at all.
4. **Self-tagged author posts** — e.g. `[MAX]` opening tag on every Max post; matches nothing in the concur-gate regex.
5. **Multi-paragraph prose where one paragraph happens to contain `CONCUR`** — only the literal bracketed tag triggers.
6. **Comment/code snippets containing `[CONCUR:x]` as documentation** — borderline; design choice below.

## Proposed regex (anchored)

```python
import re

_CONCUR_GATE_RE = re.compile(
    r"^\s*\[(?P<action>CONCUR|BLOCK):(?P<callsign>aiden|elliot|max|atlas|orion|scout|enforcer)\](?:\s|$)",
    re.MULTILINE,
)
```

Match semantics:
- `^\s*` — anchored to line start (allows leading whitespace for indented re-posts).
- `\[(?P<action>CONCUR|BLOCK):` — literal brackets + uppercase action + colon, no surrounding text on the action.
- `(?P<callsign>...)` — explicit callsign enumeration (no `.*` wildcard).
- `\](?:\s|$)` — closing bracket followed by whitespace or end-of-line — prevents `[CONCUR:elliotsfoo]` matching `[CONCUR:elliot]` partial.
- `re.MULTILINE` — anchors `^` to line starts, allowing a governance tag on line N of a multi-paragraph post to trigger correctly.

### Why anchored + line-start

The current broad regex `\bCONCUR\b` (or similar) catches anywhere-in-post. The anchored form ensures only POSTS THAT START WITH (or have a line starting with) the explicit tag trigger. Factual prose mid-line is exempt.

### Borderline: bracketed tag in code snippets

Case: a design doc or post quotes `[CONCUR:x]` inside a fenced code block. The `^\s*\[` anchor still matches. Design choice:

**Option A** (chosen): tag inside code blocks STILL matches the gate. Rationale — once posted to #execution, the gate processes raw text; agents writing about the protocol in code blocks should escape the brackets (e.g. `[CONCUR:x]` → `&lbrack;CONCUR:x&rbrack;` or surround with backticks like `` `[CONCUR:x]` `` which adds backticks to the line-start). Keeps the regex simple + the false-positive rate is low (governance discussion posts are rare).

**Option B**: pre-filter triple-backtick fenced blocks before regex match. Requires fenced-block parser. Adds complexity for low frequency.

Recommend A. Document the escape pattern in GOVERNANCE.md.

## Test cases — must MATCH (gate fires)

| Input | Expected match |
|---|---|
| `[CONCUR:elliot] FINAL on PR #832` | YES — captures `action=CONCUR callsign=elliot` |
| `[BLOCK:max] hold on Sonar finding` | YES — captures `action=BLOCK callsign=max` |
| `  [CONCUR:aiden] release on FINAL` (leading space) | YES — `^\s*` permits |
| Multi-line post:<br>`Line 1: status update`<br>`Line 2: [CONCUR:elliot] release` | YES — MULTILINE anchors line 2 |
| `[CONCUR:scout]\n` (trailing newline only) | YES — `(?:\s\|$)` matches newline |

## Test cases — must NOT MATCH (gate passes)

| Input | Expected non-match |
|---|---|
| `I concur with the analysis` | NO match — lowercase + not bracketed |
| `CONCUR with EMPIRICAL CORRECTION on step 2:` | NO match — no bracketed tag |
| `Status: Stream 2 sealed` (factual answer to Dave) | NO match — no governance pattern |
| `[CONCUR:elliotbot]` (callsign typo / bot-suffix) | NO match — callsign not in enum |
| `prefix [CONCUR:elliot]` (not line-start) | NO match (in non-MULTILINE) — but DOES match in MULTILINE if at start of any line. Trade-off → only an issue if someone embeds the tag mid-prose with a leading newline. |
| `[STARTING] KEI-37 design — owned by aiden` | NO match — STARTING is not CONCUR/BLOCK |
| `[PROPOSE:aiden] next item...` | NO match — PROPOSE is not CONCUR/BLOCK |
| `[HOLD:aiden] on Sonar finding` | NO match — HOLD is intentional separate semantic; if HOLD should gate too, add to action alternation. |

### Open design question: HOLD action

Today this session, agents have used `[HOLD:aiden]` to flag a PR-review hold (not the same as `[BLOCK:max]`). Decision needed:
- If HOLD should gate (peer release required to clear), add `HOLD` to the action alternation.
- If HOLD is informational only (author can release self), exclude from regex.

Recommend: **exclude HOLD from gate** — it's an informational PR-review tag, not a governance-coordination claim. Author can clear by amending + re-FINAL.

## Acceptance criteria

- Max can post `[MAX] Status: Stream 2 sealed` directly to #execution without gate-held.
- Max can post `CONCUR with EMPIRICAL CORRECTION on step 2:` prose review without gate-held.
- `[CONCUR:elliot]` actual governance concur still gate-fires correctly.
- Test suite covers all match + no-match rows above with explicit regex_assertions.

## Implementation handoff for Elliot

Files to touch:

1. Locate the gate code (likely in slack_relay.py or a wrapper script — Elliot to point exact path; not in my current path knowledge).
2. Replace the existing pattern with `_CONCUR_GATE_RE` above.
3. Add pytest cases covering the test matrix in §test-match + §test-no-match.
4. Document the in-code-block escape pattern in GOVERNANCE.md.
5. Smoke probe: Max attempts a direct factual post to #execution; verifies no gate-hold.

Estimated: ~30 LoC regex + ~15 LoC test cases + 1 GOVERNANCE.md paragraph.

## Rollback

If the new regex over-narrows and lets a real governance claim slip through, revert via `git revert` of the regex change. The held-CONCUR-stub pattern is informational; missing one doesn't corrupt state.
