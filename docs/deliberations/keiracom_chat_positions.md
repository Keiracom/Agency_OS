# Keiracom Chat + Voice Interface — Working Positions

Dave directive 2026-05-20 ("the most important deliberation"). Deliberators: Elliot
(synthesis + implementation-feasibility), Aiden (architecture + competitive — placement,
background-surfacing), Max (cost + quality — message types, memory integrity).
Output → `ceo:deliberation:keiracom_chat_spec`. One session.

Reframe: the chat IS the product; the dashboard is the audit trail of what chat caused.
Function + behaviour only — no colours/aesthetics.

---

## ELLIOT — implementation-feasibility lens (2026-05-20)

**Anchoring principle: the processing display must mirror what the Face actually does.**
Dave is explicit — no spinner, no fake progress bar. So the spec for §3 must be built on
the Face's real execution sequence, and I can name it exactly.

**What a Face actually does, per message (the real sequence):**
1. Spawn — the ephemeral agent boots.
2. Load the last-20-message conversation window.
3. Recall identity + governance from Cognee.
4. Recall relevant context from Weaviate (vector search on the message).
5. Query live thread state from the Dispatcher (container_monitor / session_manager).
6. Conditionally query spend (spend_tracker) — only if the message implicates cost.
7. **Route decision** — answer directly, or dispatch to the thread pool.
8. If dispatch — claim a thread, hand off the task brief.
9. Compose + stream the response.
10. Terminate.

Each step is a real operation with an observable start and end. They CAN be streamed —
that is the build requirement for honest processing transparency (§3).

### (3) Processing transparency — my lead

Between submit and response, the chat shows the Face's **actual current step**, advancing
as each completes. Not a spinner — a labelled, honest sequence:
- "Reading the conversation…" (step 2)
- "Recalling what I know…" — Cognee + Weaviate (steps 3–4). When Weaviate returns a
  hit, the display can name it: "Found context from 3 days ago" (feeds §4).
- "Checking your threads…" (step 5) — and spend, if relevant (step 6).
- "Deciding…" (step 7) — the routing moment.
- Then it resolves: either the response streams (answer), or a task-confirmation card
  appears (dispatch path → §6).

**Behaviour:** steps appear in order, each marked done as it completes; the display is
the Face emitting a status event per real step. A step that takes longer simply sits
longer — honest, because it reflects real latency. If a step fails (e.g. Cognee
unreachable), the display says so ("Memory layer slow — answering from recent context
only") rather than hanging.

**Build gap:** the Face must be instrumented to emit per-step status events, streamed to
the chat UI (websocket/SSE). The steps exist; the streaming instrumentation is the build.

### (5) Voice interface — my lead

Our voice stack is real (ElevenLabs / Vapi integrated). Position:

- **Voice is a MODE within chat, not a separate entry point.** Same Face, same
  conversation, same persistent memory — only the I/O channel changes. A user can start
  in text and toggle to voice mid-conversation; continuity must hold across the switch.
- **Visual layer during voice:** a waveform while the user speaks; the SAME honest
  processing states from §3 run on screen while the user is still talking or thinking
  (voice removes the discrete "submit" moment — processing overlaps with input); a live
  transcript builds as both sides speak.
- **Response shape: audio + a transcript card — never audio-only.** Audio-only destroys
  the conversation record and the audit trail. Every voice exchange leaves the same
  message objects in the chat history a text exchange would.
- **Task-confirmation card mid-voice — switches to visual for approval.** A dispatch is a
  commitment (it spends the customer's money and runs the fleet). It must NOT be approved
  by a voice "yes" that could be misheard or ambient. When the Face reaches a dispatch
  point in a voice session: the Face reads the brief aloud, the confirmation card appears
  visually, and approval requires an explicit visual tap (or a deliberate voice
  confirmation with a full read-back). Default: visual tap. This mirrors the internal
  Step-0-before-execute discipline — confirmation is deliberate, not ambient.

### (6) Deliberation flow before work — my lead

A user describes an idea loosely; the Face refines it into a dispatchable brief before
any thread picks it up. This is the customer-facing equivalent of our Step-0 restate.

- **Clarifying questions are bounded — 1 to 3, never an interrogation.** The Face asks
  ONLY what a thread genuinely needs to start and cannot reasonably infer. Where it can
  infer, it infers and shows the inference in the confirmation card for correction —
  surfacing an assumption to be corrected beats asking a question.
- **The task-confirmation card is the final brief** — what the thread will do, the scope
  (in/out), which integrations it will touch, the expected output/artifact, and a cost
  expectation (defer the cost-display detail to Max). It is editable inline before
  confirm.
- **The user confirms explicitly** — one deliberate action. Nothing dispatches to a
  thread without it. Confirm → a thread claims the work → the card transitions to
  "task dispatched" (§2).

### Quick reads on the other 4 (defer leads to Aiden/Max)

- (1) Placement: concur it must be the default surface, not a dashboard widget. My
  implementation note — chat as the landing, dashboard reachable from it; when chat is
  open it should hold focus, with the dashboard a deliberate navigation away, not a
  peek-behind. Defer the exact structure to Aiden.
- (2) Message types: defer to Max. Implementation note — each type maps to a real event:
  task-confirmation = pre-dispatch (§6); task-dispatched = a thread claim succeeded;
  task-completed = the audit/outcome record written. The chat must subscribe to those
  events to render the transitions.
- (4) Memory surfacing: defer to Max. Implementation note — a "recalled from N days ago"
  marker MUST be driven by a real Weaviate hit with a real timestamp. If the Face
  displays recall, the recall must be a true retrieval, never a fabricated claim — this
  is the same honesty rule as the processing display.
- (7) Background surfacing: defer to Aiden. Implementation note — task-completed events
  already flow (the audit record is written on completion); surfacing them to a chat
  that is closed needs a notification channel + an unread marker. Feasible; the
  notification transport is the build item.

**Elliot headline for synthesis:** the chat-is-the-product spec is feasible. The honest
processing display (§3) is buildable because the Face's steps are real and instrumentable
— that is the load-bearing build. Voice is a mode, not a separate product, and dispatch
approval stays visual+deliberate even in voice. The deliberation flow (§6) is the
customer-facing Step 0. Three build gaps: per-step status streaming, the voice visual
layer, and a background notification transport.

---

## AIDEN — architecture + competitive lens (received 2026-05-20)

**IA RECONCILIATION FLAG:** the dashboard spec set Threads as default landing; this
deliberation's reframe ("chat IS the product") overrides it — **default landing = Chat**.
Dashboard nav stays valid but demotes to verification views one click from chat. Cross-
doc consistency fix for the synthesis (not a deliberator divergence).

- **(1) Chat placement (lead):** chat is the default landing SURFACE, not a slide-in
  widget. Layout — chat-primary with a **persistent fleet rail** (compact, always
  visible: live thread states, capacity meter, fleet-health dot) so the user directs AND
  sees verification without leaving chat. Dashboard views = tabs one click away. Empty
  state teaches the interaction model — 3-4 example directives phrased as things you say,
  current fleet state, one line on "describe what you want, I refine then dispatch."
- **(2) Six response shapes:** plain text answer; clarifying question (+ quick-pick
  chips); task-confirmation card (objective/scope/threads/est-spend/est-duration —
  Confirm/Edit/Cancel, nothing dispatches without Confirm); task-dispatched card (id,
  thread, live state, updates in place); task-completed card (artifacts, actual-vs-est
  spend, duration); error card (what/where/honest cause/suggested action).
- **(3) Processing (competitive read):** Cursor/Claude Code surface real named tool
  steps that stream and resolve with results — no spinner, no fake %. Keiracom mirrors
  this with the Face's real steps; each resolves with a concrete result ("Found 3 items
  from memory", "6 threads — 4 running"); steps collapse to a one-line expandable summary
  after the response lands. The processing trace IS the trust artifact.
- **(4) Memory:** 20-msg window = ordinary scrollback, no special treatment. Long-term
  memory surfaces as explicit **recall chips** ("recalled — [topic], from 3 days ago",
  click to expand). User never wonders "did it remember" — chip present or not. Returning
  session: Face opens by signalling continuity.
- **(5) Voice:** mode-within-chat, not separate. Visual layer = listening indicator +
  live transcript (catch misrecognition) + the §3 steps still render. Response = audio +
  transcript + cards. Task-confirmation card MUST render visually mid-voice — dispatch
  never approvable by audio alone; voice narrates it, user confirms by tap or deliberate
  voice. Voice is for directing + deliberation; confirmation/verification stay visual.
- **(6) Deliberation flow:** clarifying questions capped 2-3; if still ambiguous the Face
  states its assumption on the confirmation card for correction. Confirmation card = the
  final brief (objective, scope in/out, threads, est spend+duration, key assumptions).
  Confirm/Edit/Cancel — Confirm is the only dispatch trigger. Multi-task = a small ordered
  set of cards, not one monolith.
- **(7) Background surfacing (lead — Linear/Vercel research):** common pattern — push the
  event on completion, hold the result where the user returns, badge the entry point.
  Keiracom 3 layers: (1) on completion — in-app toast if present, else configured channel
  (email/Slack via connected integrations); (2) held in chat — task-completed card waits
  unread, chat/nav badged; (3) **the Face reintroduces it** — next spawn reads "tasks
  completed since last interaction" and leads with a composed summary + audit links: "you
  return to a briefing, not a backlog." Build gap: in-app toast + presence detection +
  the completed-since-last-interaction query.

**Aiden headline:** chat = default landing (overrides dashboard-spec Threads-landing);
nothing dispatches without explicit Confirm (text or voice); processing = honest streamed
named steps; memory = explicit recall chips; background completion = the Face reintroduces
finished work.

---

## MAX — cost + quality lens (received 2026-05-20)

Cross-cutting QUALITY RULE: every card showing a number (spend, count, duration, ETA)
must be backed by a real query with an as-of timestamp. No fabricated figures, ever.
- **(2) Message types (lead):** plain text answer (numbers = live queried, labelled
  as-of); **task-confirmation card** — the core card — refined brief (objective/scope/
  definition-of-success), threads it occupies, **COST EXPECTATION** (estimated BYO-key
  token spend as a range + est wall-clock — user approves SPEND before it is incurred),
  integrations touched → irreversible/external actions called out explicitly, actions
  Approve/Edit/Cancel; task-dispatched (id, thread, dispatched-at); task-completed
  (outcome, artifacts, **actual spend shown beside the pre-dispatch estimate** — closes
  the cost-promise loop, duration, audit link); clarifying question; error (what failed,
  stage, plain cause, **spend-incurred-before-failure** shown). BUILD GAP: spend_tracker
  meters AFTER the fact — a pre-dispatch cost ESTIMATOR does not exist, must be built for
  the confirmation card.
- **(4) Memory (lead, data-integrity):** within the 20-msg window continuity is implicit
  (no marker). Beyond it, a Weaviate recall MUST cite a recall chip linked to the real
  record. NON-NEGOTIABLE: a recall claim must be backed by a real retrieval of a real
  record; "from 3 days ago" = the actual created_at, never estimated; the chip links to
  source so the customer can verify; if no recall, the Face says so plainly and NEVER
  confabulates — a fabricated recall is the worst trust failure a chat-first product can
  have. Window-boundary honesty. Memory writes inspectable ("what I'll remember from
  this"). Surface a chip ONLY when a recall actually fired.
- **(1) Chat placement:** default surface post-onboarding, full surface not a widget.
  Empty state teaches the verb set with 2-3 example asks.
- **(3) Processing:** honest steps with checkmarks. INTEGRITY RULE — never display a step
  that did not run; a fake step is a fake progress bar by another name.
- **(5) Voice:** mode within chat. Live transcript (ASR errors common) + honest steps.
  Audio + transcript always; structured output = audio + full card. COST-SAFETY RULE: a
  voice misrecognition must NEVER trigger a spend-bearing or irreversible dispatch —
  cost-bearing approval needs explicit confirm-back ("Confirming: dispatch X, est $Y —
  say yes") or tap.
- **(6) Deliberation:** ask as FEW questions as possible — only what materially changes
  brief or cost; batch them. After 2-3 rounds present best-guess brief with assumptions
  marked; don't loop forever.
- **(7) Background surfacing:** dashboard alerts + optional email/push; on return the
  Face reintroduces as a task-completed card — and the async reintroduction MUST still
  show actual-vs-estimated spend.

**Max divergence flags:** (2) the pre-dispatch cost estimator is a real build gap — no
backing capability today; (4) no-fabricated-recall is a hard shippable-blocker.

---

## CONVERGENCE / DIVERGENCE (for the concur round)

**Near-total 3-way convergence** on all 7 sections: chat = default full landing surface
(not a widget); 6 response shapes; honest streamed named processing steps (no spinner /
no fake bar / never show a step that didn't run); long-term memory = recall chips
(no-fabricated-recall hard rule); voice = mode-within-chat, audio+transcript+cards,
dispatch never approvable by audio alone; deliberation flow = 2-3 clarifying questions
then best-guess-with-assumptions, confirmation card = the final brief, Confirm is the
only dispatch trigger; background completion = push + held card + the Face reintroduces
with a composed summary ("a briefing, not a backlog").

**Two items to confirm in the concur round (resolutions, not open divergences):**
- **IA reconciliation (Aiden):** the reframe makes default landing = Chat — this
  SUPERSEDES the dashboard spec's "Threads landing." The dashboard nav stays valid,
  demoted to verification views one click from chat. The final chat doc states this
  supersedes the dashboard-spec landing decision.
- **Cost-estimator resolution (Max flag 2):** the no-fabricated-numbers rule (all 3 hold)
  forces the answer — the task-confirmation card ships with an HONEST cost field: a real
  estimate WITH a stated basis once the estimator exists, and "estimate unavailable —
  actual will be metered" until then. The pre-dispatch cost estimator is a named build
  gap. This is deliberator-resolvable (forced by the shared integrity rule), not a Dave
  escalation.

**Carried as hard requirements:** every number backed by a real query + as-of timestamp;
no-fabricated-recall (recall chip ↔ real record); never display a processing step that
didn't run; voice cost-safety (misrecognition never triggers spend-bearing dispatch);
actual-vs-estimate shown on completion (closes the cost loop).

**Build gaps flagged:** per-step status streaming; pre-dispatch cost estimator; voice
visual layer; background notification transport + presence detection +
completed-since-last-interaction query; per-message Face-spawn + recall-chip provenance
plumbing.
