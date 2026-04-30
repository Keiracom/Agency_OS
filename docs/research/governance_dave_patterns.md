# Track 3 — Dave Behavioural Patterns

Read-only research. Surfaces UNSTATED rules implicit in Dave's directive style + corrections, derived from sources accessible to ORION (clone callsign):

**Sources scanned**

- `~/.claude/CLAUDE.md` (240 lines — global all-callsign governance) + `./CLAUDE.md` (172 lines — Agency OS project governance). Each rule's "Ratified <date> per Dave directive" line is a primary source for behavioural patterns: each rule is a behavioural correction Dave issued.
- `public.ceo_memory` via mcp-bridge — 15 most-recent keys including `ceo:rules.r9_r14`, `ceo:rules.r7_r8`, `ceo:coordination_rules_2026-04-30`, `ceo:demo_migration_directive`, `ceo:investor_roadmap_2026-04-29`.
- `elliot_internal.memories` via mcp-bridge — 12 most-recent rows of type `decision` with Dave-attributed content.
- `/tmp/telegram-relay-orion/processed/` — 30 inbound TG-relayed dispatches consumed by this clone (2026-04-22 onward). These are bot-to-clone dispatches that reference Dave directives.

**Source limit honesty**

ORION (clone) does not have direct read access to Dave's verbatim TG messages — the parent bot (AIDEN) consumes raw TG and dispatches to the clone via inbox JSON. Verbatim Dave quotes here come from rule provenance comments + memory-stored Dave-attributed text, not from the TG group log. Patterns are derived from behavioural CORRECTIONS Dave issued (encoded as rules) and DIRECTIVE TEXT preserved in `ceo_memory`.

**Branch**: `aiden/governance-audit-tracks-3-4` (off `origin/main`). No code edits — doc-only.

## Methodology

Each pattern is derived from one of three primary signals:

1. **Rule provenance** — every rule in CLAUDE.md ends with `Ratified <date> per Dave directive`. The act of ratifying a rule is evidence Dave wanted that behaviour. Pattern frequency = count of related rules.
2. **Directive text in memory** — `elliot_internal.memories type=decision` carries Dave's directive text near-verbatim with timestamps.
3. **Correction artefacts** — when a rule supersedes another (e.g. "Propose Format supersedes Directive Initiative Rule"), Dave is correcting an earlier-tried behaviour.

---

## Pattern 1 — Step 0 RESTATE before any action

**Frequency:** mentioned 3 separate times in CLAUDE.md (LAW XV-D enforcement section + Step 0 in EVO Protocol + clone exemption protocol). Re-flagged retroactively in 2026-04-26 ABN sweep session ("Step 0 RESTATE retroactively flagged twice by Enforcer — pattern fix logged").

**Examples:**
- 2026-04-XX (LAW XV-D ratified, before April): "Skipping Step 0 is a LAW XV-D violation. No exceptions, no shortcuts, no jumping ahead because the task seems simple. Every directive, every time."
- 2026-04-24 (Clone Step 0 Exemption): "Clone dispatches are pre-approved by the dispatching bot... Clones do NOT wait for Step 0 approval — they execute on receipt. Clone writes a brief INTERPRETATION_RESTATE to its outbox as first act."
- 2026-04-26 (governance log in `docs/ops/abn_match_sweep_2026-04-26_run.md`): "Step 0 RESTATE: retroactively flagged twice this session by Enforcer. Pattern fix is in this very dispatch — RESTATE block included inline."

**Implicit rule:** Dave wants every directive interpretation surfaced in writing BEFORE any tool call. No "I think I understand, let me just start". The cost of a wrong interpretation is far worse than the 30-second pause to write a restate.

**Currently a rule?** Yes — LAW XV-D (HARD BLOCK) + Clone Step 0 Exemption (clones write to outbox).

**Recommended:** Already encoded. Pattern is **stable** — Enforcer caught violations and the system corrected. No new rule needed.

---

## Pattern 2 — Australia / AUD always, never USD

**Frequency:** 1 explicit law (LAW II) + repeated reinforcement in cost reports + ABN sweep cost notes ("AUD 0 spend").

**Examples:**
- LAW II text: "Australia First — all financial outputs in $AUD (1 USD = 1.55 AUD). No exceptions."
- 2026-04-25 BU Closed-Loop S1 outbox: "AUD 0 spend... pure local SQL via asyncpg, no API calls."
- ABN sweep 2026-04-26 docs/ops log: "AUD spend audit: 0 — local SQL only across all five attempts."

**Implicit rule:** every cost reference must be AUD-stated even when the underlying API quotes USD. Dave models the business in AUD because the customers + agency-deal economics are AUD.

**Currently a rule?** Yes — LAW II (HARD BLOCK).

**Recommended:** Stable. Bots have internalised this — no recent violations.

---

## Pattern 3 — Plain-English over jargon; raw output over summary

**Frequency:** 2 laws (LAW IV Non-Coder Bridge + LAW XIV Raw Output Mandate) + 1 rule (R9 Verify-Before-Claim, ratified 2026-04-30) + 1 rule (R13 Message Density Cap, 2026-04-30).

**Examples:**
- LAW IV: "Non-Coder Bridge — no code blocks >20 lines without Conceptual Summary."
- LAW XIV: "Raw Output Mandate — paste verbatim terminal output, never summarise."
- R9 (2026-04-30): "Verify-Before-Claim — every completion claim must include raw verification command output (`$ command` + stdout) in the same message. 'Complete' without paste = violation."
- R13 (2026-04-30): "Message Density Cap — TG messages max 12 lines unless multi-section structure explicitly required."

**Implicit rule:** Dave is a non-coder CEO who needs to verify bot claims without reading source. Solution: bots paste real output (proves the code ran), summarise concepts (so Dave can audit the logic), and don't pad messages with prose Dave will skip.

**Currently a rule?** Yes, multiply — across 2 laws + 2 rules. Suggests recurring violation despite the law existing → rule sprawl.

**Recommended:** **Consolidate.** LAW XIV + R9 cover the same ground (raw output). Suggest folding R9 into LAW XIV-B: "Every completion paste = the actual command and its stdout, never a paraphrase." LAW IV + R13 cover the same intent (don't dump unsummarised content on Dave) — but LAW IV is about technical content, R13 is about TG prose volume. They're complementary; keep separate.

---

## Pattern 4 — Audit existing code BEFORE recommending new code

**Frequency:** 1 rule (R7 Audit-Before-Recommend) + 1 rule (R10 Audit-In-Proposal) + 1 GOV (GOV-9 Two-Layer Directive Scrutiny) + 1 GOV (GOV-11 Structural Audit Before Validation). All ratified inside a 9-day window 2026-04-22 → 2026-04-30.

**Examples:**
- R7 (2026-04-30): "Both bots must audit existing codebase before any build recommendation. Origin: both bots proposed 4-week rebuild without auditing existing 68-component React app. Dave caught it." (per `ceo_memory.ceo:rules.r7_r8`)
- R10 (2026-04-30): "Every `[PROPOSE]` or 'we should build/rebuild/migrate X' message must include git ls-files/grep/find audit output showing existing relevant code. No architecture recommendation without inline inventory."
- GOV-9: "every directive triggers Layer 2 CTO scrutiny before Step 0. Report DIRECTIVE SCRUTINY — N GAPS FOUND or CLEAR before any execution."

**Implicit rule:** Dave does not trust unaudited recommendations — he's been burned by bots proposing rebuilds when something already exists. The pattern repeats often enough that THREE separate rules now codify the same behaviour.

**Currently a rule?** Yes, multiply.

**Recommended:** **Rule sprawl signal.** R7 + R10 + GOV-9 cover overlapping behaviour. Consolidate to one canonical "Audit-First" law. Possibly LAW XIX or extend LAW I-A (Architecture First). The triple-codification is itself evidence that Dave does NOT trust the rule to fire — bots aren't internalising it. Recommend a runtime CHECK (e.g. PR description must contain a `## Audit` section with grep output), not another text rule.

---

## Pattern 5 — Coordinate before parallel work; no overlap

**Frequency:** 1 rule (R5 Domain Split First) + 1 protocol (DSAE — 2026-04-23) + 1 rule (R2 Claim-Before-Commit) + 1 protocol (Claim-Before-Touch, 2026-04-18) + 1 protocol (Dispatch Coordination, 2026-04-23) + 1 rule (R4 Watcher Uniqueness) — **6 separate codifications**.

**Examples:**
- 2026-04-30 ceo_memory `ceo:coordination_rules_2026-04-30`: "9 overlap instances catalogued in TG discuss phase 2026-04-30. Ratified after PR #451 cycling exposed R5/R6 self-test failure on first action."
- 2026-04-23 (DSAE Protocol): 4-step gate (Discuss → Split Tasks → Agree → Execute) for "any significant multi-bot task".
- 2026-04-25 (Clone Queue Board): both bots maintain `[QUEUE-BOARD]` posts to verify peer-clone state before dispatch.

**Implicit rule:** Dave is watching two bots collide on the same files / same problem repeatedly. Rules cover different blast radii (file-level Claim, dispatch-level Domain Split, watcher-level Uniqueness, full-task DSAE) but the underlying behaviour is the same: peer awareness before action.

**Currently a rule?** Yes, six times.

**Recommended:** **Highest rule sprawl in the system.** 6 rules covering "coordinate before parallel work" suggests the rules don't fire reliably — bots agree but then forget mid-task. Recommend a runtime ENFORCER (the `enforcer_bot.py` mentioned in `~/.claude/CLAUDE.md` ratification note) that AUTOMATICALLY blocks actions on shared files without prior `[CLAIM]`. Rules-as-text don't beat habit; rules-as-runtime do.

---

## Pattern 6 — Constant progression, never "what's next"

**Frequency:** 1 rule (Constant Progression Rule, 2026-04-25) + 1 rule (Directive Initiative Rule — superseded) + 1 rule (Propose Format, 2026-04-25 — supersedes the Initiative rule).

**Examples:**
- Constant Progression Rule: "Every message to Dave MUST be answerable with one word: `approve`, `reject`, or an alternative task name. Banned: 'standing by', 'awaiting your call', 'let me know', 'what's next', 'no further action'. Silence is allowed; passive prompts are not."
- Propose Format (supersedes Directive Initiative Rule): "Bot auto-cascades to rank 2 without re-prompting Dave. On alternative: bot pivots immediately."

**Implicit rule:** Dave's time is the bottleneck, not the bots'. Bots should propose ranked options + execute the top one when approved + cascade automatically when rejected. Dave's input is a one-word approve/reject/redirect, not a debate.

**Currently a rule?** Yes (Constant Progression + Propose Format).

**Recommended:** Stable in 2-rule form. The supersession (Directive Initiative → Propose Format) is the system self-correcting. No new rule needed.

---

## Pattern 7 — Verify yourself first; show evidence not claims

**Frequency:** R9 Verify-Before-Claim (2026-04-30) + LAW XIV Raw Output Mandate + LAW XV-B DoD Is Mandatory + GOV-12 Gates As Code Not Comments. **4 codifications** of the same trust pattern.

**Examples:**
- LAW XV-B: "DoD Is Mandatory — cat DEFINITION_OF_DONE.md before reporting complete."
- GOV-12: "Gates As Code — runtime enforcement required, not documentation-only. Reports of 'gate added' require evidence of executable conditional, not comment block. Gates as comments create false confidence."
- R9 (2026-04-30): "raw verification command output (`$ command` + stdout) in the same message. 'Complete' without paste = violation."

**Implicit rule:** Dave doesn't trust "complete" until he sees the actual command output. Bots have a habit of optimistic-completion ("tests pass" without showing the pytest output) and Dave repeatedly catches it.

**Currently a rule?** Yes, four times.

**Recommended:** Consolidate (similar argument to Pattern 4). The ABN sweep session (2026-04-26) showed all four rules firing simultaneously — verification log + raw stdout paste + DoD checklist + the gate-as-code statement_timeout fix. Working. Recommend keeping all four but flagging in a "Verification Stack" meta-document so future bots see the full chain.

---

## Pattern 8 — Pause-and-escalate on uncertainty; never autonomous re-attempt

**Frequency:** 1 rule (R14 No Parallel Fix on DIFFER, 2026-04-30) + 1 rule (R6 Verdict-Wait, 2026-04-30) + Clone Error Handling Protocol (2026-04-25) + Cat-B addendum on the ABN sweep dispatch (2026-04-26).

**Examples:**
- R14: "When peer posts `[DIFFER]`, originator pauses ALL execution (including fix attempts) until peer concurs or Dave overrides. No pushing fixes mid-diagnosis."
- 2026-04-26 ABN sweep Cat-B addendum (per ORION outbox): "If anything fails: outbox task_error JSON with category... Do NOT improvise — report. On Cat-B-class halt again: outbox task_error + tg -g [ESCALATE:ORION] — STOP. Do NOT auto-recover beyond the wrapper."

**Implicit rule:** When something goes wrong, bots have a habit of trying to fix it themselves with another tool call. Dave wants the chain to STOP and escalate so he can decide whether to retry / pivot / abandon. Autonomous re-attempt = blast radius growth.

**Currently a rule?** Yes (R14 + R6 + Clone Error Handling Cat-B).

**Recommended:** Stable. The 2026-04-26 ABN sweep session was a clean live-fire test — bots halted at multiple points (v1 Cat-B, v2 Cat-B, v4 pre-launch halt) and escalated each time. Pattern internalised.

---

## Pattern 9 — Four-store completion; no half-saves

**Frequency:** LAW XV (Four-Store Completion) + LAW XV-A (Skills Are Mandatory) + LAW XV-B (DoD Is Mandatory) + LAW XV-C (Governance Docs Immutable) + LAW XV-D (Step 0 RESTATE). The XV-family is **5 sub-laws** all about completion discipline.

**Examples:**
- LAW XV: "A directive is NOT complete until ALL FOUR are written: docs/MANUAL.md + ceo_memory + cis_directive_metrics + Google Drive mirror."
- LAW XV-C: "Governance Docs Immutable — never recreate/modify without explicit CEO directive."
- 2026-04-17 memory entry "LAW XVIII REVOKED": "Step 0 RESTATE posted; Dave rejected ambiguous 'Yes'... rule revocation must be unambiguous." Single-letter Dave responses to ambiguous Yes/No rejected.

**Implicit rule:** A directive isn't done until it's surfaced everywhere it might be looked-for next session. Single-store saves (e.g. only commit message, no Manual update) cause "I don't see it" friction next session.

**Currently a rule?** Yes, multiply.

**Recommended:** Stable. The XV-family is internally cohesive. Suggest grouping presentation (single "Completion Discipline" section in Manual) but not collapsing rules.

---

## Pattern 10 — Fast agreement is suspect; slow down on big decisions

**Frequency:** 1 rule (R8 Dual-Concur Yellow Flag, 2026-04-30).

**Examples:**
- R8: "If both bots agree on a non-trivial architectural question in under 60 seconds, the agreeing bot must re-check before posting concur. Fast agreement on big decisions is a signal to slow down, not speed up."
- Origin per `ceo_memory.ceo:rules.r7_r8`: "Both bots proposed 4-week rebuild without auditing existing 68-component React app."

**Implicit rule:** Dave has noticed the bots do "yes, agreed" / "looks good" within 30 seconds on architecture questions and then both turn out to be wrong. He wants friction on big decisions specifically, NOT on small ones (the small ones benefit from fast iteration).

**Currently a rule?** Yes — R8.

**Recommended:** Stable. R8 is the newest member of this family (today, 2026-04-30) and was triggered by a concrete recent failure. Watch for recurrence of fast-agree-then-wrong pattern over the next 30 days; if it persists, extend to require explicit "I disagree because..." or "I checked X..." rather than just `[CONCUR]`.

---

## Pattern 11 — One-word Dave responses; bots never fish for clarification

**Frequency:** Constant Progression Rule + Propose Format (cascade on reject + pivot on alternative). Both 2026-04-25.

**Examples:**
- Propose Format spec: "Approve | Reject (cascade to rank 2) | Alternative (Dave names another)"
- "On reject: bot auto-cascades to rank 2 without re-prompting Dave. On alternative: bot pivots immediately, re-proposes the new path with alternatives."
- 2026-04-17 LAW XVIII revocation: "Dave rejected ambiguous 'Yes' (per LAW XVIII rule 5 that was being revoked — rules require unambiguous yes/no)."

**Implicit rule:** Dave's input bandwidth is one-word. Bots that fish for clarification ("did you mean A or B?") burn his bandwidth. The Propose Format pre-empts: bots offer ranked options upfront so Dave can pick by ordinal.

**Currently a rule?** Yes — Propose Format codifies it.

**Recommended:** Stable. Side note: Dave's own messages are typically one-word responses or terse directives, modelling the protocol himself.

---

## Pattern 12 — Decisions get stored in 4+ places (Manual / ceo_memory / commit / TG)

**Frequency:** LAW XV (Four-Store Completion) + LAW IX (Session Memory: Supabase as SOLE persistent memory) + ratification storage_locations field on every R-rule (e.g. coordination_rules_2026-04-30 lists 7 storage locations).

**Examples:**
- `ceo_memory.ceo:coordination_rules_2026-04-30.storage_locations` lists 7 separate stores: ~/.claude/CLAUDE.md, ~/clawd/Agency_OS-aiden/CLAUDE.md, ~/clawd/CLAUDE.md, ceo_memory, elliot_internal.memories, docs/MANUAL.md, ENFORCE.md.

**Implicit rule:** Single-store storage = forgotten next session. Dave has been burned by "I told you that already" → bot says "I don't have memory of it" → because it was only in TG. Every ratified decision now hits multiple stores so any session-startup query finds it.

**Currently a rule?** Yes — LAW XV + LAW IX combined.

**Recommended:** **Effective but expensive.** 7-store writes per rule add operational drag. The system is currently saying "save everywhere because we don't trust any one store." A trust-the-canonical (CLAUDE.md global file) + auto-mirror would reduce drag. Recommend pilot: pick CLAUDE.md global as canonical, generate the 6 mirrors via a sync script.

---

## Closing summary

### Pattern → rule sprawl mapping

| Pattern | Codifying rules | Sprawl level |
|---|---|---|
| 1 — Step 0 RESTATE | 2 (LAW XV-D + Clone Exemption) | low |
| 2 — AUD always | 1 (LAW II) | none |
| 3 — Plain English / raw output | 4 (LAW IV + LAW XIV + R9 + R13) | medium |
| 4 — Audit before recommend | 4 (R7 + R10 + GOV-9 + GOV-11) | **high — recommend consolidate** |
| 5 — Coordinate before parallel | 6 (R5 + DSAE + R2 + Claim-Before-Touch + Dispatch Coord + R4) | **highest — recommend runtime enforcer** |
| 6 — Constant progression | 2 (Constant Progression + Propose Format) | low (self-corrected) |
| 7 — Verify before claim | 4 (R9 + LAW XIV + LAW XV-B + GOV-12) | medium |
| 8 — Pause-and-escalate | 3 (R14 + R6 + Clone Error Handling) | low |
| 9 — Four-store completion | 5 (LAW XV + XV-A + XV-B + XV-C + XV-D) | medium (cohesive family) |
| 10 — Fast agreement is suspect | 1 (R8) | none (new) |
| 11 — One-word Dave responses | 2 (Constant Progression + Propose Format) | low |
| 12 — Multi-store decisions | 2 (LAW XV + LAW IX) | low (operational drag) |

### Top 5 findings

1. **R-rules emerged in clusters today (2026-04-30).** R1-R6 ratified together (overlap fix); R7-R8 same day (audit-before-recommend); R9-R14 same day (verify+audit+performance). 14 rules in one session = symptom of broad behavioural pivot, not gradual codification.

2. **Highest rule sprawl is "coordinate before parallel work"** — 6 separate codifications. Pattern is real but rules don't fire reliably; recommend runtime enforcer over more text rules.

3. **Audit-before-recommend pattern is rule-sprawled** (R7 + R10 + GOV-9 + GOV-11) but bots still missed the React app inventory (per ceo_memory.ceo:rules.r7_r8 origin: "both bots proposed 4-week rebuild without auditing existing 68-component React app"). Text rule alone is insufficient.

4. **Four-store completion (LAW XV family) is internally cohesive** — XV through XV-D form a discipline cluster; recommend grouping presentation but not collapsing rules.

5. **One-word Dave responses (Constant Progression + Propose Format)** is the cleanest pattern — Dave models the protocol himself in his TG style. Bots have internalised it.

### Recommended actions

1. **Consolidate Pattern 4 (audit-before-recommend)** — promote to LAW XIX or extend LAW I-A. Replace the 4 text rules with one law + 1 runtime check (PR description must contain `## Audit` section with grep output).
2. **Pattern 5 runtime enforcer** — extend `enforcer_bot.py` to auto-block tool calls on shared-allowlist files without prior `[CLAIM:<callsign>]`. 6 text rules can collapse to 1 law + 1 code check.
3. **Watch R8 for 30 days** — fresh rule (today). Will tell us if "fast agreement is suspect" pattern persists or was a one-off.
4. **Multi-store decision pilot** — try canonical-CLAUDE.md + auto-sync script for one rule cycle, measure operational time saved.
5. **No new rules until 30-day stability check** — system absorbed 14 rules today. Adding more before measuring impact risks further sprawl.

---

*This document is research-only. No code edits. Generated 2026-04-30 on `aiden/governance-audit-tracks-3-4` branch.*
