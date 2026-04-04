# src/prefect_utils/__init__.py
# Shim — re-exports EVO-003 hooks from Agency_OS/src/prefect_utils/
# This allows `from src.prefect_utils.completion_hook import on_completion_hook`
# to resolve correctly under pytest and at runtime without sys.path manipulation.
