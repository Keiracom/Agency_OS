"""Work-loop consumer — closes the self-driving loop (Agency_OS-s3ye).

Postgres trigger → Valkey `keiracom:tasks:available` → tier-gated consumer →
`/dispatcher/spawn`. The consumer enforces per-tenant concurrency ceilings with
an atomic Lua INCR+compare, overflows (never drops) at the ceiling, and releases
slots on agent exit (popping the overflow to spawn the next task).
"""

from src.keiracom_system.work_loop.consumer import WorkLoopConsumer

__all__ = ["WorkLoopConsumer"]
