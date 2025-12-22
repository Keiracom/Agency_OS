# FILE: src/api/__init__.py
# PURPOSE: API package initialization
# PHASE: 7 (API Routes)
# TASK: API-001

"""Agency OS API Package."""

# Note: app is imported from src.api.main directly, not from this __init__.py
# to avoid circular imports during module initialization.

__all__ = ["app"]
