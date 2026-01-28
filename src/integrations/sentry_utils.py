"""
FILE: src/integrations/sentry_utils.py
PURPOSE: Sentry utilities for integration layer
PHASE: DevOps (Audit remediation)
DEPENDENCIES:
  - sentry_sdk
  - src/config/settings.py
"""

import functools
from collections.abc import Callable
from typing import Any, TypeVar

import sentry_sdk

from src.config.settings import settings

F = TypeVar("F", bound=Callable[..., Any])


def track_integration_call(service: str) -> Callable[[F], F]:
    """
    Decorator to track external API calls in Sentry.

    Captures:
    - Service name (apollo, resend, etc.)
    - Success/failure
    - Error details with context

    Usage:
        @track_integration_call("apollo")
        async def enrich_person(self, email: str) -> dict:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with sentry_sdk.start_span(op="integration", description=f"{service}.{func.__name__}"):
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    # Add context before capturing
                    sentry_sdk.set_context("integration", {
                        "service": service,
                        "function": func.__name__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    })
                    sentry_sdk.capture_exception(e)
                    raise
        return wrapper  # type: ignore
    return decorator


def track_sync_integration_call(service: str) -> Callable[[F], F]:
    """Sync version of track_integration_call for non-async functions."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with sentry_sdk.start_span(op="integration", description=f"{service}.{func.__name__}"):
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    sentry_sdk.set_context("integration", {
                        "service": service,
                        "function": func.__name__,
                    })
                    sentry_sdk.capture_exception(e)
                    raise
        return wrapper  # type: ignore
    return decorator


def capture_business_error(
    error_type: str,
    message: str,
    context: dict[str, Any] | None = None,
    level: str = "error",
) -> None:
    """
    Capture business logic errors that don't throw exceptions.

    Use this for "silent failures" like:
    - Lead score calculated incorrectly
    - Campaign not sending when it should
    - Data validation passed but shouldn't have

    Args:
        error_type: Category of error (e.g., "scoring_anomaly", "campaign_stalled")
        message: Human-readable description
        context: Additional data for debugging
        level: Sentry level (error, warning, info)

    Usage:
        if lead.score > 100:
            capture_business_error(
                "scoring_anomaly",
                f"Lead score exceeded maximum: {lead.score}",
                context={"lead_id": lead.id, "score": lead.score}
            )
    """
    if not settings.sentry_dsn:
        return

    with sentry_sdk.push_scope() as scope:
        scope.set_tag("error_type", error_type)
        scope.set_level(level)
        if context:
            scope.set_context("business_error", context)
        sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str, email: str | None = None, client_id: str | None = None) -> None:
    """Set user context for all subsequent Sentry events in this request."""
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "client_id": client_id,
    })


def add_breadcrumb(message: str, category: str = "info", data: dict | None = None) -> None:
    """Add a breadcrumb to track steps leading to an error."""
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        data=data or {},
    )
