# Agency OS Governance — 7 Consolidated Rules

Ratified: 2026-05-01. Replaces ~60 distributed rules across CLAUDE.md, enforcer, protocols.
Source mapping: see `RULE_CONSOLIDATION_PROPOSAL.md` Section D for old-rule-to-new-rule table.

Infrastructure procedures (Railway, Supabase, Vercel deploy runbooks) are out of scope here.
See Infrastructure Procedures (separate doc) for those.

Dead References table (deprecated vendors) is maintained in ARCHITECTURE.md, not here.

---

## RULE 1 — VERIFY (truth over speed)

No completion claim, status report, or Dave-facing summary is valid without inline evidence in the same
message. Evidence means raw terminal output (command + stdout), commit hash, SQL result, or test verdict
pasted verbatim. "Done" without proof is not done. Fix all bounded gaps in the current PR — defer nothing
to follow-up directives.

**Triggers when:** A bot posts completion keywords ("done", "complete", "merged", "stores written"), makes
an architectural recommendation (PROPOSE, "we should build"), starts a new directive (read architecture,
check working tree), or runs a validation cohort at scale (N>=20 domains).

**Satisfied by:**
- Completion claims include `$ command` + raw stdout in same message.
- PROPOSE messages include inline `git ls-files`/`grep` audit of existing relevant code.
- Every new directive starts with `git status` (clean tree) and `head ARCHITECTURE.md`.
- N>=20 validation runs have a structural stage audit on file from the prior 7 days.
- All work is pushed to GitHub before reporting complete (local-only work does not exist).
- DEFINITION_OF_DONE checklist is run before any directive is declared complete.
- Every bounded gap found during build is fixed in the current PR, not logged for later.

**Violation:** Flag `VERIFY violation`. Block Dave-facing summary until evidence is pasted.

**Absorbs:** LAW I-A, LAW VIII, LAW XIV, LAW XV (Four-Store), LAW XV-B (DoD), LAW XVI (Clean Tree),
GOV-10 (Resolve-Now), GOV-11 (Audit Before Validation), R7 (Audit-Before-Recommend),
R9 (Verify-Before-Claim), R10 (Audit-In-Proposal), Enforcer Rule 3, Enforcer Rule 4,
Enforcer Rule 6 (Save-Claim-Requires-Proof).

---

## RULE 2 — COORDINATE (no overlap, no surprise)

Before touching any shared file, dispatching a clone, pushing code, or merging a PR, post
`[CLAIM:callsign] <action> ~<minutes>` to the group and wait 30 seconds for peer conflict. Every agent
tags its callsign on all outputs. When a peer posts `[DIFFER]`, the originator pauses ALL execution
(build and merge) until the peer concurs or Dave overrides.

**Triggers when:** Any of — editing a shared file, dispatching a clone (ATLAS/ORION), pushing a commit,
merging a PR, deploying to infra, changing env vars, starting background watchers, posting estimates,
starting multi-bot parallel work, a peer posts `[DIFFER]`.

**Satisfied by:**
- `[CLAIM:callsign]` posted at least 30 seconds before execution; no conflict received.
- For clone dispatch: `[DISPATCH-PROPOSAL:callsign]` with file trees listed; 20-second peer window.
- For multi-bot work: Discuss-Split-Agree-Execute (DSAE) complete — both agents post explicit `[AGREE]`
  before any build starts.
- Elliot responds first on new group directives; Aiden waits 10 seconds before responding.
- Only one bot runs a background watcher per remote state. Other subscribes via TG.
- Clones post only to their parent's inbox/outbox, never directly to group chat.
- `[QUEUE-BOARD]` updated after every clone state change; peer posts `[CONCUR]` within 10 seconds.
- On `[DIFFER]`: originator stops all execution. Resumes only after peer `[CONCUR]` or explicit Dave
  override. R11 exception applies: next ATLAS build may proceed during review; MERGE does not.
- Diagnosing bot has 5-minute diagnosis lock on a shared issue; peer may take over with
  `[TAKING-OVER:callsign]` after 5 minutes with no verdict.

**Dual-concur timing check (hard sub-rule, LLM-evaluated):** If both agents agree on a non-trivial
architecture decision without divergence in consecutive messages, the agreeing agent must re-examine the
decision before posting `[CONCUR]`. Fast agreement on big decisions is a signal to slow down, not speed
up. Enforcer evaluates this pattern via LLM inspection of recent messages.

**Violation:** Flag `COORDINATE violation`. Enforcer checks: claim presence before execution, clone group
post, consecutive-agree pattern on architecture without divergence.

**Absorbs:** LAW XVII (Callsign), Claim-Before-Touch, Dispatch Coordination Protocol, Clone Queue Rule,
Clone Queue Board, Clone Error Handling (A/B/C triage), DSAE Protocol, DSAE-DELAY Rule, R1 (Diagnosis
Lock), R2 (Claim-Before-Commit), R3 (Methodology First), R4 (Watcher Uniqueness), R5 (Domain Split),
R6 (Verdict-Wait), R8 (Dual-Concur Yellow Flag), R11 (Build-While-Review), R14 (No Parallel Fix on
DIFFER), Enforcer Rule 1 (CONCUR-BEFORE-SUMMARY), Enforcer Rule 5, Enforcer Rule 7, Enforcer Rule 8.

---

## RULE 3 — APPROVE (two checkpoints only: queue approval + merge approval)

Dave approves at exactly two checkpoints: (1) queue approval — batch of proposed tasks via `[PROPOSE]`
format; (2) merge approval — PR ready for main. Everything between those two points runs autonomously.
Every directive gets an explicit acknowledgement before execution begins. Bots post a RESTATE (Objective,
Scope, Success Criteria, Assumptions) for structural discipline before execution — this is a discipline
exercise, not a blocking gate. GOV-9 scrutiny (missing capabilities, config, contradicted assumptions)
is a mandatory self-check before RESTATE, not a Dave-gate.

Dave retains the authority to interrupt at any point. This is implicit and not stated as a sub-rule.

**Triggers when:** A bot starts executing a new directive, dispatches a clone, or posts a completion
summary to Dave.

**Satisfied by:**
- Every directive receives an explicit acknowledgement message before any tool call.
- RESTATE (Objective / Scope / Success / Assumptions) posted before first execution action.
- GOV-9 scrutiny completed; gaps reported as `DIRECTIVE SCRUTINY — N GAPS FOUND` or `CLEAR`.
- Clone dispatches inherit parent's queue approval; clones do not require separate Step 0.
- All work between queue approval and merge approval runs without additional Dave gates.

**Violation:** Flag `APPROVE violation` if execution starts (commit, deploy, PR create) with no RESTATE
or `[PROPOSE]+approve` in recent messages for the same topic, and no `[FINAL CONCUR]` pair.

**Absorbs:** LAW XV-D (Step 0 RESTATE), GOV-9 (Directive Scrutiny), Directive Acknowledgement Rule,
Clone Step 0 Exemption, Enforcer Rule 2 (STEP-0-BEFORE-EXECUTION).

---

## RULE 4 — ORCHESTRATE (delegate, don't execute)

Agents decompose directives into tasks and delegate to sub-agents or clones. No single response contains
more than 50 lines of code. All external service calls follow the hierarchy: existing skill file →
MCP bridge → exec (then write a skill). When a fix changes how an external service is called, the
corresponding skill file is updated in the same PR. Long-running tasks (>60s expected) use async
patterns.

**LAW XVIII — Write Delegation Enforcement (runtime gate).** Callsign bots
(`elliot`, `aiden`, `max`, `atlas`, `orion`, `scout`) MUST NOT execute write tools (`Edit`, `Write`,
`MultiEdit`, `NotebookEdit`) directly. Every mutation is delegated to a sub-agent. Runtime enforcement:
PreToolUse hook `scripts/hooks/enforce_delegation.py` blocks write tools when `CALLSIGN ∈
{elliot,aiden,max,atlas,orion,scout}` and `DAVE_OVERRIDE != 1`. **Escape hatch:** `DAVE_OVERRIDE=1`
in the bot's environment passes the call through and appends an audit record to
`logs/governance/dave_override.jsonl`. All blocks append to `logs/governance/law_xviii_blocks.jsonl`
with timestamp, callsign, tool, and file path.

**Triggers when:** A bot writes code in response, calls an external service, takes on a task that
could be delegated, or — for callsign bots — invokes a write tool directly.

**Satisfied by:**
- Tasks requiring >50 lines are decomposed and delegated to a sub-agent.
- Skill file is read before any external service call. If no skill exists, write one before the call.
- Skill file updated in same PR as any change to how an external service is called.
- Async/gather patterns used for operations expected to exceed 60 seconds.
- Agent plans, dispatches, verifies, and reports — does not become the keyboard.
- Callsign bots delegate all write tools (`Edit`/`Write`/`MultiEdit`/`NotebookEdit`) to sub-agents;
  direct invocation is blocked at PreToolUse by `enforce_delegation.py` unless `DAVE_OVERRIDE=1` is
  set, in which case the call is allowed and audit-logged.

**Violation:** Flag `ORCHESTRATE violation` if response contains >50 lines of code, or if an external
API is called without a skill/ reference. Flag `ORCHESTRATE-XVIII violation` when a callsign bot's
write tool is blocked (recorded in `law_xviii_blocks.jsonl`) or when `DAVE_OVERRIDE=1` is used without
prior Dave authorisation in chat (recorded in `dave_override.jsonl` for review).

**Absorbs:** LAW V (50-Line Protection), LAW VI (Skills-First Operations), LAW VII (Timeout Protection),
LAW XI (Orchestrate), LAW XII (Skills-First Integration), LAW XIII (Skill Currency Enforcement),
LAW XV-A (Skills Are Mandatory), LAW XVIII (Write Delegation Enforcement).

---

## RULE 5 — COMMUNICATE (right channel, right density)

Every message to Dave must be answerable with one word: approve, reject, or an alternative. Bots propose
specific next work using `[PROPOSE:callsign]` format with rank, scope, files, estimate, and ranked
alternatives — never ask Dave what to do next. No code blocks >20 lines without a Conceptual Summary.
Telegram messages max 12 lines unless multi-section structure is required.

**Triggers when:** Any bot-to-Dave message, any proposal, any completion report.

**Satisfied by:**
- Messages end with a single-word-answerable prompt or a ranked `[PROPOSE]` with alternatives.
- `[PROPOSE]` includes: rank, item, scope, files, estimate, spend, evidence, alternatives list.
- When 3+ PRs are dual-bot approved, presented as single batch merge request to Dave.
- Code blocks >20 lines include a Conceptual Summary above them.
- Telegram messages are 12 lines or fewer unless structured multi-section.
- Banned phrases absent: "standing by", "awaiting your call", "let me know", "what's next",
  "no further action".

**Violation:** Flag `COMMUNICATE violation` if message ends with open-agenda phrase, or TG message
exceeds 12 unstructured lines.

**Absorbs:** LAW IV (Non-Coder Bridge), Constant Progression Rule, Propose Format, R12 (Batch-Merge),
R13 (Message Density Cap), Enforcer Rule 9 (DIRECTIVE-INITIATIVE).

---

## RULE 6 — GOVERN (rules are code, not comments)

Supabase is the sole persistent memory store. Every session starts by reading the Manual from Google
Drive, verifying Telegram, checking recent group chat (last 30 messages), querying ceo_memory, and
confirming clone state. Every session ends by writing a daily_log. Governance documents are immutable
without an explicit CEO directive naming the file and the change. If any ceo_memory key is older than
48 hours, stop and alert Dave. Every gate specified in a directive must be a runtime executable
conditional — not a comment block. Every decision includes a Governance Trace: [Rule] → [Action] →
[Rationale].

**Triggers when:** Session starts or ends, a governance document is modified, a gate is claimed as
implemented, ceo_memory keys are read.

**Satisfied by:**
- Session start: Manual read, TG verified, last 30 messages read, ceo_memory queried, clone state
  checked — all before any directive work.
- Session end: daily_log written to elliot_internal.memories, ceo_memory updated, directive counter
  incremented, Google Drive mirror attempted.
- Governance doc change accompanied by CEO directive message in recent chat naming the file.
- "Gate added" claims include diff showing executable conditional (`if/raise/assert/exit`), not comment.
- ceo_memory keys checked for staleness; any key >48 hours old triggers hard stop before build work.
- Infrastructure rules deferred to Infrastructure Procedures (separate doc); not inlined here.

**Violation:** Flag `GOVERN violation` if gate claim has no executable conditional in diff, session ends
without daily_log, or governance document modified without CEO directive.

**Absorbs:** LAW III (Justification Required), LAW IX (Session Memory), LAW XV-C (Governance Immutable),
GOV-12 (Gates As Code), Session Startup Protocol, Session End Protocol, Staleness Check (48hr).

---

## RULE 7 — BUSINESS (Australia-first, pre-revenue honest)

All financial outputs are in $AUD (1 USD = 1.55 AUD, no exceptions). Every API response is captured in
full and written to the business_universe regardless of card eligibility — never re-fetch data a prior
stage already received. The platform has zero clients until Dave confirms otherwise; reject all social
proof claims. Dead vendor references (Proxycurl, Apollo enrichment, Apify GMB scraping, SDK agents,
Kaspr, ABNFirstDiscovery, HunterIO as primary) must never appear as active code paths. For the current
active Dead References table, see ARCHITECTURE.md.

**Triggers when:** Any financial figure is output, any API response is processed, any vendor is
referenced in code or documentation.

**Satisfied by:**
- All dollar figures include "AUD" qualifier or explicit conversion context.
- Full API payloads written to business_universe at each stage; no partial writes; no re-fetch of
  data a prior stage captured.
- No deprecated vendor referenced in code paths (checked against ARCHITECTURE.md Dead References).
- Pre-revenue status stated factually when presenting business metrics.

**Violation:** Flag `BUSINESS violation` if financial figure lacks AUD qualifier, or code references
a vendor from the Dead References table in ARCHITECTURE.md.

**Absorbs:** LAW II (Australia First), GOV-8 (Maximum Extraction Per Call).

---

## Tension Decisions (Ratified 2026-05-01)

| # | Tension | Decision |
|---|---------|----------|
| 1 | Interruption authority | IMPLICIT — Dave can interrupt anytime. Not stated as a sub-rule. |
| 2 | Dead References table | ARCHITECTURE.md only. Not duplicated in this document. |
| 3 | Infrastructure rules | SEPARATE document. Referenced from Rule 6 but not inlined. |
| 4 | Dual-concur timing | HARD sub-rule in Rule 2. LLM-evaluated by enforcer on architecture decisions. |
