"""
Elliot Redis State Manager
==========================
Simple session state persistence for cross-session continuity.

Keys managed:
- elliot:current_task - Currently active task/goal
- elliot:last_session - Previous session summary
- elliot:pending_todos - Queue of deferred tasks
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional, TypedDict
from urllib.parse import urlparse

import redis

# ============================================
# Configuration
# ============================================

def get_redis_url() -> str:
    """Get Redis URL from environment."""
    url = os.environ.get("UPSTASH_REDIS_URL") or os.environ.get("REDIS_URL")
    if not url:
        raise ValueError("UPSTASH_REDIS_URL or REDIS_URL must be set")
    return url


def get_redis_client() -> redis.Redis:
    """Create Redis client from environment URL."""
    url = get_redis_url()
    parsed = urlparse(url)
    
    # Upstash uses rediss:// (TLS)
    use_ssl = parsed.scheme == "rediss"
    
    return redis.Redis(
        host=parsed.hostname,
        port=parsed.port or (6380 if use_ssl else 6379),
        password=parsed.password,
        ssl=use_ssl,
        decode_responses=True
    )


# ============================================
# Type Definitions
# ============================================

class CurrentTask(TypedDict, total=False):
    task: Optional[str]
    started_at: Optional[str]
    context: Optional[dict]
    priority: Optional[str]


class LastSession(TypedDict, total=False):
    session_id: Optional[str]
    ended_at: Optional[str]
    summary: Optional[str]
    key_decisions: Optional[list[str]]
    unfinished_work: Optional[list[str]]


class TodoItem(TypedDict):
    id: str
    task: str
    created_at: str
    priority: str  # high, medium, low
    context: Optional[dict]


# ============================================
# State Manager Class
# ============================================

class ElliotStateManager:
    """
    Manages Elliot's cross-session state in Redis.
    
    Usage:
        state = ElliotStateManager()
        state.set_current_task("Building learning system")
        task = state.get_current_task()
    """
    
    PREFIX = "elliot:"
    
    # Key definitions
    CURRENT_TASK = "elliot:current_task"
    LAST_SESSION = "elliot:last_session"
    PENDING_TODOS = "elliot:pending_todos"
    
    # TTLs (in seconds)
    DEFAULT_TTL = 86400 * 7  # 7 days
    TASK_TTL = 86400  # 1 day
    
    def __init__(self, client: Optional[redis.Redis] = None):
        """Initialize with optional Redis client."""
        self._client = client
    
    @property
    def client(self) -> redis.Redis:
        """Lazy-load Redis client."""
        if self._client is None:
            self._client = get_redis_client()
        return self._client
    
    def _now_iso(self) -> str:
        """Current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()
    
    # ============================================
    # Generic Get/Set
    # ============================================
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a JSON value from Redis."""
        full_key = key if key.startswith(self.PREFIX) else f"{self.PREFIX}{key}"
        value = self.client.get(full_key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a JSON value in Redis."""
        full_key = key if key.startswith(self.PREFIX) else f"{self.PREFIX}{key}"
        json_value = json.dumps(value, default=str)
        if ttl:
            return bool(self.client.setex(full_key, ttl, json_value))
        return bool(self.client.set(full_key, json_value))
    
    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        full_key = key if key.startswith(self.PREFIX) else f"{self.PREFIX}{key}"
        return bool(self.client.delete(full_key))
    
    # ============================================
    # Current Task
    # ============================================
    
    def get_current_task(self) -> CurrentTask:
        """Get the current active task."""
        return self.get(self.CURRENT_TASK, {
            "task": None,
            "started_at": None,
            "context": None,
            "priority": None
        })
    
    def set_current_task(
        self,
        task: str,
        context: Optional[dict] = None,
        priority: str = "medium"
    ) -> bool:
        """Set the current active task."""
        return self.set(self.CURRENT_TASK, {
            "task": task,
            "started_at": self._now_iso(),
            "context": context,
            "priority": priority
        }, ttl=self.TASK_TTL)
    
    def clear_current_task(self) -> bool:
        """Clear the current task (completed or abandoned)."""
        return self.set(self.CURRENT_TASK, {
            "task": None,
            "started_at": None,
            "context": None,
            "priority": None
        })
    
    # ============================================
    # Last Session
    # ============================================
    
    def get_last_session(self) -> LastSession:
        """Get the last session summary."""
        return self.get(self.LAST_SESSION, {
            "session_id": None,
            "ended_at": None,
            "summary": None,
            "key_decisions": [],
            "unfinished_work": []
        })
    
    def save_session_end(
        self,
        session_id: str,
        summary: str,
        key_decisions: Optional[list[str]] = None,
        unfinished_work: Optional[list[str]] = None
    ) -> bool:
        """Save session end state for next session bootstrap."""
        return self.set(self.LAST_SESSION, {
            "session_id": session_id,
            "ended_at": self._now_iso(),
            "summary": summary,
            "key_decisions": key_decisions or [],
            "unfinished_work": unfinished_work or []
        }, ttl=self.DEFAULT_TTL)
    
    # ============================================
    # Pending Todos
    # ============================================
    
    def get_pending_todos(self) -> list[TodoItem]:
        """Get all pending todo items."""
        return self.get(self.PENDING_TODOS, [])
    
    def add_todo(
        self,
        task: str,
        priority: str = "medium",
        context: Optional[dict] = None
    ) -> str:
        """Add a todo item, returns the todo ID."""
        import uuid
        
        todos = self.get_pending_todos()
        todo_id = str(uuid.uuid4())[:8]
        
        todos.append({
            "id": todo_id,
            "task": task,
            "created_at": self._now_iso(),
            "priority": priority,
            "context": context
        })
        
        self.set(self.PENDING_TODOS, todos, ttl=self.DEFAULT_TTL)
        return todo_id
    
    def complete_todo(self, todo_id: str) -> bool:
        """Mark a todo as complete (remove from list)."""
        todos = self.get_pending_todos()
        original_len = len(todos)
        todos = [t for t in todos if t.get("id") != todo_id]
        
        if len(todos) < original_len:
            self.set(self.PENDING_TODOS, todos, ttl=self.DEFAULT_TTL)
            return True
        return False
    
    def clear_todos(self) -> bool:
        """Clear all pending todos."""
        return self.set(self.PENDING_TODOS, [])
    
    # ============================================
    # Utility Methods
    # ============================================
    
    def get_bootstrap_state(self) -> dict:
        """
        Get all state needed for session bootstrap.
        Returns a combined dict of all relevant state.
        """
        return {
            "current_task": self.get_current_task(),
            "last_session": self.get_last_session(),
            "pending_todos": self.get_pending_todos(),
            "retrieved_at": self._now_iso()
        }
    
    def health_check(self) -> bool:
        """Check Redis connectivity."""
        try:
            return self.client.ping()
        except Exception:
            return False


# ============================================
# Module-level convenience functions
# ============================================

_default_manager: Optional[ElliotStateManager] = None


def get_manager() -> ElliotStateManager:
    """Get the default state manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = ElliotStateManager()
    return _default_manager


# Convenience functions
def get_current_task() -> CurrentTask:
    return get_manager().get_current_task()


def set_current_task(task: str, **kwargs) -> bool:
    return get_manager().set_current_task(task, **kwargs)


def get_last_session() -> LastSession:
    return get_manager().get_last_session()


def save_session_end(session_id: str, summary: str, **kwargs) -> bool:
    return get_manager().save_session_end(session_id, summary, **kwargs)


def get_pending_todos() -> list[TodoItem]:
    return get_manager().get_pending_todos()


def add_todo(task: str, **kwargs) -> str:
    return get_manager().add_todo(task, **kwargs)


def complete_todo(todo_id: str) -> bool:
    return get_manager().complete_todo(todo_id)


def get_bootstrap_state() -> dict:
    return get_manager().get_bootstrap_state()


# ============================================
# CLI for testing
# ============================================

if __name__ == "__main__":
    import sys
    
    manager = ElliotStateManager()
    
    if not manager.health_check():
        print("❌ Redis connection failed")
        sys.exit(1)
    
    print("✅ Redis connected")
    print(f"\nCurrent state:")
    print(json.dumps(manager.get_bootstrap_state(), indent=2))
