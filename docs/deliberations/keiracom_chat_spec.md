# Keiracom Chat + Voice Interface — Concurred Specification

**Deliberators:** Elliot (implementation-feasibility + synthesis), Aiden (architecture +
competitive), Max (cost + quality). **Status:** full 3-way concur — `[CONCUR:elliot]`
`[CONCUR:aiden]` `[CONCUR:max]`. Dave directive 2026-05-20, one-session deliberation.

**The reframe (foundation):** the chat interface IS the product. The dashboard is the
audit trail of what the chat caused to happen. A customer opens Keiracom and *talks* to
it — text or voice — and the fleet does the work. Threads, spend, activity, integrations
are what you check to *verify*; chat is where you *direct*.

**The Face:** an ephemeral agent that spawns on each message. It has the last 20 messages,
identity + governance from Cognee, context recalled from Weaviate, live thread state from
the Dispatcher, spend from spend_tracker, the audit trail, all integrations, and the
ability to dispatch tasks to the thread pool or answer directly. It terminates after
responding; the next spawn resumes from persistent memory.

Function + behaviour only — no colours or aesthetic style.

> **Supersedes:** this spec's §1 changes the default landing surface from *Threads* (set
> in `ceo:deliberation:keiracom_dashboard_spec`) to **Chat**. The dashboard spec stays
> valid — its navigation, views, and cards remain — but demoted to the verification layer
> one click from chat. Where the two docs differ on the entry surface, this doc governs.

---

## 1. Chat interface placement and structure

**Chat is the default landing surface — a full surface, not a slide-in widget.** A
widget would frame chat as secondary; the reframe makes it the room you enter.

**Layout — chat-primary with a persistent fleet rail:**
- **Centre — the conversation.** Full-height message stream + composer. Where the user
  directs.
- **Persistent fleet rail** (compact, always visible alongside chat) — live thread states
  (running / idle / blocked / failed), the thread-capacity meter, the fleet-health dot.
  The user directs AND sees verification in one glance, never leaving chat to know the
  fleet is OK. The rail is the bridge from chat to the dashboard.
- **Dashboard views** (Threads / Spend / Activity / Integrations / Alerts / Settings) —
  routes one click away, the audit layer. You go there to verify, not to operate.
- The dashboard-spec header persistent elements (capacity meter, fleet-health dot,
  command-K) carry over.

**Empty state for a new user** (post-onboarding; BYO-key already gated): not a blank box.
Show — (a) 3-4 example directives phrased as things you *say* ("Ask me to audit a repo",
"Have the fleet research X"); (b) current fleet state (likely 0 / idle threads) so the
user sees the resource they are about to direct; (c) one line on the interaction model —
"Describe what you want. I'll refine it with you, then dispatch the fleet." The empty
state teaches the verb set.

## 2. Message types and response shapes

Six response shapes, each a distinct card in the stream. **Cross-cutting rule:** every
card showing a number (spend, count, duration, ETA) is backed by a real query with an
as-of timestamp — no fabricated figures, ever.

- **Plain text answer** — the Face answered directly, no dispatch. Text + optional inline
  live data + any memory-recall chips (§4). Any number is a live queried value, labelled
  as-of. Actions: copy, "actually, do this" (escalate to a task).
- **Clarifying question** — the Face needs detail before it can brief a task. Question +
  optional quick-pick chips. Action: answer inline.
- **Task-confirmation card (pre-dispatch — REQUIRES APPROVAL)** — the core card. Before
  the fleet does any work the Face shows what it will do. Contents: refined brief
  (objective, scope in/out, definition of success); threads it will occupy / dispatch to;
  **cost expectation** (estimated BYO-key token spend + estimated wall-clock);
  integrations it will touch — with irreversible / external actions (emails sent, PRs
  opened) called out explicitly. Actions: **Confirm** (dispatches) / **Edit** (reopens
  the brief, → §6) / **Cancel**. Nothing dispatches without Confirm. Data: the Face's
  refined brief + Dispatcher capacity + the cost estimator (see §2 build note).
- **Task-dispatched card** — work started: task id, assigned thread(s), dispatched-at,
  live state, updates in place as the thread runs. Actions: open thread detail, pause,
  cancel.
- **Task-completed card** — the outcome: result (success / partial / failed), artifacts
  (PR links, commits, files, messages sent), **actual token spend shown beside the
  pre-dispatch estimate** (closes the cost-promise loop — how the customer learns to
  trust estimates), duration, link to the audit record. Actions: view audit detail, open
  artifacts, follow-up.
- **Error card** — what failed, at which stage (Face / dispatch / execution / integration
  / core service), plain-language honest cause, and **spend incurred before the failure**
  ("$X consumed before this failed"). Actions: retry, edit-and-retry, abandon, view logs.

**Cost-field rule (concurred):** the confirmation card's cost expectation is an honest
field — a real estimate WITH a stated basis ("~X–Y tokens, from N similar past tasks")
once the pre-dispatch estimator exists; "estimate unavailable — actual will be metered"
until then. **Confirm is NEVER gated on the estimate being present** — the estimate field
is informational; the user may dispatch accepting metered-actual. Actual spend is always
shown on the completed card regardless.

**Build gap:** spend_tracker meters actual spend *after* the fact. A pre-dispatch cost
*estimator* does not exist — it is a named build gap. Until it ships, the card shows
"estimate unavailable."

## 3. Processing transparency — submit to response

The Face does real, discrete work between submit and response. The display shows the
**actual current step**, advancing as each completes — not a spinner, not a fake progress
bar (the Face cannot know % complete; a bar would be a lie).

**The Face's real per-message sequence:** spawn → load the 20-message window → recall
identity + governance from Cognee → recall context from Weaviate → query live thread
state from the Dispatcher → conditionally query spend → route decision (answer directly
vs dispatch) → (if dispatch) claim a thread + hand off → compose response → terminate.

**The display** streams these as named steps, each resolving with a concrete result:
- "Recalling context…" → "Found 3 relevant items from memory" / "no prior context"
- "Checking the fleet…" → "6 threads — 4 running, 2 idle"
- "Checking spend…" → "$12.40 this cycle, within budget" (only if the message implicates cost)
- "Deciding…" → "This needs the thread pool" / "I can answer this directly"

**Integrity rules (hard requirements):**
- Show only steps that *actually ran*. If the Face skipped memory recall, do NOT show
  "Recalling context" — a fake step is a fake progress bar by another name.
- Each step resolves visibly with its result; the processing trace is itself the trust
  artifact — proof the Face did real work, not a canned reply.
- A step that takes longer simply sits longer (honest latency). A failed step says so
  ("Memory layer slow — answering from recent context only"), never hangs.
- After the response lands, the steps collapse to a one-line expandable summary
  (Claude Code / Cursor pattern).

**Build gap:** the Face must be instrumented to emit a per-step status event, streamed to
the chat UI (websocket / SSE). The steps are real; the streaming instrumentation is new.

## 4. Conversation continuity and memory surfacing

The Face is ephemeral; memory is persistent. Each spawn resumes from the 20-message
window + Cognee (identity / governance) + Weaviate (recalled context).

- **The 20-message window is ordinary scrollback** — present it as normal chat history,
  no special treatment. Within it, continuity is implicit; the Face refers to recent
  messages naturally, no marker needed.
- **Long-term memory surfaces as explicit recall chips.** When the Face uses a Weaviate
  recall it shows an inline chip on that message — "recalled: [topic], from [date]" —
  and clicking it expands the recalled record. The user never wonders "did it remember?"
  — a chip is present or it is not.
- **Returning session:** the Face opens by signalling continuity — "Last time we worked
  on X; since then 2 tasks finished" (ties to §7).

**Data-integrity requirements (hard — quality lens, non-negotiable):**
- A recall claim MUST be backed by a real Weaviate retrieval of a real stored record.
  "from 3 days ago" = the record's actual `created_at` — never estimated, never fabricated.
- The recall chip links to its source record so the customer can VERIFY it, not just
  trust it (same traceability principle as the dashboard audit trail).
- If the Face has no recall it says so plainly — "I don't have prior context on that." It
  NEVER confabulates a memory. A fabricated recall is the single worst trust failure a
  chat-first product can have — it poisons every subsequent claim the Face makes.
- Window-boundary honesty: a referenced message aged out of the 20-window AND absent from
  Weaviate → "that's beyond what I have," not a half-memory.
- Memory writes are inspectable — the customer can view "what I'll remember from this".

**Build gap:** Weaviate / Cognee recall exists; the per-message Face-spawn wiring and the
recall-chip provenance plumbing are new.

## 5. Voice interface

- **Voice is a MODE within chat, not a separate entry point.** Same Face, same
  conversation, same persistent memory, same thread pool, same cards — only the I/O
  channel changes. A user can toggle text ↔ voice mid-conversation; continuity holds
  across the switch. A separate "voice app" would fork state.
- **Visual layer during audio:** a listening / processing indicator; a **live transcript**
  of what was heard (so the user catches misrecognition immediately) and of the Face's
  spoken reply; the §3 processing steps still render visually during a voice turn (voice
  removes the discrete "submit" moment — processing overlaps with the user still speaking
  or thinking).
- **Response shape: audio + transcript always.** Audio-only is unsafe and destroys the
  conversation record. For structured output (a task-confirmation card) the response is
  audio + the full card rendered visually.
- **Task-confirmation mid-voice — approval is visual + deliberate.** A dispatch spends the
  customer's money and runs the fleet; it must NEVER be approvable by audio alone — a
  misrecognised "yes" cannot commit spend. When the Face reaches a dispatch point in a
  voice session it narrates the brief ("I've drafted this — 6 threads, about $4 — confirm
  on screen or say a clear yes"), the confirmation card renders visually, and approval is
  an explicit visual tap OR a deliberate confirm-back with read-back. **Cost-safety rule:
  a voice misrecognition must never trigger a spend-bearing or irreversible dispatch.**
- Voice is for *directing* and *deliberation* (§6 is natural in voice); confirmation and
  verification stay visual.

**Build gap:** the voice visual layer (waveform / live transcript / steps-during-audio).

## 6. The deliberation flow before work starts

A user describes an idea loosely; the Face refines it into a dispatchable brief before
any thread picks it up. This is the customer-facing equivalent of the internal Step-0
restate — a mini-RESTATE.

- **Clarifying questions are capped at 2-3** — only what materially changes the brief or
  the cost; batched, never an interrogation. Where the Face can reasonably infer, it
  infers and shows the inference as a stated assumption on the confirmation card for
  correction — surfacing an assumption to be corrected beats asking another question.
- **If still ambiguous after 2-3 rounds,** the Face presents its best-guess brief with
  the assumptions explicitly marked — it does not loop forever.
- **The task-confirmation card IS the deliberation output / final brief** (§2): objective,
  scope in/out, definition of success, threads, cost expectation, integrations / external
  actions, key assumptions. Editable inline.
- **The user confirms explicitly** — Confirm is the only thing that dispatches; the Face
  never silently re-interprets. For a multi-task request the Face proposes a small ordered
  set of confirmation cards, not one monolith — the user confirms / cancels each.

## 7. Notification and background surfacing

Tasks run on the thread pool and finish whether or not chat is open. (Research: Linear
surfaces background work as a notification + the record updates in place; Vercel pushes a
completion notification + the row flips state — common pattern: push on completion, hold
the result where the user returns, badge the entry point.)

**Keiracom — three layers:**
1. **On completion** — an in-app toast if the user is in the product; if not, the
   configured channel (email / Slack, via integrations the user already connected). The
   user is never silently left wondering.
2. **Held in chat** — the task-completed card waits in the conversation as unread; the
   chat / nav entry carries a count badge.
3. **The Face reintroduces it.** Because the Face is ephemeral but memory is persistent,
   the next spawn reads "tasks completed since last user interaction" and *leads the
   conversation with them* — a Face-composed summary with links to the audit entries, not
   a raw dump: "While you were away, 2 tasks finished — here's what shipped…" The user
   re-enters into a briefing, not a backlog.

**The async reintroduction still shows actual-vs-estimated spend** — the cost loop closes
even when the user was not watching.

Data: task lifecycle events from the Dispatcher + audit trail; user presence (in-product
vs away); connected notification integrations; the "last user interaction" timestamp from
persistent memory.

**Build gap:** in-app toast + presence detection + the "completed-since-last-interaction"
query are new; the audit trail and the email/Slack integrations that carry the
out-of-product notification largely exist.

---

## Cross-cutting hard requirements (carried verbatim, 3-way concur)

1. Every number shown (spend, count, duration, ETA) is backed by a real query with an
   as-of timestamp — no fabricated figures.
2. No fabricated recall — a recall chip must link to a real stored record; absent a
   recall the Face says so plainly and never confabulates.
3. Never display a processing step that did not actually run.
4. Voice cost-safety — a misrecognition must never trigger a spend-bearing or irreversible
   dispatch; cost-bearing approval is visual + deliberate.
5. Actual-vs-estimate is shown on task completion (and on async reintroduction) — the cost
   promise loop always closes.

## Build gaps (between this spec and a shippable chat product)

- Per-step Face status streaming (websocket / SSE) — drives §3.
- Pre-dispatch cost estimator — drives the §2 confirmation-card cost field.
- Voice visual layer — waveform, live transcript, steps-during-audio.
- Background notification transport + presence detection + completed-since-last-
  interaction query — drives §7.
- Per-message Face-spawn wiring + recall-chip provenance plumbing — drives §3/§4.

## Concurrence

`[CONCUR:elliot]` `[CONCUR:aiden]` `[CONCUR:max]` — full 3-way concur on all 7 sections,
the chat-supersedes-dashboard-landing reconciliation, the honest cost-field resolution
(Confirm never gated on estimate-presence), and the five carried hard requirements. No
deadlocks.
