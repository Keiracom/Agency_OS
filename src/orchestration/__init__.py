"""
FILE: src/orchestration/__init__.py
PURPOSE: Orchestration package - Prefect flows and tasks
PHASE: 5 (Orchestration)
"""

# Lazy import to avoid PrefectAgent deprecation error during module load
# Worker is only needed when explicitly running the worker process


def start_worker():
    """Lazy wrapper to import and start the worker."""
    from src.orchestration.worker import start_worker as _start_worker
    return _start_worker()


__all__ = ["start_worker"]
