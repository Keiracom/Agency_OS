"""Composition metering interpretation — Week 3 readiness.

Renders a Markdown report from the atomization + cache metrics emitted by:
  - PR #1185 (Week 1) — keiracom.atomization.atomizer.* + verifier.flags
  - PR #1189 (Week 2) — keiracom.atomization.compositions_per_task (pre-wired)
  - PR #1173 (A7 cache) — keiracom.cache.valkey.lookup + cache.anthropic.input_tokens

DESIGN — Dave starts daily use of the atomized memory system in Week 3. He
needs a way to READ the curve and understand what it's telling him without
having to query Better Stack himself. This report wraps the metrics into a
classified health summary.

Mirrors `scripts/cache_baseline_48h.py` (PR #1173) shape: pure function +
classification thresholds + injected metrics_fetcher (testable; no live
Better Stack call required in unit tests).

CLASSIFICATIONS (per design § + dispatch failure-mode-mitigations):

Atomization health:
  - tokens_in/atoms_produced < 100   → ATOMIZER_NOISY (atoms too sparse; grain too fine)
  - tokens_in/atoms_produced > 2000  → ATOMIZER_DENSE  (atoms too coarse; grain too broad)
  - else                              → HEALTHY

Verifier flag rate:
  - blocking_flags / total_atoms > 0.10   → BLOCKING-V1 (atomizer quality regression)
  - warning_flags / total_atoms > 0.30    → TRACK-AND-IMPROVE
  - else                                   → HEALTHY

Cache hit rate (Valkey + Anthropic) thresholds: SAME as PR #1173 cache_baseline_48h
(<10% BLOCKING-V1; 10-40% TRACK-AND-IMPROVE; >=40% HEALTHY).

Composition curve: rising trend indicates retrieval hitting context budget;
flagged as TRACK for Week 3 — real threshold needs first-week-Dave data to
calibrate.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

log = logging.getLogger(__name__)

# Atomizer health bands.
ATOMIZER_NOISY_MAX_TOKENS_PER_ATOM: float = 100.0
ATOMIZER_DENSE_MIN_TOKENS_PER_ATOM: float = 2000.0

# Verifier flag rate bands.
VERIFIER_BLOCKING_THRESHOLD: float = 0.10
VERIFIER_WARNING_THRESHOLD: float = 0.30

# Cache hit rate bands — same as PR #1173 cache_baseline_48h (cross-PR consistency).
CACHE_BLOCKING_THRESHOLD: float = 0.10
CACHE_HEALTHY_THRESHOLD: float = 0.40
ANTHROPIC_HEALTHY_THRESHOLD: float = 0.50
ANTHROPIC_TRACK_THRESHOLD: float = 0.20

# Metrics fetcher: caller-injected. Returns dict of metric_name -> aggregated values.
# Signature: (metric_name, tags_filter, window_start, window_end) -> dict[str, int|float]
MetricsFetcher = Callable[
    [str, dict[str, str], datetime, datetime],
    dict[str, float],
]


@dataclass(frozen=True, kw_only=True)
class MeteringSummary:
    """Aggregated metrics for one tenant + window — the report's input data."""

    tenant_id: str
    window_start: datetime
    window_end: datetime

    # Atomizer
    atomizer_tokens_in: int = 0
    atomizer_tokens_out: int = 0
    atoms_produced: int = 0
    atomizer_latency_ms_avg: float = 0.0

    # Verifier
    verifier_flags_info: int = 0
    verifier_flags_warning: int = 0
    verifier_flags_blocking: int = 0

    # Valkey cache
    valkey_hits: int = 0
    valkey_misses: int = 0

    # Anthropic prompt cache
    anthropic_create_tokens: int = 0
    anthropic_read_tokens: int = 0
    anthropic_standard_tokens: int = 0

    # Composition curve (Week 2 pre-wired)
    compositions_per_task_avg: float = 0.0


def classify_atomizer_grain(tokens_in: int, atoms_produced: int) -> str:
    """Tokens-in per atom ratio — coarse / fine grain heuristic."""
    if atoms_produced <= 0:
        return "INSUFFICIENT_DATA (no atoms produced yet)"
    ratio = tokens_in / atoms_produced
    if ratio < ATOMIZER_NOISY_MAX_TOKENS_PER_ATOM:
        return f"ATOMIZER_NOISY ({ratio:.0f} tokens/atom — atoms too sparse, grain too fine)"
    if ratio > ATOMIZER_DENSE_MIN_TOKENS_PER_ATOM:
        return f"ATOMIZER_DENSE ({ratio:.0f} tokens/atom — atoms too coarse, grain too broad)"
    return f"HEALTHY ({ratio:.0f} tokens/atom — grain within band)"


def classify_verifier_rate(blocking: int, warning: int, total_atoms: int) -> str:
    """Verifier flag rate banding."""
    if total_atoms <= 0:
        return "INSUFFICIENT_DATA (no atoms verified yet)"
    blocking_rate = blocking / total_atoms
    warning_rate = warning / total_atoms
    if blocking_rate > VERIFIER_BLOCKING_THRESHOLD:
        return (
            f"BLOCKING-V1 ({blocking_rate:.1%} blocking-flag rate — "
            "atomizer quality regression; pause customer onboarding)"
        )
    if warning_rate > VERIFIER_WARNING_THRESHOLD:
        return (
            f"TRACK-AND-IMPROVE ({warning_rate:.1%} warning-flag rate — "
            "human review queue volume rising)"
        )
    return f"HEALTHY (blocking={blocking_rate:.1%}, warning={warning_rate:.1%})"


def classify_valkey_hit_rate(hits: int, misses: int) -> str:
    """Valkey cache hit rate — mirrors PR #1173 cache_baseline_48h thresholds."""
    total = hits + misses
    if total <= 0:
        return "INSUFFICIENT_DATA (no Valkey lookups yet)"
    rate = hits / total
    if rate < CACHE_BLOCKING_THRESHOLD:
        return (
            f"BLOCKING-V1 ({rate:.1%} hit rate — re-tune _quantise_to_bucket "
            "and re-baseline before customer onboarding)"
        )
    if rate < CACHE_HEALTHY_THRESHOLD:
        return f"TRACK-AND-IMPROVE ({rate:.1%} hit rate — flagged, non-blocking)"
    return f"HEALTHY ({rate:.1%} hit rate)"


def classify_anthropic_cache_rate(create: int, read: int, standard: int) -> str:
    """Anthropic prompt-cache read-ratio banding."""
    total = create + read + standard
    if total <= 0:
        return "INSUFFICIENT_DATA (no Anthropic tokens yet)"
    read_ratio = read / total
    if read_ratio < ANTHROPIC_TRACK_THRESHOLD:
        return (
            f"TRACK-AND-IMPROVE ({read_ratio:.1%} cache-read ratio — "
            "breakpoint placement misaligned)"
        )
    if read_ratio < ANTHROPIC_HEALTHY_THRESHOLD:
        return f"MARGINAL ({read_ratio:.1%} cache-read ratio — between bands)"
    return f"HEALTHY ({read_ratio:.1%} cache-read ratio)"


def classify_composition_curve(compositions_per_task_avg: float) -> str:
    """Composition rate trend — Week 3 calibration starting point.

    Initial bands: <2 = under-using atoms; 2-8 = healthy band; >8 = context
    budget pressure. These need first-week-Dave data to calibrate properly —
    flagged as PROVISIONAL until N=1-week-actual-traffic baseline exists.
    """
    if compositions_per_task_avg <= 0:
        return "INSUFFICIENT_DATA (no compositions per task yet — Week 3 starts here)"
    if compositions_per_task_avg < 2:
        return (
            f"UNDER_USING ({compositions_per_task_avg:.1f} comp/task — retrieval may not be firing)"
        )
    if compositions_per_task_avg > 8:
        return (
            f"CONTEXT_PRESSURE ({compositions_per_task_avg:.1f} comp/task — "
            "atoms hitting Claude context budget; tune top_k or min_score)"
        )
    return f"HEALTHY-PROVISIONAL ({compositions_per_task_avg:.1f} comp/task — calibrate after first-week-Dave baseline)"


def fetch_summary(
    *,
    tenant_id: str,
    window_start: datetime,
    window_end: datetime,
    metrics_fetcher: MetricsFetcher,
) -> MeteringSummary:
    """Aggregate metrics from Better Stack (or any injected fetcher) into one summary."""
    atomizer_tokens = metrics_fetcher(
        "keiracom.atomization.atomizer.tokens",
        {"tenant_id": tenant_id},
        window_start,
        window_end,
    )
    atoms_produced_m = metrics_fetcher(
        "keiracom.atomization.atoms_produced",
        {"tenant_id": tenant_id},
        window_start,
        window_end,
    )
    atomizer_latency = metrics_fetcher(
        "keiracom.atomization.atomizer.latency_ms",
        {"tenant_id": tenant_id},
        window_start,
        window_end,
    )
    verifier_flags = metrics_fetcher(
        "keiracom.atomization.verifier.flags",
        {"tenant_id": tenant_id},
        window_start,
        window_end,
    )
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
    compositions = metrics_fetcher(
        "keiracom.atomization.compositions_per_task",
        {"tenant_id": tenant_id},
        window_start,
        window_end,
    )

    return MeteringSummary(
        tenant_id=tenant_id,
        window_start=window_start,
        window_end=window_end,
        atomizer_tokens_in=int(atomizer_tokens.get("in", 0)),
        atomizer_tokens_out=int(atomizer_tokens.get("out", 0)),
        atoms_produced=int(atoms_produced_m.get("count", 0)),
        atomizer_latency_ms_avg=float(atomizer_latency.get("avg", 0.0)),
        verifier_flags_info=int(verifier_flags.get("info", 0)),
        verifier_flags_warning=int(verifier_flags.get("warning", 0)),
        verifier_flags_blocking=int(verifier_flags.get("blocking", 0)),
        valkey_hits=int(valkey.get("hit", 0)),
        valkey_misses=int(valkey.get("miss", 0)),
        anthropic_create_tokens=int(anthropic.get("create", 0)),
        anthropic_read_tokens=int(anthropic.get("read", 0)),
        anthropic_standard_tokens=int(anthropic.get("standard", 0)),
        compositions_per_task_avg=float(compositions.get("avg", 0.0)),
    )


def render_report(summary: MeteringSummary) -> str:
    """Render a Markdown report Dave can read at a glance.

    Pure function — no I/O. Caller prints OR posts to keiracom.elliot.inbox.
    """
    total_atoms = summary.atoms_produced
    total_flags = (
        summary.verifier_flags_info
        + summary.verifier_flags_warning
        + summary.verifier_flags_blocking
    )
    valkey_total = summary.valkey_hits + summary.valkey_misses
    anthropic_total = (
        summary.anthropic_create_tokens
        + summary.anthropic_read_tokens
        + summary.anthropic_standard_tokens
    )

    return f"""# Atomization Pilot — Metering Report

**Tenant:** {summary.tenant_id}
**Window:** {summary.window_start.isoformat()} → {summary.window_end.isoformat()} UTC
**Duration:** {(summary.window_end - summary.window_start).total_seconds() / 3600:.1f} hours

## Atomizer

| Metric | Value |
|---|---|
| Atoms produced | {summary.atoms_produced:,} |
| Tokens in | {summary.atomizer_tokens_in:,} |
| Tokens out | {summary.atomizer_tokens_out:,} |
| Avg latency | {summary.atomizer_latency_ms_avg:.0f} ms |
| Grain | {classify_atomizer_grain(summary.atomizer_tokens_in, summary.atoms_produced)} |

## Verifier

| Metric | Value |
|---|---|
| Total flags | {total_flags:,} (info={summary.verifier_flags_info} warning={summary.verifier_flags_warning} blocking={summary.verifier_flags_blocking}) |
| Total atoms | {total_atoms:,} |
| Verifier verdict | {classify_verifier_rate(summary.verifier_flags_blocking, summary.verifier_flags_warning, total_atoms)} |

## Valkey semantic cache

| Metric | Value |
|---|---|
| Hits | {summary.valkey_hits:,} |
| Misses | {summary.valkey_misses:,} |
| Total lookups | {valkey_total:,} |
| Verdict | {classify_valkey_hit_rate(summary.valkey_hits, summary.valkey_misses)} |

## Anthropic prompt cache

| Metric | Value |
|---|---|
| cache_creation_input_tokens | {summary.anthropic_create_tokens:,} |
| cache_read_input_tokens | {summary.anthropic_read_tokens:,} |
| standard input_tokens | {summary.anthropic_standard_tokens:,} |
| Total | {anthropic_total:,} |
| Verdict | {classify_anthropic_cache_rate(summary.anthropic_create_tokens, summary.anthropic_read_tokens, summary.anthropic_standard_tokens)} |

## Composition curve (Week 2 pre-wired metric — calibration starts Week 3)

| Metric | Value |
|---|---|
| Compositions per task (avg) | {summary.compositions_per_task_avg:.2f} |
| Verdict | {classify_composition_curve(summary.compositions_per_task_avg)} |

## Action

- **Atomizer grain:** {classify_atomizer_grain(summary.atomizer_tokens_in, summary.atoms_produced)}
- **Verifier:** {classify_verifier_rate(summary.verifier_flags_blocking, summary.verifier_flags_warning, total_atoms)}
- **Valkey cache:** {classify_valkey_hit_rate(summary.valkey_hits, summary.valkey_misses)}
- **Anthropic cache:** {classify_anthropic_cache_rate(summary.anthropic_create_tokens, summary.anthropic_read_tokens, summary.anthropic_standard_tokens)}
- **Composition curve:** {classify_composition_curve(summary.compositions_per_task_avg)}

If any verdict shows BLOCKING-V1, pause customer onboarding until the underlying gauge is back into the healthy band. TRACK-AND-IMPROVE bands are non-blocking; flag for retro / next-iteration tuning.

## Honest framing

- **N=1 tenant (Dave)** — Week 3 baseline. Calibration data starts here.
- **First 3 paying customers + their first month of traffic = real calibration.** Bands above are conservative defaults pending real-traffic data.
- **Composition curve bands are PROVISIONAL** — they were chosen pre-data; real bands need a week of Dave-actual traffic before they're load-bearing.
"""


def generate_report(
    *,
    tenant_id: str,
    window_hours: int = 24,
    metrics_fetcher: MetricsFetcher,
    now: datetime | None = None,
) -> str:
    """End-to-end helper: fetch metrics + render report.

    `now` injectable for deterministic tests; default = utcnow.
    """
    end = now or datetime.now(UTC)
    start = end - timedelta(hours=window_hours)
    summary = fetch_summary(
        tenant_id=tenant_id,
        window_start=start,
        window_end=end,
        metrics_fetcher=metrics_fetcher,
    )
    return render_report(summary)
