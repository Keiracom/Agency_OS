# Four-Store Save Skill

Canonical save mechanism for directive completion (LAW XV).

## Purpose

Ensures every completed directive is recorded in all four mandatory stores:
1. `docs/MANUAL.md` — human-readable repo SSOT
2. `public.ceo_memory` — Supabase CEO key-value store
3. `public.cis_directive_metrics` — execution metrics row
4. Google Drive mirror via `write_manual_mirror.py` (best-effort, non-blocking)

## Usage

```
python scripts/three_store_save.py \
  --directive D1.8 \
  --pr-number 329 \
  --summary "Built three_store_save.py — canonical LAW XV completion script."
```

### Read summary from stdin

```
echo "Summary text here" | python scripts/three_store_save.py \
  --directive D1.8 --pr-number 329 --summary -
```

### Dry run (no writes)

```
python scripts/three_store_save.py \
  --directive TEST --pr-number 0 --summary "Dry run test" --dry-run
```

### Custom section

```
python scripts/three_store_save.py \
  --directive D1.8 --pr-number 329 --summary "..." --manual-section 13
```

## Arguments

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `--directive` | yes | — | Directive label: "309", "D1.8", "A", etc. |
| `--pr-number` | yes | — | GitHub PR number (int) |
| `--summary` | yes | — | Completion summary, or "-" to read stdin |
| `--manual-section` | no | 13 | MANUAL.md section to append under |
| `--dry-run` | no | false | Print actions without writing |

## Environment

Loaded from `/home/elliotbot/.config/agency-os/.env`:
- `SUPABASE_URL` — e.g. `https://jatzvazlbusedwsnqxzr.supabase.co`
- `SUPABASE_SERVICE_KEY` — service role key for PostgREST auth

## Exit codes

- `0` — all 4 stores saved (Drive mirror failure is non-fatal)
- `1` — at least one of stores 1-3 failed (output shows which succeeded before failure)

## Governance

This script satisfies LAW XV (Four-Store Completion Rule). Run it as the final step of every directive before reporting complete to Dave.
