# KEI-14 Pre-Research — Phase 3 (Audit Hardening)

Source: Dave's 20-Item Roadmap CEO post 2026-05-11 (Phase 3 items 9–11). Phase gate: builds on PR-A session store schema (already shipped per Max's PR #756).

## Item 1 — Hash-chained JSONL audit receipts

**Ship-status:** NOT STARTED. Grep for `hash.chain`, `chained.*receipt`, `jsonl.*audit`, `audit.*receipt` across `src/` and `scripts/` returns zero hits.

**Reference:** OpenClaw Flight Recorder RFC-001 (https://github.com/topics/agent-observability).

**Implementation outline:**
- New `src/audit/receipts.py`: write one JSONL line per tool call. Schema: `{ts, callsign, tool, args_hash, result_hash, prev_hash, this_hash}`. `this_hash = sha256(prev_hash + canonical_json(record_without_this_hash))`.
- Storage: `/home/elliotbot/.local/state/audit/<YYYY-MM-DD>.jsonl` (one file per day, append-only).
- Verification CLI: `python scripts/audit/verify_chain.py <date>` walks the chain, asserts hash continuity, exits non-zero on break.
- Hook integration: PostToolUse hook writes the receipt synchronously (chain integrity > performance).
- Enforcer integration: when Enforcer queries "did callsign X do Y?", query the chain rather than GitHub.

**Effort:** ~200 LOC writer + ~80 LOC verifier + 1 hook. Single PR.

## Item 2 — Ed25519 signed action receipts

**Ship-status:** NOT STARTED for action receipts. Adjacent: `scripts/sign_dispatch.py` exists but uses **HMAC** (`src/security/inbox_hmac.py`), NOT Ed25519, and only signs clone-dispatch payloads — not PR/merge/completion events.

**Reference:** `wshobson/agents` — protect-mcp skill (Cedar policy + Ed25519 signed receipts) (https://github.com/wshobson/agents).

**Implementation outline:**
- Keypair generation: one Ed25519 keypair per callsign. Private keys in `~/.config/agency-os/keys/<callsign>.ed25519` (perms 0600), public keys in `public.callsign_keys` Supabase table for verification.
- Receipt format: `{action_type, callsign, payload_hash, timestamp, signature_b64}`. `action_type ∈ {pr_open, pr_merge, completion_claim, dispatch}`.
- Sign on PR open: pre-commit hook or `gh` wrapper. Sign on merge: GitHub Actions workflow. Sign on completion claim: `scripts/three_store_save.py` writes a signed receipt alongside ceo_memory.
- Verifier: `scripts/audit/verify_receipt.py` checks signature against public key for the claimed callsign. Returns non-zero if forged.

Pairs naturally with Item 1 — embed Ed25519 signature in JSONL chain entries so the chain itself is non-repudiable.

**Effort:** ~150 LOC sign/verify + keypair bootstrap + 3 integration points. Single PR.

## Item 3 — Automated health-gate and config rollback

**Ship-status:** PARTIAL. `scripts/alerts/service_health_monitor.py` exists (per `agency-os-service-health-monitor.timer`, runs `OnCalendar *:0/5`) and posts to `#execution` on degraded state. But it is **alert-only** — no auto-rollback decision logic. Quoting the file's docstring: *"Best-effort: a Slack-post failure does NOT raise. The monitor's job is liveness reporting."*

**Reference:** Auto-rollback pattern from `caramaschiHG/awesome-ai-agents-2026`.

**Implementation outline:**
- Extend `service_health_monitor.py` (or new sibling `health_gate.py`) to:
  1. Compute rolling metrics: enforcer false-positive rate (over last 1h), test pass rate (last 24h CI runs via `gh api`), CI failure rate (same window).
  2. Define thresholds in `~/.config/agency-os/health_gate.yaml`. Each metric → threshold → revert-target (a git commit SHA or systemd unit-file path).
  3. On threshold breach: `git revert --no-edit <known-bad-sha>` OR `cp <unit-file>.lkg <unit-file>` + `systemctl --user reload <unit>`, then post to `#ceo` with metric, threshold, action taken.
  4. Idempotency: write breach state to `~/.local/state/agency-os/health_gate.state` so a sustained breach doesn't trigger N reverts.

**Effort:** ~250 LOC + config schema + 1 PR.

## Summary

| Item | Status | Effort |
|---|---|---|
| Hash-chained JSONL receipts | NOT STARTED | ~280 LOC, 1 PR |
| Ed25519 signed receipts | NOT STARTED (HMAC exists, wrong primitive) | ~150 LOC + keypair bootstrap |
| Health-gate auto-rollback | PARTIAL (monitor exists, no rollback) | ~250 LOC extension |

Sequence: ship Item 1 first (writer + hook), Item 2 second (slots into the chain), Item 3 independent. Items 1+2 share the verifier surface — bundle into one PR if Aiden prefers.
