"""KEI-165 — governance model proxy: body-schema validation + N enumerated denials.

Stub for the Part 17 product layer. Validates inbound request bodies against
a minimal schema, then applies an enumerated deny-list derived from
docs/governance/CONSOLIDATED_RULES.md (3 patterns for the stub; full rule-set
is a later KEI). Denials are LOGGED at WARNING level with the reason code +
tenant_id (no body payload — denial logs must not echo prompt contents).

Acceptance (Linear KEI-165): proxy accepts valid body; denies enumerated
patterns (start with 3); logs denials.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Final

logger = logging.getLogger(__name__)

SOURCE_DOC: Final = "docs/governance/CONSOLIDATED_RULES.md"

# Enumerated deny patterns (verbatim string names from CONSOLIDATED_RULES.md):
DENY_VERIFY_RULE: Final = "verify_rule_no_inline_evidence"
DENY_BUSINESS_RULE: Final = "business_rule_usd_without_aud"
DENY_GOVERN_RULE: Final = "govern_rule_hook_bypass"

_COMPLETION_WORDS = re.compile(r"\b(done|complete|merged|shipped)\b", re.IGNORECASE)
_EVIDENCE_MARKER = re.compile(r"\$\s")  # dollar-space — standard shell-prompt evidence shape
_USD_PATTERNS = re.compile(r"(?:\bUSD\b|\$USD|U\$)")
_AUD_PATTERNS = re.compile(r"(?:\bAUD\b|\$AUD|A\$)")
_HOOK_BYPASS = re.compile(r"(?:--no-verify|--no-gpg-sign|--skip-hooks)")


@dataclass(frozen=True)
class RequestBody:
    tenant_id: str
    prompt: str
    max_tokens: int


@dataclass(frozen=True)
class ProxyDecision:
    allowed: bool
    reason: str | None = None
    body: RequestBody | None = None


class SchemaError(ValueError):
    """Raised when the request body fails minimal schema validation."""


def _validate_schema(body_dict: dict) -> RequestBody:
    """Parse + validate minimal request shape. Raises SchemaError on failure."""
    tenant_id = body_dict.get("tenant_id")
    if not tenant_id:
        raise SchemaError("tenant_id is required and must be non-empty")

    prompt = body_dict.get("prompt")
    if prompt is None:
        raise SchemaError("prompt is required")
    if not isinstance(prompt, str) or prompt == "":
        raise SchemaError("prompt must be a non-empty string")

    max_tokens = body_dict.get("max_tokens")
    if max_tokens is None:
        raise SchemaError("max_tokens is required")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
        raise SchemaError("max_tokens must be a positive integer")

    return RequestBody(tenant_id=str(tenant_id), prompt=prompt, max_tokens=max_tokens)


def _check_enumerated_denials(prompt: str) -> str | None:
    """Apply the 3 enumerated patterns. Returns the matching deny reason or None.

    Evaluation order is deterministic: VERIFY -> BUSINESS -> GOVERN.
    """
    # RULE 1 VERIFY: bare completion claim without shell-prompt evidence
    if _COMPLETION_WORDS.search(prompt) and not _EVIDENCE_MARKER.search(prompt):
        return DENY_VERIFY_RULE

    # RULE 7 BUSINESS: USD mentioned without AUD counterpart
    if _USD_PATTERNS.search(prompt) and not _AUD_PATTERNS.search(prompt):
        return DENY_BUSINESS_RULE

    # RULE 6 GOVERN: hook bypass flags present
    if _HOOK_BYPASS.search(prompt):
        return DENY_GOVERN_RULE

    return None


def evaluate(body_dict: dict) -> ProxyDecision:
    """Single-call entry: validate schema then check deny patterns.

    Returns:
        ProxyDecision(allowed=True, body=RequestBody) on accept;
        ProxyDecision(allowed=False, reason='schema:<msg>') on schema failure;
        ProxyDecision(allowed=False, reason='deny:<rule_name>') on enumerated deny.
    """
    try:
        body = _validate_schema(body_dict)
    except SchemaError as exc:
        return ProxyDecision(allowed=False, reason=f"schema:{exc}")

    denial_reason = _check_enumerated_denials(body.prompt)
    if denial_reason is not None:
        logger.warning(
            "governance_proxy: DENY tenant_id=%s reason=%s",
            body.tenant_id,
            denial_reason,
        )
        return ProxyDecision(allowed=False, reason=f"deny:{denial_reason}")

    return ProxyDecision(allowed=True, body=body)
