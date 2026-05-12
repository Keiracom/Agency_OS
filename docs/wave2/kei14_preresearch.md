# KEI-14 Pre-Research — Phase 3 (Audit Hardening)

Source: Dave's 20-Item Roadmap 2026-05-11 (items 9–11). Builds on PR-A session store schema (Max's PR #756).

## 1. Hash-chained JSONL audit receipts — NOT STARTED

`grep -r "hash.chain\|chained.*receipt\|jsonl.*audit"` across `src/` + `scripts/` = zero hits.

**Reference:** OpenClaw Flight Recorder RFC-001.

**Outline:**
- `src/audit/receipts.py`: one JSONL line per tool call. Schema `{ts, callsign, tool, args_hash, result_hash, prev_hash, this_hash}` where `this_hash = sha256(prev_hash + canonical_json(record_without_this))`.
- Storage: `~/.local/state/audit/<YYYY-MM-DD>.jsonl` append-only.
- Verifier CLI: `scripts/audit/verify_chain.py <date>` — exits non-zero on break.
- PostToolUse hook writes synchronously (chain integrity > perf).
- Enforcer replay-on-claim queries the chain, not GitHub.

Effort: ~280 LOC, single PR.

## 2. Ed25519 signed action receipts — NOT STARTED (wrong primitive exists)

`scripts/sign_dispatch.py` exists but uses **HMAC** (`src/security/inbox_hmac.sign`), not Ed25519, and only signs clone-dispatch payloads — not PR/merge/completion events.

**Reference:** `wshobson/agents` protect-mcp skill.

**Outline:**
- Per-callsign Ed25519 keypair: privkey at `~/.config/agency-os/keys/<callsign>.ed25519` (0600), pubkey in new `public.callsign_keys` Supabase table.
- Receipt: `{action_type, callsign, payload_hash, ts, signature_b64}` where `action_type ∈ {pr_open, pr_merge, completion_claim, dispatch}`.
- Integration: pre-commit hook signs on PR open; GitHub Actions signs on merge; `scripts/three_store_save.py` signs completion-claim store.
- Verifier: `scripts/audit/verify_receipt.py` returns non-zero on forgery.
- Pairs with #1 — embed signature in chain entries → non-repudiable chain.

Effort: ~150 LOC + keypair bootstrap, single PR.

## 3. Health-gate auto-rollback — PARTIAL

`scripts/alerts/service_health_monitor.py` exists (timer `OnCalendar *:0/5`) but alert-only per its docstring: *"Best-effort: a Slack-post failure does NOT raise. The monitor's job is liveness reporting."* No rollback logic.

**Reference:** `caramaschiHG/awesome-ai-agents-2026` auto-rollback pattern.

**Outline:**
- Extend monitor (or new `health_gate.py`) to compute rolling metrics: enforcer false-positive rate (1h), CI pass rate (24h via `gh api`), CI failure rate.
- Thresholds + revert-targets in `~/.config/agency-os/health_gate.yaml`. Each metric → threshold → revert-target (git SHA or systemd unit `.lkg` file).
- On breach: `git revert --no-edit <sha>` or `cp <unit>.lkg <unit>` + `systemctl --user reload`, post `#ceo`.
- Idempotency: breach-state file at `~/.local/state/agency-os/health_gate.state` prevents repeat reverts.

Effort: ~250 LOC, single PR.

## Sequence

#1 first (writer + hook). #2 second (slots into chain). #3 independent. #1+#2 bundle-able into one PR — shared verifier surface.
