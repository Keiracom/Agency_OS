"""Per-spawn attribution logging — Cat 21 lever 27 / Cutover Blocker 6.

Captures (source_type, source_id) at dispatch time so every spawn is
traceable back to its triggering event (Slack message / PR / cron / inbox).

Exports:
- SOURCE_TYPES — frozenset of legal source_type values
- SpawnAttributionEntry — frozen dataclass row representation
- log_spawn_attribution — write one event to the JSONL log
- load_attribution_last_24h — read recent events for aggregation
"""

from .logger import (
    SOURCE_TYPES,
    SpawnAttributionEntry,
    load_attribution_last_24h,
    log_spawn_attribution,
)

__all__ = [
    "SOURCE_TYPES",
    "SpawnAttributionEntry",
    "load_attribution_last_24h",
    "log_spawn_attribution",
]
