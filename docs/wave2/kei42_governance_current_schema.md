# KEI-42 — `ceo:governance_current` schema design (live-state SSOT)

**Author:** Aiden (schema design only — per Dave verbatim ts ~1778668400)
**Implementer:** Elliot (post-compact live cat-and-write per LAW I-A hard empirical authorship)
**Beads:** Agency_OS-uss — P1 URGENT
**ceo_memory anchor:** `ceo:rule:supabase_sole_ssot` (compose) + new key `ceo:governance_current`.

Schema-shape only — field list + types + write triggers + query pattern. NO inline live values (those are Elliot's lane).

## Dave verbatim (canonical source — ts ~1778668400)

> Single Supabase key `ceo:governance_current` containing complete LIVE governance state:
> - Enforcer rules (exact)
> - Beads schema
> - Relay architecture
> - CONCUR gate regex
> - Three-store save current state
> - Fabrication Defense layer status
> - Better Stack monitors
> - All 6 agent worktree paths
> - Cognee wiring state
>
> LAW I-A hard: cat actual files, query actual state. File X says X, memory says Y → report X.
>
> NOT include: build history, pipeline architecture, aspirational design. Current live state only.
>
> Closes CEO blind spot.

## Schema

```json
{
  "schema_version": 1,
  "written_at": "ISO timestamp",
  "written_by": "elliot",
  "source_of_truth_anchor": "LAW I-A: cat-actual-files + query-actual-state",

  "enforcer_rules": {
    "rule_2_step_0_before_execution": "<verbatim regex/text from enforcer source>",
    "rule_9_directive_initiative": "<verbatim>",
    "rule_6_save_claim_requires_proof": "<verbatim>",
    "rule_8_dispatch_coordination": "<verbatim>",
    "rule_13_blocker_escalation": "<verbatim>",
    "rule_14_idle_status_dispatch": "<verbatim>",
    "source_file": "scripts/enforcer/<filename>.py",
    "last_modified": "ISO timestamp"
  },

  "beads_schema": {
    "version": "<bd --version output>",
    "native_subcommands": ["ready", "list", "show", "update", "create", "close", "linear sync", "find-duplicates"],
    "non_native_wrapped": ["check-claim"],
    "external_ref_field": "url-mirror to Linear KEI",
    "schema_source": "bd help / bd <cmd> --help verbatim"
  },

  "relay_architecture": {
    "primary_relay": "scripts/slack_relay.py",
    "callsign_resolution_path": "Path(__file__).resolve().parent.parent / 'IDENTITY.md'",
    "callsign_resolution_bug_status": "KEI-22 deliverable-tbd or workaround CALLSIGN=<name> env override",
    "bot_token_env": "SLACK_BOT_TOKEN",
    "default_channel_id": "C0B3QB0K1GQ (#execution)",
    "channels_by_callsign": "<per-callsign allowlist verbatim from slack_relay.py>",
    "concur_gate_state": "broad (pending KEI-38 narrowing)"
  },

  "concur_gate_regex": {
    "current_pattern": "<verbatim regex string from gate source>",
    "current_match_class": "anywhere-in-post + prose-CONCUR + factual-status (over-broad)",
    "kei_38_target_pattern": "^\\s*\\[(CONCUR|BLOCK):(aiden|elliot|max|atlas|orion|scout|enforcer)\\](?:\\s|$)",
    "kei_38_status": "design-doc merged PR #834 + scope-expansion PR #835 (Rule 2 narrowing) merged; implementation pending Elliot post-compact"
  },

  "three_store_save_state": {
    "stores": ["supabase_ceo_memory", "cis_directive_metrics", "linear_issue_comment"],
    "law_xv_version": "v2 (Drive Manual retired ts ~1778668100)",
    "law_xv_source_doc": "docs/wave2/law_xv_drive_retired_supabase_sole_ssot.md (PR #839 merged @ 2b9ddc0e)",
    "session_end_check_script": "scripts/session_end_check.py",
    "deprecated": "write_manual_mirror.py (1-cycle warning before removal)"
  },

  "fabrication_defense_layer": {
    "verify_gate_active": true,
    "verify_gate_script": "src/bot_common/verify_gate.py",
    "verify_gate_invocation": "scripts/slack_relay.py main() pre-post check",
    "blocks": ["fabricated PR# in completion claims", "fabricated commit-hash in completion claims"],
    "blocked_history_count": "<count from logs>"
  },

  "better_stack_monitors": {
    "active_endpoints": "<list of BETTERSTACK_HB_* env vars + URLs from .env (redacted)>",
    "active_dispatch_outcome_heartbeat": "BETTERSTACK_HB_DISPATCH_OUTCOME",
    "active_phase1_ingest_heartbeat": "BETTERSTACK_HB_COGNEE_PHASE1_INGEST",
    "incident_webhook_to_linear": "KEI-26 PR #815 — cognee-phase1-ingest false-positive on completion-exit pending bd issue tune"
  },

  "agent_worktree_paths": {
    "elliot": "/home/elliotbot/clawd/Agency_OS",
    "aiden": "/home/elliotbot/clawd/Agency_OS-aiden",
    "max": "/home/elliotbot/clawd/Agency_OS-max",
    "atlas": "/home/elliotbot/clawd/Agency_OS-atlas",
    "orion": "/home/elliotbot/clawd/Agency_OS-orion",
    "scout": "/home/elliotbot/clawd/Agency_OS-scout"
  },

  "cognee_wiring_state": {
    "wrapper": "src/cognee/client.py (Phase 0 sole-call-surface per PR #764)",
    "vector_db_provider": "lancedb",
    "graph_db_provider": "networkx",
    "system_root_directory": "<.env value if set, else venv default>",
    "lance_writer_serialisation": "asyncio.Semaphore(1) eager-init in client.py (PR #826 + PR #832)",
    "cross_process_lock_status": "OPEN — bd Agency_OS-nk8 P2 (fcntl flock on /home/elliotbot/.cognee_system/lance.lock)",
    "phase_1_corpus_status": "Stream 1+2 sealed; Stream 3+4 in-progress at write-time",
    "skill_callsurface": "skills/cognee-recall (read-only)"
  }
}
```

## Write triggers

Per Dave LAW I-A hard rule (live state, not memory), write triggers are read-driven not push-driven:

1. **Hourly cron during peak hours (07:00–21:00 AEST)** — Elliot orchestrator polls + writes a fresh snapshot.
2. **On any merge to main of a file in the watched-paths set** — slack_relay.py / enforcer / IDENTITY.md / CLAUDE.md / cognee/client.py / session_end_check.py / .env. Watched-paths regex emitted by KEI-22 deliverable 7 (Slack-relay auto-detect, scoped to governance-changing PRs).
3. **On Dave standing-rule ratification** — same fire-path as `ceo:rule:*` auto-record (KEI-22 D7).
4. **On manual `bd governance refresh`** — Elliot triggers post-compact or as needed.

Write contention: last-write-wins on Supabase upsert (single key). Each writer constructs the FULL snapshot from live cats + queries; no partial diffs.

## Query pattern

```sql
SELECT value FROM public.ceo_memory WHERE key = 'ceo:governance_current';
```

Sub-100ms; CEO new-session AND mid-session-uncertainty reads this when "what's the actual current state of X?" beats "what's the documented architecture for X?".

Composes with `ceo:boot_state_current` (KEI-37): boot_state is the WHAT-TO-DO-NEXT primary; governance_current is the WHAT-IS-CURRENTLY-WIRED primary.

## Acceptance criteria

- Key `ceo:governance_current` exists in `public.ceo_memory`.
- Schema-version 1 envelope.
- Field values match LIVE state via empirical cat / query at write-time (LAW I-A — no aspirational design, no memory recall).
- Hourly cron refresh during peak hours; staleness ≤60 min during peak.
- Drift-test: take any field's value (e.g. `concur_gate_regex.current_pattern`); cat the source file; assert byte-equality. If drift detected → re-write fires immediately.
- Excludes: build history, pipeline architecture, aspirational design (per Dave explicit not-include).

## Implementation handoff for Elliot (post-compact)

1. Cat each source file referenced in the schema (slack_relay.py / enforcer / .env / cognee/client.py / IDENTITY.md / session_end_check.py / GOVERNANCE.md).
2. Query bd / Supabase / Better Stack API for live versions, allowlists, monitor URLs.
3. Construct the JSON object per the schema above.
4. UPSERT into `public.ceo_memory` with key `ceo:governance_current`.
5. Add to `ceo:boot_state_current.rules_ref` if not already (so new CEO sessions load it).
6. Verify with the drift-test for at least one field (e.g. concur_gate_regex).

Estimated: ~30 min wall-clock for first authoritative write; ~5 min for hourly refresh.

## Rollback

Snapshot prior key version to `docs/archive/ceo_governance_current_<timestamp>.json` before any UPSERT. If a write introduces a regression, restore the prior version via SQL INSERT.

## Sequencing

Bundles with the pre-restart governance refresh cascade (KEI-37 / 38 / 39 / 8lz / hygiene / Rule 2 / LAW XV / this schema). Total cascade is a single Elliot post-compact work-block.
