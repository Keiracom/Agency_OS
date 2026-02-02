#!/usr/bin/env python3
"""
Behavior Cache (Muscle-Mem)
===========================
A caching layer that remembers successful action sequences.
Instead of re-thinking from scratch, replay known solutions.

Inspired by: https://github.com/pig-dot-dev/muscle-mem

Usage:
    @behavior_cached("check_server_status")
    def check_server_status():
        # Steps are recorded on first run
        # Replayed on subsequent runs
        
    # Or use directly:
    cache = BehaviorCache()
    cache.start_recording("task_name")
    # ... do steps ...
    cache.record_step("step_1", {"action": "curl", "url": "..."})
    cache.stop_recording()
    
    # Later:
    if cache.has_behavior("task_name"):
        steps = cache.replay("task_name")
"""

import os
import json
import hashlib
import functools
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable, Any, TypeVar, List, Dict
from dataclasses import dataclass, asdict
import threading

# Type variable for decorator
F = TypeVar('F', bound=Callable[..., Any])

# ============================================
# Configuration
# ============================================

CACHE_DIR = Path(__file__).parent.parent / ".cache" / "behaviors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# How long before a cached behavior expires (hours)
DEFAULT_TTL_HOURS = 168  # 1 week

# Similarity threshold for fuzzy matching
SIMILARITY_THRESHOLD = 0.8


# ============================================
# Data Structures
# ============================================

@dataclass
class BehaviorStep:
    """A single step in a behavior sequence."""
    index: int
    action: str
    params: dict
    result: Optional[Any] = None
    duration_ms: Optional[int] = None
    timestamp: Optional[str] = None


@dataclass  
class CachedBehavior:
    """A complete cached behavior sequence."""
    name: str
    description: str
    steps: List[BehaviorStep]
    context_hash: str  # Hash of input parameters
    created_at: str
    last_used: str
    use_count: int
    success_rate: float
    avg_duration_ms: int
    
    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "steps": [asdict(s) for s in self.steps]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CachedBehavior":
        steps = [BehaviorStep(**s) for s in data.pop("steps", [])]
        return cls(steps=steps, **data)


# ============================================
# Behavior Cache Core
# ============================================

class BehaviorCache:
    """
    Main behavior cache manager.
    Records, stores, and replays action sequences.
    """
    
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Recording state
        self._recording = False
        self._current_name: Optional[str] = None
        self._current_steps: List[BehaviorStep] = []
        self._current_context: dict = {}
        self._record_start: Optional[datetime] = None
        
        # Thread safety
        self._lock = threading.Lock()
    
    def _get_cache_path(self, name: str, context_hash: str = "") -> Path:
        """Get cache file path for a behavior."""
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        if context_hash:
            return self.cache_dir / f"{safe_name}_{context_hash[:8]}.json"
        return self.cache_dir / f"{safe_name}.json"
    
    def _hash_context(self, context: dict) -> str:
        """Create hash of context for matching."""
        # Sort keys for consistency
        normalized = json.dumps(context, sort_keys=True, default=str)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    # ============================================
    # Recording API
    # ============================================
    
    def start_recording(self, name: str, context: dict = None, description: str = "") -> None:
        """Start recording a new behavior sequence."""
        with self._lock:
            self._recording = True
            self._current_name = name
            self._current_steps = []
            self._current_context = context or {}
            self._current_description = description
            self._record_start = datetime.now(timezone.utc)
    
    def record_step(
        self,
        action: str,
        params: dict = None,
        result: Any = None,
    ) -> None:
        """Record a single step in the current behavior."""
        if not self._recording:
            return
        
        with self._lock:
            step = BehaviorStep(
                index=len(self._current_steps),
                action=action,
                params=params or {},
                result=result,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self._current_steps.append(step)
    
    def stop_recording(self, success: bool = True) -> Optional[CachedBehavior]:
        """Stop recording and save the behavior."""
        if not self._recording:
            return None
        
        with self._lock:
            self._recording = False
            
            if not success or not self._current_steps:
                # Don't cache failed behaviors
                return None
            
            # Calculate duration
            duration_ms = 0
            if self._record_start:
                duration = datetime.now(timezone.utc) - self._record_start
                duration_ms = int(duration.total_seconds() * 1000)
            
            # Create behavior
            context_hash = self._hash_context(self._current_context)
            now = datetime.now(timezone.utc).isoformat()
            
            behavior = CachedBehavior(
                name=self._current_name,
                description=self._current_description,
                steps=self._current_steps,
                context_hash=context_hash,
                created_at=now,
                last_used=now,
                use_count=1,
                success_rate=1.0,
                avg_duration_ms=duration_ms,
            )
            
            # Save to disk
            self._save_behavior(behavior)
            
            return behavior
    
    def _save_behavior(self, behavior: CachedBehavior) -> None:
        """Save behavior to cache file."""
        cache_path = self._get_cache_path(behavior.name, behavior.context_hash)
        cache_path.write_text(json.dumps(behavior.to_dict(), indent=2))
    
    # ============================================
    # Lookup & Replay API
    # ============================================
    
    def has_behavior(self, name: str, context: dict = None) -> bool:
        """Check if a cached behavior exists."""
        return self.get_behavior(name, context) is not None
    
    def get_behavior(
        self,
        name: str,
        context: dict = None,
        max_age_hours: int = DEFAULT_TTL_HOURS,
    ) -> Optional[CachedBehavior]:
        """Get a cached behavior if it exists and is fresh."""
        context_hash = self._hash_context(context or {})
        
        # Try exact match first
        cache_path = self._get_cache_path(name, context_hash)
        if cache_path.exists():
            behavior = self._load_behavior(cache_path)
            if behavior and self._is_fresh(behavior, max_age_hours):
                return behavior
        
        # Try without context hash (generic behavior)
        cache_path = self._get_cache_path(name)
        if cache_path.exists():
            behavior = self._load_behavior(cache_path)
            if behavior and self._is_fresh(behavior, max_age_hours):
                return behavior
        
        return None
    
    def _load_behavior(self, path: Path) -> Optional[CachedBehavior]:
        """Load behavior from cache file."""
        try:
            data = json.loads(path.read_text())
            return CachedBehavior.from_dict(data)
        except Exception:
            return None
    
    def _is_fresh(self, behavior: CachedBehavior, max_age_hours: int) -> bool:
        """Check if behavior is within TTL."""
        try:
            created = datetime.fromisoformat(behavior.created_at.replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - created
            return age.total_seconds() / 3600 < max_age_hours
        except Exception:
            return False
    
    def replay(self, name: str, context: dict = None) -> Optional[List[BehaviorStep]]:
        """
        Get steps to replay for a cached behavior.
        Updates usage stats.
        """
        behavior = self.get_behavior(name, context)
        if not behavior:
            return None
        
        # Update usage stats
        with self._lock:
            behavior.last_used = datetime.now(timezone.utc).isoformat()
            behavior.use_count += 1
            self._save_behavior(behavior)
        
        return behavior.steps
    
    # ============================================
    # Management API
    # ============================================
    
    def list_behaviors(self) -> List[dict]:
        """List all cached behaviors."""
        behaviors = []
        for path in self.cache_dir.glob("*.json"):
            try:
                behavior = self._load_behavior(path)
                if behavior:
                    behaviors.append({
                        "name": behavior.name,
                        "description": behavior.description,
                        "steps": len(behavior.steps),
                        "use_count": behavior.use_count,
                        "created_at": behavior.created_at,
                        "last_used": behavior.last_used,
                    })
            except Exception:
                pass
        return behaviors
    
    def clear_behavior(self, name: str) -> bool:
        """Clear a specific cached behavior."""
        cleared = False
        for path in self.cache_dir.glob(f"{name}*.json"):
            path.unlink()
            cleared = True
        return cleared
    
    def clear_all(self) -> int:
        """Clear all cached behaviors."""
        count = 0
        for path in self.cache_dir.glob("*.json"):
            path.unlink()
            count += 1
        return count


# ============================================
# Decorator API
# ============================================

# Global cache instance
_default_cache = BehaviorCache()


def behavior_cached(
    name: Optional[str] = None,
    description: str = "",
    context_keys: List[str] = None,
    ttl_hours: int = DEFAULT_TTL_HOURS,
) -> Callable[[F], F]:
    """
    Decorator that caches function behavior.
    
    On first call: Records the function execution
    On subsequent calls: Returns cached result if behavior exists
    
    Args:
        name: Behavior name (defaults to function name)
        description: Human-readable description
        context_keys: Argument names to include in cache key
        ttl_hours: Cache TTL in hours
    
    Example:
        @behavior_cached("check_server_status")
        def check_server():
            # This sequence is recorded
            result1 = ping_server()
            result2 = check_health()
            return {"ping": result1, "health": result2}
    """
    def decorator(func: F) -> F:
        behavior_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build context from specified keys
            context = {}
            if context_keys:
                for key in context_keys:
                    if key in kwargs:
                        context[key] = kwargs[key]
            
            # Check for cached behavior
            behavior = _default_cache.get_behavior(behavior_name, context, ttl_hours)
            
            if behavior:
                # Return cached result from last step
                last_step = behavior.steps[-1] if behavior.steps else None
                if last_step and last_step.result is not None:
                    print(f"[BEHAVIOR_CACHE] Replaying '{behavior_name}' ({len(behavior.steps)} steps)")
                    
                    # Update usage
                    _default_cache.replay(behavior_name, context)
                    
                    return last_step.result
            
            # No cache - record new behavior
            _default_cache.start_recording(behavior_name, context, description)
            
            try:
                result = func(*args, **kwargs)
                
                # Record the final result
                _default_cache.record_step(
                    action=f"{func.__name__}_complete",
                    params={"args": str(args)[:200], "kwargs": str(kwargs)[:200]},
                    result=result,
                )
                
                _default_cache.stop_recording(success=True)
                
                return result
                
            except Exception as e:
                _default_cache.stop_recording(success=False)
                raise
        
        return wrapper
    return decorator


def record_step(action: str, params: dict = None, result: Any = None) -> None:
    """Record a step in the current behavior (if recording)."""
    _default_cache.record_step(action, params, result)


def get_cache() -> BehaviorCache:
    """Get the default cache instance."""
    return _default_cache


# ============================================
# CLI Interface
# ============================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Behavior Cache Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # List command
    list_parser = subparsers.add_parser("list", help="List cached behaviors")
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear cached behaviors")
    clear_parser.add_argument("name", nargs="?", help="Behavior name (or 'all')")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test behavior caching")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show cache statistics")
    
    args = parser.parse_args()
    cache = BehaviorCache()
    
    if args.command == "list":
        behaviors = cache.list_behaviors()
        if behaviors:
            print(f"📋 Cached Behaviors ({len(behaviors)}):\n")
            for b in behaviors:
                print(f"  • {b['name']}")
                print(f"    Steps: {b['steps']} | Uses: {b['use_count']}")
                print(f"    Last used: {b['last_used'][:19]}")
                print()
        else:
            print("No cached behaviors yet.")
    
    elif args.command == "clear":
        if args.name == "all":
            count = cache.clear_all()
            print(f"✅ Cleared {count} cached behaviors")
        elif args.name:
            if cache.clear_behavior(args.name):
                print(f"✅ Cleared behavior: {args.name}")
            else:
                print(f"❌ Behavior not found: {args.name}")
        else:
            print("Specify behavior name or 'all'")
    
    elif args.command == "stats":
        behaviors = cache.list_behaviors()
        total_steps = sum(b["steps"] for b in behaviors)
        total_uses = sum(b["use_count"] for b in behaviors)
        
        print("📊 Behavior Cache Statistics")
        print(f"   Behaviors cached: {len(behaviors)}")
        print(f"   Total steps: {total_steps}")
        print(f"   Total replays: {total_uses}")
        print(f"   Cache directory: {CACHE_DIR}")
    
    elif args.command == "test":
        print("🧪 Testing Behavior Cache...\n")
        
        # Define a test function
        @behavior_cached("test_server_check", description="Test server health check")
        def test_check():
            # Simulate some work
            import time
            print("   Executing step 1: Ping server...")
            record_step("ping", {"host": "localhost"}, {"latency_ms": 5})
            time.sleep(0.1)
            
            print("   Executing step 2: Check health...")
            record_step("health_check", {"endpoint": "/health"}, {"status": "ok"})
            time.sleep(0.1)
            
            print("   Executing step 3: Get metrics...")
            record_step("metrics", {"path": "/metrics"}, {"cpu": 45, "mem": 60})
            
            return {"status": "healthy", "checks": 3}
        
        print("First run (recording):")
        result1 = test_check()
        print(f"   Result: {result1}\n")
        
        print("Second run (should replay from cache):")
        result2 = test_check()
        print(f"   Result: {result2}\n")
        
        print("✅ Test complete! Check 'list' command to see cached behavior.")


if __name__ == "__main__":
    main()
