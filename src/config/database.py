# Re-export database utilities for backward compatibility
# Actual implementation is in src.integrations.supabase

from src.integrations.supabase import get_db_session, get_async_engine, AsyncSessionLocal

__all__ = ["get_db_session", "get_async_engine", "AsyncSessionLocal"]
