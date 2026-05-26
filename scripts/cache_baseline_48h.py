"""48h cache-hit-rate baseline observation report — Phase A7 sub-task 5.

Per design §7 (docs/architecture/design/a7_cache_architecture.md) — runs
post-A9-migration validation gate; reports cache hit rates to
keiracom.elliot.inbox.

HONEST FRAMING (per design §7): N=1 tenant (Dave), 48h window. Not
representative of multi-tenant production scale. First 3 paying customers
+ their first month of traffic = real calibration data.

ACTION THRESHOLDS (per design §13 CB-8):
  - Valkey hit rate <10%  → BLOCKING-V1 (re-tune _quantise_to_bucket + re-baseline)
  - Valkey hit rate 10-40% → TRACK-AND-IMPROVE (flagged, non-blocking)
  - Valkey hit rate >40%  → HEALTHY
  - Anthropic prompt cache read/(create+read+standard) >50% → HEALTHY
  - Anthropic prompt cache read/(...) <20%                   → TRACK-AND-IMPROVE (Anthropic-side measurement, non-customer-facing)

Reads metrics from Better Stack via injected `metrics_fetcher` callable to
keep this module testable (no live Better Stack call in unit tests).

USAGE:
    python scripts/cache_baseline_48h.py --tenant-id 00000000-...-001 --out /tmp/baseline.md

Output is Markdown to STDOUT or --out path. Post to keiracom.elliot.inbox
manually via tg or via the orchestrator after running.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

# Action thresholds — keep in sync with design §13 CB-8.
VALKEY_BLOCKING_THRESHOLD: float = 0.10
VALKEY_HEALTHY_THRESHOLD: float = 0.40
ANTHROPIC_HEALTHY_THRESHOLD: float = 0.50
ANTHROPIC_TRACK_THRESHOLD: float = 0.20

# Metrics fetcher: caller-injected. Returns dict of metric_name -> aggregated value.
# Signature: (metric_name, tags_filter, window_start, window_end) -> dict[str, int]
MetricsFetcher = Callable[
    [str, dict[str, str], datetime, datetime],
    dict[str, int],
]


def _classify_valkey(hit_rate: float) -> str:
    if hit_rate < VALKEY_BLOCKING_THRESHOLD:
        return "BLOCKING-V1 (re-tune buckets + re-baseline before paying customer)"
    if hit_rate < VALKEY_HEALTHY_THRESHOLD:
        return "TRACK-AND-IMPROVE (flagged, non-blocking)"
    return "HEALTHY"


def _classify_anthropic(read_ratio: float) -> str:
    if read_ratio < ANTHROPIC_TRACK_THRESHOLD:
        return "TRACK-AND-IMPROVE (breakpoint placement misaligned)"
    if read_ratio < ANTHROPIC_HEALTHY_THRESHOLD:
        return "MARGINAL (between TRACK and HEALTHY thresholds)"
    return "HEALTHY"


def _safe_divide(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def generate_report(
    *,
    tenant_id: str,
    window_start: datetime,
    window_end: datetime,
    metrics_fetcher: MetricsFetcher,
) -> str:
    """Generate the Markdown baseline report. Pure function — no I/O."""
    valkey = metrics_fetcher(
        "keiracom.cache.valkey.lookup",
        {"tenant_id": tenant_id},
        window_start,
        window_end,
    )
    anthropic = metrics_fetcher(
        "keiracom.cache.anthropic.input_tokens",
        {"tenant_id": tenant_id},
        window_start,
        window_end,
    )

    hits = int(valkey.get("hit", 0))
    misses = int(valkey.get("miss", 0))
    total = hits + misses
    hit_rate = _safe_divide(hits, total)

    cache_read = int(anthropic.get("read", 0))
    cache_create = int(anthropic.get("create", 0))
    standard = int(anthropic.get("standard", 0))
    anthropic_total = cache_read + cache_create + standard
    read_ratio = _safe_divide(cache_read, anthropic_total)

    return f"""# 48h Cache-Hit Baseline — {tenant_id}

**Window:** {window_start.isoformat()} → {window_end.isoformat()} UTC
**N:** 1 tenant (Dave dogfooding). NOT representative of multi-tenant production scale.
**First-paying-customer calibration:** required before treating these as definitive.

## Valkey semantic cache

| Field | Value |
|---|---|
| Hits | {hits:,} |
| Misses | {misses:,} |
| Total lookups | {total:,} |
| Hit rate | {hit_rate:.1%} |
| Classification | {_classify_valkey(hit_rate)} |

## Anthropic prompt cache (per Anthropic API usage block)

| Field | Value |
|---|---|
| cache_read_input_tokens | {cache_read:,} |
| cache_creation_input_tokens | {cache_create:,} |
| standard input_tokens | {standard:,} |
| Total | {anthropic_total:,} |
| Read ratio | {read_ratio:.1%} |
| Classification | {_classify_anthropic(read_ratio)} |

## Action

- Valkey: {_classify_valkey(hit_rate)}
- Anthropic prompt cache: {_classify_anthropic(read_ratio)}

If Valkey is BLOCKING-V1, re-tune `_quantise_to_bucket` (num_buckets) in
`src/keiracom_system/cache/valkey_client.py` and re-run this baseline
before customer onboarding.
"""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--out", default="-", help="output path or '-' for stdout")
    parser.add_argument("--hours", type=int, default=48)
    return parser.parse_args()


def _placeholder_fetcher(*_args: Any, **_kwargs: Any) -> dict[str, int]:
    """Placeholder fetcher when running this script standalone without Better Stack.

    Real production wire-up injects a Better Stack metrics API client.
    Returning zeros documents the contract; the report will show 0%
    hit rate which classifies as BLOCKING-V1 — the script doesn't lie about
    its inputs, the caller wires the real fetcher.
    """
    return {"hit": 0, "miss": 0, "create": 0, "read": 0, "standard": 0}


def main() -> int:
    args = _parse_args()
    end = datetime.now(UTC)
    start = end - timedelta(hours=args.hours)
    report = generate_report(
        tenant_id=args.tenant_id,
        window_start=start,
        window_end=end,
        metrics_fetcher=_placeholder_fetcher,
    )
    if args.out == "-":
        sys.stdout.write(report)
    else:
        with open(args.out, "w") as fh:
            fh.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
