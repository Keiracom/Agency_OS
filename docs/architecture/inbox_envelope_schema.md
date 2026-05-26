# Inbox JSON Envelope Schema (v1)

**Status:** RATIFIED — PR #1140 §5 + §7 piece #3
**Canonical module:** `src/relay/envelope_schema.py` (registry + producer validator)
**Author:** nova (Agency_OS-1nf4)
**Date:** 2026-05-26

This doc is the single source of truth for the inner-payload shape of every
message written to `/tmp/telegram-relay-<callsign>/inbox/`. The HMAC outer
wrapper (`security.inbox_hmac.sign`) is type-agnostic; everything below
describes what lives INSIDE the signed payload.

Consumer-side routing on these types belongs to the dispatcher package
(PR #1140 §7 piece #1) — a separate KEI. This doc + the registry module are
producer-side only.

## §1 Universal fields (every envelope)

| Field | Type | Description |
|---|---|---|
| `id` | str | Unique identifier (typically `task_<unix_ts>_<6-hex>` or arbitrary string). Stable across re-deliveries. |
| `type` | str | One of the 4 values in §2. Routes the consumer's dispatch on which handler to invoke. |
| `from` | str | Sender callsign (e.g. `elliot`, `nova`). For audit + reply routing. |

`created_at` (unix int) is added by `scripts/sign_dispatch.py` but is NOT a
required schema field — the HMAC layer carries timestamp semantics via the
signature. Producers that need a payload-level timestamp should include it
explicitly per type.

## §2 Envelope types

### 2.1 `task_dispatch` (existing, since pre-v1)

Producer dispatches a task to a callsign. The original shape since the inbox
relay shipped.

Required fields: `id`, `type`, `from`, `target`, `brief`.

| Field | Type | Description |
|---|---|---|
| `target` | str | Target callsign — must be a known callsign with an inbox dir. |
| `brief` | str | One-paragraph description of the task. |

Common optional fields: `max_task_minutes` (int), `task_ref` (str — opaque
correlation key for later messages).

Example:
```json
{
  "id": "task_1748252400_abc123",
  "type": "task_dispatch",
  "from": "elliot",
  "target": "nova",
  "brief": "Review PR #N + post APPROVE or HOLD.",
  "max_task_minutes": 30,
  "task_ref": "review-pr-N"
}
```

### 2.2 `decision_request` (new — PR #1140 §5)

Agent A pauses mid-task and asks Dave (or another decision-maker) a yes/no
or multiple-choice question. Carries the originating task_ref so the
response can route back.

Required fields: `id`, `type`, `from`, `target`, `question`, `options`.

| Field | Type | Description |
|---|---|---|
| `target` | str | Decision-maker callsign (e.g. `elliot` for orchestrator-routing-to-Dave). |
| `question` | str | The question text shown to the decision-maker. |
| `options` | list[str] | Valid response strings. The response's `decision` field MUST match one of these. |

Common optional fields: `decision_deadline_s` (int — unix-ts after which the
request is treated as dead-lettered; defaults to 7 days at consumer policy).

Example:
```json
{
  "id": "dec_req_1748252500_def456",
  "type": "decision_request",
  "from": "nova",
  "target": "elliot",
  "question": "PR #1140 has a HOLD-NIT. Push fix-up commit or override?",
  "options": ["push_fixup", "override_hold", "abandon"],
  "decision_deadline_s": 1748857300
}
```

### 2.3 `decision_response` (new — PR #1140 §5)

The decision-maker's reply. Carries `original_task_ref` so the dispatcher
can resume the paused agent.

Required fields: `id`, `type`, `from`, `target`, `decision`, `original_task_ref`.

| Field | Type | Description |
|---|---|---|
| `target` | str | The callsign that paused (e.g. `nova` if responding to nova's `decision_request`). |
| `decision` | str | The chosen option. MUST match one of the offered `options` from the request. |
| `original_task_ref` | str | The `task_ref` from the paused agent's pre-pause state. The dispatcher uses this to look up the `paused_tasks` row + resume-spawn. |

Common optional fields: `responder` (str — who actually decided, distinct
from `from` if relayed; e.g. `from=elliot, responder=dave`).

Example:
```json
{
  "id": "dec_resp_1748252900_ghi789",
  "type": "decision_response",
  "from": "elliot",
  "target": "nova",
  "decision": "push_fixup",
  "original_task_ref": "review-pr-N",
  "responder": "dave"
}
```

### 2.4 `paused_pending_decision` (new — PR #1140 §5)

Emitted by the paused agent BEFORE termination. Captures interim state so
the future resume-spawn agent can pick up where the paused agent left off.
Persisted to the `paused_tasks` Postgres table (PR #1140 §7 piece #2 —
separate KEI; this envelope just carries the payload).

Required fields: `id`, `type`, `from`, `task_ref`, `paused_at`, `interim_state`.

| Field | Type | Description |
|---|---|---|
| `task_ref` | str | Opaque correlation key. The matching `decision_response.original_task_ref` routes the resume. |
| `paused_at` | int | Unix timestamp when the agent paused. Used for TTL (~7 days per §5) + dead-letter computation. |
| `interim_state` | dict | Typically `<1KB` JSON. Carries: the question that was asked, paths to intermediate artifacts, any per-task notes the agent wants the resume-spawn to inherit. Schema is per-task; the consumer doesn't introspect. |

`target` is intentionally NOT required — `paused_pending_decision` is a
self-snapshot, not a routed message. The dispatcher reads it from the
emitter's outbox; no inter-callsign delivery.

Example:
```json
{
  "id": "paused_1748252600_jkl012",
  "type": "paused_pending_decision",
  "from": "nova",
  "task_ref": "review-pr-N",
  "paused_at": 1748252600,
  "interim_state": {
    "question_sent": "PR #1140 has a HOLD-NIT...",
    "artifacts": ["/tmp/review-pr-N-draft.md"],
    "notes": "Substance review LGTM; only the dangling comment blocks me."
  }
}
```

## §3 Validation contract

`src/relay/envelope_schema.py` exposes:
- `KNOWN_ENVELOPE_TYPES: frozenset[str]` — the 4 type-name literals
- `REQUIRED_FIELDS: Mapping[str, frozenset[str]]` — per-type required field sets
- `validate_envelope(payload) -> None` — raises `EnvelopeSchemaError` if `type`
  is missing or unknown, or if any required field is absent

The validator checks field PRESENCE only, not field VALUES. Value-level
checks (e.g. `options` is a list of str; `paused_at` is a positive int)
belong to producers + consumers per-call — over-validation in a shared
module would couple to internal details and break across producer updates.

`scripts/sign_dispatch.py` wires the type list at the argparse layer:
`--type choices=sorted(KNOWN_ENVELOPE_TYPES)`. Adding a new type is a
2-line change (registry entry + required-fields entry) plus a doc update
here.

## §4 Out of scope (separate KEIs)

- **Consumer-side enforcement** in `relay_watcher.sh` / `nats_to_inbox_bridge.py`
  — dispatcher package KEI (PR #1140 §7 piece #1).
- **`paused_tasks` Postgres table** — PR #1140 §7 piece #2 (separate KEI).
- **Resume-spawn logic** (consumer of `decision_response` + `paused_pending_decision`)
  — PR #1140 §7 piece #1.
- **HMAC signing** — `security.inbox_hmac.sign` already wraps any inner payload;
  no changes here.

## §5 References

- PR #1140 — Ephemeral agent system scoping doc (§5 state-snapshot + §7
  piece #3 schema update)
- `scripts/sign_dispatch.py` — primary producer (now wired to validator)
- `security.inbox_hmac.sign` — outer HMAC wrapper
- Agency_OS-zw3k — Scout's audit that surfaced §7 piece #3 as never-filed
