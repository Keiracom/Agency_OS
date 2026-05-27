"""Per-spawn attribution logging — Cat 21 levers 23 + 27 / Cutover Blockers 6 + 7.

Captures (source_type, source_id, task_type) at dispatch time so every spawn
is traceable back to its triggering event AND its workload class.

Exports:
- SOURCE_TYPES — frozenset of legal source_type values (slack/pr/cron/inbox/unknown)
- TASK_TYPES — frozenset of legal task_type values (pr_review/deliberation/build/chat/dispatch_mgmt/unknown)
- SpawnAttributionEntry — frozen dataclass row representation
- log_spawn_attribution — write one event to the JSONL log
- load_attribution_last_24h — read recent events for aggregation
"""

from .logger import (
    COMPLETION_STATUSES,
    SOURCE_TYPES,
    TASK_TYPES,
    SpawnAttributionEntry,
    aggregate_by_completion_status,
    load_attribution_last_24h,
    log_spawn_attribution,
)

__all__ = [
    "COMPLETION_STATUSES",
    "SOURCE_TYPES",
    "TASK_TYPES",
    "SpawnAttributionEntry",
    "aggregate_by_completion_status",
    "load_attribution_last_24h",
    "log_spawn_attribution",
]
