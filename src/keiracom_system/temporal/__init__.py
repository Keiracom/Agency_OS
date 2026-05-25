"""keiracom_system.temporal — Temporal workflow engine integration.

Phase A6 build per bd Agency_OS-(A6).
"""

from .client import (
    DEFAULT_NAMESPACE,
    DEFAULT_TASK_QUEUE,
    TemporalConnectError,
    connect,
    from_env,
)

__all__ = [
    "DEFAULT_NAMESPACE",
    "DEFAULT_TASK_QUEUE",
    "TemporalConnectError",
    "connect",
    "from_env",
]
