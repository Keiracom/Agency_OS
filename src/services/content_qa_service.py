"""
Contract: src/services/content_qa_service.py
Purpose: Pre-send content quality validation for all outreach channels
Layer: 3 - services
Imports: none (standalone)
Consumers: outreach_flow

FILE: src/services/content_qa_service.py
PURPOSE: Pre-send content quality validation for all outreach channels
PHASE: 22 (Content QA Check)
TASK: Item 22
DEPENDENCIES:
  - None (standalone service)
LAYER: 3 (services)
CONSUMERS: outreach_flow.py

This service validates generated content BEFORE sending to catch:
- Unresolved placeholders ({{first_name}}, [COMPANY], etc.)
- Length violations (too short/too long)
- Spam trigger words (FREE, URGENT, ACT NOW, etc.)
- Missing personalization
- Formatting issues

Design Decisions:
- Separate from JIT validator (eligibility vs quality)
- Returns detailed QA result with all issues found
- Configurable thresholds per channel
- Safe fallback recommendations when content fails
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class QAStatus(str, Enum):
    """Content QA validation status."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"  # Passed but has minor issues


class ContentChannel(str, Enum):
    """Supported content channels."""

    EMAIL = "email"
    SMS = "sms"
    LINKEDIN = "linkedin"
    VOICE = "voice"


@dataclass
class QAIssue:
    """Single QA issue found in content."""

    code: str  # e.g., "placeholder_found", "too_long"
    severity: str  # "error" or "warning"
    message: str  # Human-readable description
    content_field: str | None = None  # "subject", "body", "message"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class QAResult:
    """Result of content QA validation."""

    status: QAStatus
    channel: ContentChannel
    issues: list[QAIssue] = field(default_factory=list)
    checks_performed: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if content passed QA (no errors)."""
        return self.status in (QAStatus.PASSED, QAStatus.WARNING)

    @property
    def has_errors(self) -> bool:
        """True if any error-level issues found."""
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        """True if any warning-level issues found."""
        return any(i.severity == "warning" for i in self.issues)

    @property
    def error_messages(self) -> list[str]:
        """List of error messages."""
        return [i.message for i in self.issues if i.severity == "error"]

    def to_dict(self) -> dict[str, Any]:
        """Serialize for logging/API."""
        return {
            "status": self.status.value,
            "channel": self.channel.value,
            "passed": self.passed,
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity,
                    "message": i.message,
                    "field": i.content_field,
                    "details": i.details,
                }
                for i in self.issues
            ],
            "checks_performed": self.checks_performed,
        }


# =============================================================================
# CONFIGURATION: Channel-specific limits and rules
# =============================================================================

# Length limits per channel
LENGTH_LIMITS = {
    ContentChannel.EMAIL: {
        "subject_min": 10,
        "subject_max": 100,
        "body_min": 50,
        "body_max": 3000,
    },
    ContentChannel.SMS: {
        "message_min": 20,
        "message_max": 160,
    },
    ContentChannel.LINKEDIN: {
        "connection_min": 20,
        "connection_max": 300,
        "inmail_min": 50,
        "inmail_max": 1000,
    },
    ContentChannel.VOICE: {
        "opening_min": 10,
        "opening_max": 200,
        "value_prop_min": 20,
        "value_prop_max": 500,
        "cta_min": 10,
        "cta_max": 200,
    },
}

# Placeholder patterns to detect (unresolved template variables)
PLACEHOLDER_PATTERNS = [
    r"\{\{[^}]+\}\}",  # {{first_name}}, {{company}}
    r"\[\[[^\]]+\]\]",  # [[FIRST_NAME]], [[COMPANY]]
    r"\[[A-Z_]+\]",  # [FIRST_NAME], [COMPANY]
    r"<[A-Z_]+>",  # <FIRST_NAME>, <COMPANY>
    r"\{[a-z_]+\}",  # {first_name}, {company}
    r"%[A-Z_]+%",  # %FIRST_NAME%, %COMPANY%
]

# Spam trigger words/phrases (case-insensitive)
SPAM_TRIGGERS = [
    # Urgency
    r"\bURGENT\b",
    r"\bACT NOW\b",
    r"\bLIMITED TIME\b",
    r"\bDON'T MISS\b",
    r"\bLAST CHANCE\b",
    r"\bEXPIRES?\b",
    r"\bIMMEDIATE(LY)?\b",
    # Money/Free
    r"\bFREE\b",
    r"\b\$\d+",
    r"\bDISCOUNT\b",
    r"\bSAVE \d+%",
    r"\bMONEY BACK\b",
    r"\bNO COST\b",
    r"\bCHEAP\b",
    # Pressure
    r"\bGUARANTEE[DS]?\b",
    r"\bNO OBLIGATION\b",
    r"\bRISK[- ]FREE\b",
    r"\bCALL NOW\b",
    r"\bORDER NOW\b",
    r"\bBUY NOW\b",
    r"\bCLICK HERE\b",
    r"\bCLICK BELOW\b",
    # Suspicious
    r"\bCONGRAT(ULATION)?S?\b",
    r"\bWINNER\b",
    r"\bSELECTED\b",
    r"\bYOU'VE BEEN CHOSEN\b",
    # Excessive punctuation (3+ in a row)
    r"[!?]{3,}",
    r"\.{4,}",
]

# Generic/template phrases that suggest poor personalization
GENERIC_PHRASES = [
    r"\bDear Sir or Madam\b",
    r"\bTo Whom It May Concern\b",
    r"\bDear Customer\b",
    r"\bDear Friend\b",
    r"\bHello there\b",
    r"\bI hope this email finds you well\b",
    r"\bI am writing to\b",
    r"\bI wanted to reach out\b",
    r"\bI came across your profile\b",
]


class ContentQAService:
    """
    Service for validating content quality before sending.

    Provides channel-specific validation for:
    - Email (subject + body)
    - SMS (message)
    - LinkedIn (connection request or InMail)
    - Voice (opening + value_prop + cta)
    """

    def __init__(self):
        """Initialize the Content QA service."""
        self._placeholder_regex = re.compile("|".join(PLACEHOLDER_PATTERNS), re.IGNORECASE)
        self._spam_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in SPAM_TRIGGERS]
        self._generic_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in GENERIC_PHRASES]

    # =========================================================================
    # PUBLIC: Channel-specific validation methods
    # =========================================================================

    def validate_email(
        self,
        subject: str,
        body: str,
        lead_first_name: str | None = None,
        lead_company: str | None = None,
    ) -> QAResult:
        """
        Validate email content (subject + body).

        Args:
            subject: Email subject line
            body: Email body content
            lead_first_name: Lead's first name (for personalization check)
            lead_company: Lead's company name (for personalization check)

        Returns:
            QAResult with validation status and any issues found
        """
        issues: list[QAIssue] = []
        checks: list[str] = []
        limits = LENGTH_LIMITS[ContentChannel.EMAIL]

        # 1. Check subject length
        checks.append("subject_length")
        subject_len = len(subject) if subject else 0
        if subject_len < limits["subject_min"]:
            issues.append(
                QAIssue(
                    code="subject_too_short",
                    severity="error",
                    message=f"Subject too short ({subject_len} chars, min {limits['subject_min']})",
                    content_field="subject",
                    details={"length": subject_len, "min": limits["subject_min"]},
                )
            )
        elif subject_len > limits["subject_max"]:
            issues.append(
                QAIssue(
                    code="subject_too_long",
                    severity="warning",
                    message=f"Subject too long ({subject_len} chars, max {limits['subject_max']})",
                    content_field="subject",
                    details={"length": subject_len, "max": limits["subject_max"]},
                )
            )

        # 2. Check body length
        checks.append("body_length")
        body_len = len(body) if body else 0
        if body_len < limits["body_min"]:
            issues.append(
                QAIssue(
                    code="body_too_short",
                    severity="error",
                    message=f"Body too short ({body_len} chars, min {limits['body_min']})",
                    content_field="body",
                    details={"length": body_len, "min": limits["body_min"]},
                )
            )
        elif body_len > limits["body_max"]:
            issues.append(
                QAIssue(
                    code="body_too_long",
                    severity="warning",
                    message=f"Body too long ({body_len} chars, max {limits['body_max']})",
                    content_field="body",
                    details={"length": body_len, "max": limits["body_max"]},
                )
            )

        # 3. Check for placeholders in subject
        checks.append("subject_placeholders")
        subject_placeholders = self._find_placeholders(subject or "")
        if subject_placeholders:
            issues.append(
                QAIssue(
                    code="placeholder_in_subject",
                    severity="error",
                    message=f"Unresolved placeholder(s) in subject: {', '.join(subject_placeholders)}",
                    content_field="subject",
                    details={"placeholders": subject_placeholders},
                )
            )

        # 4. Check for placeholders in body
        checks.append("body_placeholders")
        body_placeholders = self._find_placeholders(body or "")
        if body_placeholders:
            issues.append(
                QAIssue(
                    code="placeholder_in_body",
                    severity="error",
                    message=f"Unresolved placeholder(s) in body: {', '.join(body_placeholders)}",
                    content_field="body",
                    details={"placeholders": body_placeholders},
                )
            )

        # 5. Check for spam triggers in subject
        checks.append("subject_spam")
        subject_spam = self._find_spam_triggers(subject or "")
        if subject_spam:
            issues.append(
                QAIssue(
                    code="spam_in_subject",
                    severity="error",
                    message=f"Spam trigger(s) in subject: {', '.join(subject_spam[:3])}",
                    content_field="subject",
                    details={"triggers": subject_spam},
                )
            )

        # 6. Check for spam triggers in body (warning only)
        checks.append("body_spam")
        body_spam = self._find_spam_triggers(body or "")
        if body_spam:
            issues.append(
                QAIssue(
                    code="spam_in_body",
                    severity="warning",
                    message=f"Potential spam trigger(s) in body: {', '.join(body_spam[:3])}",
                    content_field="body",
                    details={"triggers": body_spam},
                )
            )

        # 7. Check for generic phrases
        checks.append("generic_phrases")
        generic = self._find_generic_phrases(body or "")
        if generic:
            issues.append(
                QAIssue(
                    code="generic_phrase",
                    severity="warning",
                    message=f"Generic phrase(s) detected: {', '.join(generic[:2])}",
                    content_field="body",
                    details={"phrases": generic},
                )
            )

        # 8. Check personalization (if lead data provided)
        if lead_first_name or lead_company:
            checks.append("personalization")
            has_name = lead_first_name and lead_first_name.lower() in (body or "").lower()
            has_company = lead_company and lead_company.lower() in (body or "").lower()
            if not has_name and not has_company:
                issues.append(
                    QAIssue(
                        code="no_personalization",
                        severity="warning",
                        message="Content doesn't mention lead's name or company",
                        content_field="body",
                        details={"checked_name": lead_first_name, "checked_company": lead_company},
                    )
                )

        # 9. Check subject is not ALL CAPS
        checks.append("subject_caps")
        if subject and len(subject) > 10 and subject.isupper():
            issues.append(
                QAIssue(
                    code="subject_all_caps",
                    severity="error",
                    message="Subject line is all caps (spam indicator)",
                    content_field="subject",
                )
            )

        # Determine overall status
        status = self._determine_status(issues)

        logger.debug(
            f"Email QA: {status.value} - {len(issues)} issues, "
            f"subject_len={subject_len}, body_len={body_len}"
        )

        return QAResult(
            status=status,
            channel=ContentChannel.EMAIL,
            issues=issues,
            checks_performed=checks,
        )

    def validate_sms(
        self,
        message: str,
        lead_first_name: str | None = None,
    ) -> QAResult:
        """
        Validate SMS message content.

        Args:
            message: SMS message content
            lead_first_name: Lead's first name (for personalization check)

        Returns:
            QAResult with validation status and any issues found
        """
        issues: list[QAIssue] = []
        checks: list[str] = []
        limits = LENGTH_LIMITS[ContentChannel.SMS]

        # 1. Check message length
        checks.append("message_length")
        msg_len = len(message) if message else 0
        if msg_len < limits["message_min"]:
            issues.append(
                QAIssue(
                    code="message_too_short",
                    severity="error",
                    message=f"SMS too short ({msg_len} chars, min {limits['message_min']})",
                    content_field="message",
                    details={"length": msg_len, "min": limits["message_min"]},
                )
            )
        elif msg_len > limits["message_max"]:
            issues.append(
                QAIssue(
                    code="message_too_long",
                    severity="error",
                    message=f"SMS too long ({msg_len} chars, max {limits['message_max']})",
                    content_field="message",
                    details={"length": msg_len, "max": limits["message_max"]},
                )
            )

        # 2. Check for placeholders
        checks.append("placeholders")
        placeholders = self._find_placeholders(message or "")
        if placeholders:
            issues.append(
                QAIssue(
                    code="placeholder_found",
                    severity="error",
                    message=f"Unresolved placeholder(s): {', '.join(placeholders)}",
                    content_field="message",
                    details={"placeholders": placeholders},
                )
            )

        # 3. Check for spam triggers
        checks.append("spam_triggers")
        spam = self._find_spam_triggers(message or "")
        if spam:
            issues.append(
                QAIssue(
                    code="spam_trigger",
                    severity="warning",
                    message=f"Potential spam trigger(s): {', '.join(spam[:3])}",
                    content_field="message",
                    details={"triggers": spam},
                )
            )

        # 4. Check personalization
        if lead_first_name:
            checks.append("personalization")
            if lead_first_name.lower() not in (message or "").lower():
                issues.append(
                    QAIssue(
                        code="no_personalization",
                        severity="warning",
                        message="SMS doesn't mention lead's name",
                        content_field="message",
                    )
                )

        status = self._determine_status(issues)

        logger.debug(f"SMS QA: {status.value} - {len(issues)} issues, len={msg_len}")

        return QAResult(
            status=status,
            channel=ContentChannel.SMS,
            issues=issues,
            checks_performed=checks,
        )

    def validate_linkedin(
        self,
        message: str,
        message_type: str = "connection",
        lead_first_name: str | None = None,
    ) -> QAResult:
        """
        Validate LinkedIn message content.

        Args:
            message: LinkedIn message content
            message_type: "connection" or "inmail"
            lead_first_name: Lead's first name (for personalization check)

        Returns:
            QAResult with validation status and any issues found
        """
        issues: list[QAIssue] = []
        checks: list[str] = []
        limits = LENGTH_LIMITS[ContentChannel.LINKEDIN]

        # Determine limits based on message type
        if message_type == "inmail":
            min_len = limits["inmail_min"]
            max_len = limits["inmail_max"]
        else:
            min_len = limits["connection_min"]
            max_len = limits["connection_max"]

        # 1. Check message length
        checks.append("message_length")
        msg_len = len(message) if message else 0
        if msg_len < min_len:
            issues.append(
                QAIssue(
                    code="message_too_short",
                    severity="error",
                    message=f"LinkedIn {message_type} too short ({msg_len} chars, min {min_len})",
                    content_field="message",
                    details={"length": msg_len, "min": min_len, "type": message_type},
                )
            )
        elif msg_len > max_len:
            issues.append(
                QAIssue(
                    code="message_too_long",
                    severity="error",
                    message=f"LinkedIn {message_type} too long ({msg_len} chars, max {max_len})",
                    content_field="message",
                    details={"length": msg_len, "max": max_len, "type": message_type},
                )
            )

        # 2. Check for placeholders
        checks.append("placeholders")
        placeholders = self._find_placeholders(message or "")
        if placeholders:
            issues.append(
                QAIssue(
                    code="placeholder_found",
                    severity="error",
                    message=f"Unresolved placeholder(s): {', '.join(placeholders)}",
                    content_field="message",
                    details={"placeholders": placeholders},
                )
            )

        # 3. Check for spam triggers
        checks.append("spam_triggers")
        spam = self._find_spam_triggers(message or "")
        if spam:
            issues.append(
                QAIssue(
                    code="spam_trigger",
                    severity="warning",
                    message=f"Potential spam trigger(s): {', '.join(spam[:3])}",
                    content_field="message",
                    details={"triggers": spam},
                )
            )

        # 4. Check for generic phrases
        checks.append("generic_phrases")
        generic = self._find_generic_phrases(message or "")
        if generic:
            issues.append(
                QAIssue(
                    code="generic_phrase",
                    severity="warning",
                    message=f"Generic phrase(s) detected: {', '.join(generic[:2])}",
                    content_field="message",
                    details={"phrases": generic},
                )
            )

        # 5. Check personalization
        if lead_first_name:
            checks.append("personalization")
            if lead_first_name.lower() not in (message or "").lower():
                issues.append(
                    QAIssue(
                        code="no_personalization",
                        severity="warning",
                        message="LinkedIn message doesn't mention lead's name",
                        content_field="message",
                    )
                )

        status = self._determine_status(issues)

        logger.debug(
            f"LinkedIn QA ({message_type}): {status.value} - {len(issues)} issues, len={msg_len}"
        )

        return QAResult(
            status=status,
            channel=ContentChannel.LINKEDIN,
            issues=issues,
            checks_performed=checks,
        )

    def validate_voice(
        self,
        opening: str,
        value_prop: str,
        cta: str,
        lead_first_name: str | None = None,
    ) -> QAResult:
        """
        Validate voice script content.

        Args:
            opening: Opening statement
            value_prop: Value proposition
            cta: Call to action
            lead_first_name: Lead's first name (for personalization check)

        Returns:
            QAResult with validation status and any issues found
        """
        issues: list[QAIssue] = []
        checks: list[str] = []
        limits = LENGTH_LIMITS[ContentChannel.VOICE]

        # Check each component
        components = [
            ("opening", opening, limits["opening_min"], limits["opening_max"]),
            ("value_prop", value_prop, limits["value_prop_min"], limits["value_prop_max"]),
            ("cta", cta, limits["cta_min"], limits["cta_max"]),
        ]

        for field_name, content, min_len, max_len in components:
            checks.append(f"{field_name}_length")
            content_len = len(content) if content else 0

            if content_len < min_len:
                issues.append(
                    QAIssue(
                        code=f"{field_name}_too_short",
                        severity="error",
                        message=f"Voice {field_name} too short ({content_len} chars, min {min_len})",
                        content_field=field_name,
                        details={"length": content_len, "min": min_len},
                    )
                )
            elif content_len > max_len:
                issues.append(
                    QAIssue(
                        code=f"{field_name}_too_long",
                        severity="warning",
                        message=f"Voice {field_name} too long ({content_len} chars, max {max_len})",
                        content_field=field_name,
                        details={"length": content_len, "max": max_len},
                    )
                )

            # Check for placeholders
            checks.append(f"{field_name}_placeholders")
            placeholders = self._find_placeholders(content or "")
            if placeholders:
                issues.append(
                    QAIssue(
                        code="placeholder_found",
                        severity="error",
                        message=f"Unresolved placeholder(s) in {field_name}: {', '.join(placeholders)}",
                        content_field=field_name,
                        details={"placeholders": placeholders},
                    )
                )

        # Check personalization in opening
        if lead_first_name:
            checks.append("personalization")
            if lead_first_name.lower() not in (opening or "").lower():
                issues.append(
                    QAIssue(
                        code="no_personalization",
                        severity="warning",
                        message="Voice opening doesn't mention lead's name",
                        content_field="opening",
                    )
                )

        status = self._determine_status(issues)

        logger.debug(f"Voice QA: {status.value} - {len(issues)} issues")

        return QAResult(
            status=status,
            channel=ContentChannel.VOICE,
            issues=issues,
            checks_performed=checks,
        )

    # =========================================================================
    # PRIVATE: Helper methods
    # =========================================================================

    def _find_placeholders(self, content: str) -> list[str]:
        """Find all unresolved placeholders in content."""
        if not content:
            return []
        matches = self._placeholder_regex.findall(content)
        return list(set(matches))  # Dedupe

    def _find_spam_triggers(self, content: str) -> list[str]:
        """Find spam trigger words/phrases in content."""
        if not content:
            return []
        triggers = []
        for regex in self._spam_regexes:
            matches = regex.findall(content)
            triggers.extend(matches)
        return list(set(triggers))  # Dedupe

    def _find_generic_phrases(self, content: str) -> list[str]:
        """Find generic/template phrases in content."""
        if not content:
            return []
        phrases = []
        for regex in self._generic_regexes:
            matches = regex.findall(content)
            phrases.extend(matches)
        return list(set(phrases))  # Dedupe

    def _determine_status(self, issues: list[QAIssue]) -> QAStatus:
        """Determine overall QA status based on issues."""
        has_errors = any(i.severity == "error" for i in issues)
        has_warnings = any(i.severity == "warning" for i in issues)

        if has_errors:
            return QAStatus.FAILED
        elif has_warnings:
            return QAStatus.WARNING
        else:
            return QAStatus.PASSED


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_content_qa_service: ContentQAService | None = None


def get_content_qa_service() -> ContentQAService:
    """Get singleton ContentQAService instance."""
    global _content_qa_service
    if _content_qa_service is None:
        _content_qa_service = ContentQAService()
    return _content_qa_service


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def validate_email_content(
    subject: str,
    body: str,
    lead_first_name: str | None = None,
    lead_company: str | None = None,
) -> QAResult:
    """
    Convenience function to validate email content.

    Args:
        subject: Email subject line
        body: Email body
        lead_first_name: Lead's first name
        lead_company: Lead's company name

    Returns:
        QAResult with validation status
    """
    service = get_content_qa_service()
    return service.validate_email(subject, body, lead_first_name, lead_company)


def validate_sms_content(
    message: str,
    lead_first_name: str | None = None,
) -> QAResult:
    """
    Convenience function to validate SMS content.

    Args:
        message: SMS message
        lead_first_name: Lead's first name

    Returns:
        QAResult with validation status
    """
    service = get_content_qa_service()
    return service.validate_sms(message, lead_first_name)


def validate_linkedin_content(
    message: str,
    message_type: str = "connection",
    lead_first_name: str | None = None,
) -> QAResult:
    """
    Convenience function to validate LinkedIn content.

    Args:
        message: LinkedIn message
        message_type: "connection" or "inmail"
        lead_first_name: Lead's first name

    Returns:
        QAResult with validation status
    """
    service = get_content_qa_service()
    return service.validate_linkedin(message, message_type, lead_first_name)


def validate_voice_script(
    script: str,
    lead_first_name: str | None = None,
) -> QAResult:
    """
    Convenience function to validate voice script content.

    Validates a single voice script string for:
    - Minimum length (50 chars)
    - Maximum length (2000 chars)
    - Placeholder detection
    - Spam trigger detection

    Args:
        script: Voice script text
        lead_first_name: Lead's first name (for personalization check)

    Returns:
        QAResult with validation status
    """
    service = get_content_qa_service()
    issues: list[QAIssue] = []
    checks: list[str] = []

    # Length limits for voice scripts
    min_len = 50
    max_len = 2000

    # 1. Check script length
    checks.append("script_length")
    script_len = len(script) if script else 0
    if script_len < min_len:
        issues.append(
            QAIssue(
                code="script_too_short",
                severity="error",
                message=f"Voice script too short ({script_len} chars, min {min_len})",
                content_field="script",
                details={"length": script_len, "min": min_len},
            )
        )
    elif script_len > max_len:
        issues.append(
            QAIssue(
                code="script_too_long",
                severity="warning",
                message=f"Voice script too long ({script_len} chars, max {max_len})",
                content_field="script",
                details={"length": script_len, "max": max_len},
            )
        )

    # 2. Check for placeholders
    checks.append("placeholders")
    placeholders = service._find_placeholders(script or "")
    if placeholders:
        issues.append(
            QAIssue(
                code="placeholder_found",
                severity="error",
                message=f"Unresolved placeholder(s): {', '.join(placeholders)}",
                content_field="script",
                details={"placeholders": placeholders},
            )
        )

    # 3. Check for spam triggers (warning only for voice)
    checks.append("spam_triggers")
    spam = service._find_spam_triggers(script or "")
    if spam:
        issues.append(
            QAIssue(
                code="spam_trigger",
                severity="warning",
                message=f"Potential spam trigger(s): {', '.join(spam[:3])}",
                content_field="script",
                details={"triggers": spam},
            )
        )

    # 4. Check personalization
    if lead_first_name:
        checks.append("personalization")
        if lead_first_name.lower() not in (script or "").lower():
            issues.append(
                QAIssue(
                    code="no_personalization",
                    severity="warning",
                    message="Voice script doesn't mention lead's name",
                    content_field="script",
                )
            )

    # Determine status
    status = service._determine_status(issues)

    return QAResult(
        status=status,
        channel=ContentChannel.VOICE,
        issues=issues,
        checks_performed=checks,
    )


# =============================================================================
# VERIFICATION CHECKLIST
# =============================================================================
# [x] Contract comment at top of file
# [x] Layer 3 service (no engine/integration/orchestration imports)
# [x] All methods have type hints
# [x] All methods have docstrings
# [x] Configurable limits per channel
# [x] Placeholder detection (multiple formats)
# [x] Spam trigger detection
# [x] Generic phrase detection
# [x] Personalization validation
# [x] Length validation (min/max)
# [x] QAResult with detailed issues
# [x] Singleton access pattern
# [x] Convenience functions for easy integration
