"""
Basic smoke tests for src/governance/restate_service module.

These tests verify:
- Module imports cleanly (given restate-sdk installed)
- The `governance` virtual object exists
- Required handler names are registered on the object
"""
import importlib
import sys
import types
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stub_restate() -> None:
    """Install a minimal stub of the restate package so tests run without
    the restate-sdk installed in CI / local envs that skip it."""
    if "restate" in sys.modules:
        return

    class _ObjectContext:
        async def get(self, key):
            return None
        async def set(self, key, value):
            pass

    class _VirtualObject:
        def __init__(self, name: str):
            self.name = name
            self._handlers: dict[str, object] = {}

        def handler(self):
            def decorator(fn):
                self._handlers[fn.__name__] = fn
                return fn
            return decorator

    def _app(services):
        return object()  # dummy ASGI app

    restate_mod = types.ModuleType("restate")
    restate_mod.VirtualObject = _VirtualObject
    restate_mod.ObjectContext = _ObjectContext

    server_mod = types.ModuleType("restate.server")
    server_mod.app = _app

    sys.modules["restate"] = restate_mod
    sys.modules["restate.server"] = server_mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_module_imports():
    _stub_restate()
    mod = importlib.import_module("src.governance.restate_service")
    assert mod is not None


def test_governance_object_exists():
    _stub_restate()
    mod = importlib.import_module("src.governance.restate_service")
    assert hasattr(mod, "governance"), "governance VirtualObject not found on module"


def test_handler_names_registered():
    _stub_restate()
    mod = importlib.import_module("src.governance.restate_service")
    obj = mod.governance
    handlers = obj._handlers
    assert "directive_start" in handlers, "directive_start handler missing"
    assert "directive_complete" in handlers, "directive_complete handler missing"
    assert "get_state" in handlers, "get_state handler missing"


def test_asgi_app_exists():
    _stub_restate()
    mod = importlib.import_module("src.governance.restate_service")
    assert hasattr(mod, "asgi_app"), "asgi_app not exposed on module"
