"""
FILE: src/exceptions.py
PURPOSE: Custom exceptions for Agency OS
PHASE: 1 (Foundation + DevOps)
TASK: CFG-001
DEPENDENCIES: None
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
"""

from typing import Any


class AgencyOSError(Exception):
    """Base exception for all Agency OS errors."""

    def __init__(
        self, message: str, code: str | None = None, details: dict[str, Any] | None = None
    ):
        self.message = message
        self.code = code or "AGENCY_OS_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


# ============================================
# Authentication & Authorization Errors
# ============================================


class AuthenticationError(AgencyOSError):
    """User is not authenticated."""

    def __init__(
        self, message: str = "Authentication required", details: dict[str, Any] | None = None
    ):
        super().__init__(message, code="AUTHENTICATION_ERROR", details=details)


class AuthorizationError(AgencyOSError):
    """User is not authorized to perform this action."""

    def __init__(self, message: str = "Permission denied", details: dict[str, Any] | None = None):
        super().__init__(message, code="AUTHORIZATION_ERROR", details=details)


class InsufficientPermissionsError(AuthorizationError):
    """User lacks the required role/permissions."""

    def __init__(
        self,
        required_role: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"Role '{required_role}' or higher required"
        details = details or {}
        details["required_role"] = required_role
        super().__init__(message, details=details)


# ============================================
# Resource Errors
# ============================================


class ResourceNotFoundError(AgencyOSError):
    """Requested resource does not exist."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"{resource_type} not found: {resource_id}"
        details = details or {}
        details["resource_type"] = resource_type
        details["resource_id"] = resource_id
        super().__init__(message, code="RESOURCE_NOT_FOUND", details=details)


class ResourceExistsError(AgencyOSError):
    """Resource already exists (conflict)."""

    def __init__(
        self,
        resource_type: str,
        identifier: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"{resource_type} already exists: {identifier}"
        details = details or {}
        details["resource_type"] = resource_type
        details["identifier"] = identifier
        super().__init__(message, code="RESOURCE_EXISTS", details=details)


class ResourceDeletedError(AgencyOSError):
    """Resource has been soft-deleted."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"{resource_type} has been deleted: {resource_id}"
        details = details or {}
        details["resource_type"] = resource_type
        details["resource_id"] = resource_id
        super().__init__(message, code="RESOURCE_DELETED", details=details)


# ============================================
# Validation Errors
# ============================================


class ValidationError(AgencyOSError):
    """Data validation failed."""

    def __init__(
        self,
        message: str = "Validation error",
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class EnrichmentValidationError(ValidationError):
    """Enrichment data failed validation threshold."""

    def __init__(
        self,
        confidence: float,
        threshold: float,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = (
            message or f"Enrichment confidence {confidence:.2f} below threshold {threshold:.2f}"
        )
        details = details or {}
        details["confidence"] = confidence
        details["threshold"] = threshold
        super().__init__(message, details=details)
        self.code = "ENRICHMENT_VALIDATION_ERROR"


# ============================================
# Rate Limiting Errors
# ============================================


class RateLimitError(AgencyOSError):
    """Rate limit exceeded."""

    def __init__(
        self,
        limit_type: str,
        limit: int,
        reset_at: str | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"Rate limit exceeded for {limit_type}"
        details = details or {}
        details["limit_type"] = limit_type
        details["limit"] = limit
        if reset_at:
            details["reset_at"] = reset_at
        super().__init__(message, code="RATE_LIMIT_ERROR", details=details)


class ResourceRateLimitError(RateLimitError):
    """Resource-level rate limit exceeded (per seat/domain/number)."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        limit: int,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"{resource_type} rate limit exceeded for {resource_id}"
        details = details or {}
        details["resource_type"] = resource_type
        details["resource_id"] = resource_id
        super().__init__(resource_type, limit, message=message, details=details)
        self.code = "RESOURCE_RATE_LIMIT_ERROR"


# ============================================
# Billing & Credits Errors
# ============================================


class BillingError(AgencyOSError):
    """Billing-related error."""

    def __init__(self, message: str = "Billing error", details: dict[str, Any] | None = None):
        super().__init__(message, code="BILLING_ERROR", details=details)


class InsufficientCreditsError(BillingError):
    """Client does not have enough credits."""

    def __init__(
        self,
        required: int,
        available: int,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"Insufficient credits: need {required}, have {available}"
        details = details or {}
        details["required"] = required
        details["available"] = available
        super().__init__(message, details=details)
        self.code = "INSUFFICIENT_CREDITS"


class SubscriptionInactiveError(BillingError):
    """Client subscription is not active."""

    def __init__(
        self,
        status: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"Subscription is {status}"
        details = details or {}
        details["subscription_status"] = status
        super().__init__(message, details=details)
        self.code = "SUBSCRIPTION_INACTIVE"


class AISpendLimitError(BillingError):
    """Daily AI spend limit exceeded."""

    def __init__(
        self,
        spent: float,
        limit: float,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"AI spend limit exceeded: ${spent:.2f} of ${limit:.2f}"
        details = details or {}
        details["spent"] = spent
        details["limit"] = limit
        super().__init__(message, details=details)
        self.code = "AI_SPEND_LIMIT_ERROR"


# ============================================
# Integration Errors
# ============================================


class IntegrationError(AgencyOSError):
    """External integration error."""

    def __init__(
        self,
        service: str,
        message: str = "Integration error",
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        details["service"] = service
        super().__init__(message, code="INTEGRATION_ERROR", details=details)


class APIError(IntegrationError):
    """External API returned an error."""

    def __init__(
        self,
        service: str,
        status_code: int,
        response: str | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"{service} API error: {status_code}"
        details = details or {}
        details["status_code"] = status_code
        if response:
            details["response"] = response
        super().__init__(service, message, details=details)
        self.code = "API_ERROR"


class WebhookError(IntegrationError):
    """Webhook delivery failed."""

    def __init__(
        self,
        url: str,
        status_code: int | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"Webhook delivery failed: {url}"
        details = details or {}
        details["url"] = url
        if status_code:
            details["status_code"] = status_code
        super().__init__("webhook", message, details=details)
        self.code = "WEBHOOK_ERROR"


# ============================================
# Engine Errors
# ============================================


class EngineError(AgencyOSError):
    """Engine processing error."""

    def __init__(self, message: str = "Engine error", details: dict[str, Any] | None = None):
        super().__init__(message, code="ENGINE_ERROR", details=details)


# ============================================
# Orchestration Errors
# ============================================


class OrchestrationError(AgencyOSError):
    """Workflow/task orchestration error."""

    def __init__(self, message: str = "Orchestration error", details: dict[str, Any] | None = None):
        super().__init__(message, code="ORCHESTRATION_ERROR", details=details)


class TaskFailedError(OrchestrationError):
    """Prefect task failed."""

    def __init__(
        self,
        task_name: str,
        error: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"Task '{task_name}' failed: {error}"
        details = details or {}
        details["task_name"] = task_name
        details["error"] = error
        super().__init__(message, details=details)
        self.code = "TASK_FAILED"


class FlowFailedError(OrchestrationError):
    """Prefect flow failed."""

    def __init__(
        self,
        flow_name: str,
        error: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"Flow '{flow_name}' failed: {error}"
        details = details or {}
        details["flow_name"] = flow_name
        details["error"] = error
        super().__init__(message, details=details)
        self.code = "FLOW_FAILED"


# ============================================
# Suppression Errors
# ============================================


class SuppressionError(AgencyOSError):
    """Lead/email is suppressed."""

    def __init__(
        self,
        email: str,
        reason: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"Email suppressed: {email}"
        details = details or {}
        details["email"] = email
        details["reason"] = reason
        super().__init__(message, code="SUPPRESSION_ERROR", details=details)


class DNCRError(SuppressionError):
    """Phone number is on Do Not Call Registry."""

    def __init__(
        self,
        phone: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = message or f"Phone on DNCR: {phone}"
        super().__init__(phone, "dncr", message=message, details=details)
        self.code = "DNCR_ERROR"


# ============================================
# BACKWARD COMPATIBILITY ALIASES
# ============================================

# Alias for services that import NotFoundError instead of ResourceNotFoundError
NotFoundError = ResourceNotFoundError


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Base AgencyOSError with to_dict()
# [x] Authentication/Authorization errors
# [x] Resource errors (NotFound, Exists, Deleted)
# [x] Validation errors including EnrichmentValidationError
# [x] Rate limit errors including resource-level
# [x] Billing errors (credits, subscription, AI spend)
# [x] Integration errors (API, webhook)
# [x] Orchestration errors (task, flow)
# [x] Suppression errors (including DNCR)
# [x] All exceptions have type hints
# [x] All exceptions have docstrings
# [x] NotFoundError alias for backward compatibility
