"""Phase A8 §7 piece 2 — paused_tasks accessor layer.

Tenant-scoped Postgres access for the keiracom_paused_tasks table that
durably holds ephemeral-agent wait-state per PR #1140 §5. Mirrors the
read+write tenant-prefix-guard pattern from PR #1185 (AtomStore) +
PR #1173 (ValkeyClient).

Exports:
- PausedTaskRecord     — frozen dataclass row representation
- PausedTaskStore      — tenant-scoped accessor + tenant-prefix guard
- PausedTaskStoreError — accessor-specific exception
"""

from .store import PausedTaskRecord, PausedTaskStore, PausedTaskStoreError

__all__ = ["PausedTaskRecord", "PausedTaskStore", "PausedTaskStoreError"]
