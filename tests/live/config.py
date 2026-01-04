"""
FILE: tests/live/config.py
PURPOSE: Configuration for live UX testing with real integrations
PHASE: 15 (Live UX Testing)
TASK: LUX-001

This module provides configuration for running live tests against
production services. All sensitive values come from environment variables.

IMPORTANT: These tests make REAL API calls that cost money.
Only run in controlled test environments.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class LiveTestConfig:
    """Configuration for live UX testing."""

    # ========================================
    # Database Configuration
    # ========================================
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "TEST_DATABASE_URL",
            os.environ.get("DATABASE_URL", "")
        )
    )
    supabase_url: str = field(
        default_factory=lambda: os.environ.get("SUPABASE_URL", "")
    )
    supabase_key: str = field(
        default_factory=lambda: os.environ.get("SUPABASE_SERVICE_KEY", "")
    )

    # ========================================
    # API Configuration
    # ========================================
    api_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "API_BASE_URL",
            "https://agency-os-production.up.railway.app"
        )
    )
    frontend_url: str = field(
        default_factory=lambda: os.environ.get(
            "FRONTEND_URL",
            "https://agency-os-liart.vercel.app"
        )
    )

    # ========================================
    # Test Client Configuration
    # ========================================
    test_client_name: str = "Live Test Agency"
    test_client_website: str = field(
        default_factory=lambda: os.environ.get(
            "TEST_CLIENT_WEBSITE",
            "https://example-agency.com"
        )
    )
    test_client_tier: str = "velocity"

    # ========================================
    # Test User Configuration
    # ========================================
    test_user_email: str = field(
        default_factory=lambda: os.environ.get(
            "TEST_USER_EMAIL",
            "test@example.com"
        )
    )
    test_user_name: str = field(
        default_factory=lambda: os.environ.get(
            "TEST_USER_NAME",
            "Test User"
        )
    )

    # ========================================
    # Test Lead Configuration (YOU as the lead)
    # ========================================
    test_lead_email: str = field(
        default_factory=lambda: os.environ.get(
            "TEST_LEAD_EMAIL",
            ""  # Must be set - this is YOUR email
        )
    )
    test_lead_phone: str = field(
        default_factory=lambda: os.environ.get(
            "TEST_LEAD_PHONE",
            ""  # Optional - YOUR phone for SMS tests
        )
    )
    test_lead_first_name: str = field(
        default_factory=lambda: os.environ.get(
            "TEST_LEAD_FIRST_NAME",
            "Test"
        )
    )
    test_lead_last_name: str = field(
        default_factory=lambda: os.environ.get(
            "TEST_LEAD_LAST_NAME",
            "Lead"
        )
    )
    test_lead_company: str = field(
        default_factory=lambda: os.environ.get(
            "TEST_LEAD_COMPANY",
            "Test Company Pty Ltd"
        )
    )
    test_lead_title: str = field(
        default_factory=lambda: os.environ.get(
            "TEST_LEAD_TITLE",
            "CEO"
        )
    )

    # ========================================
    # Integration Keys (for verification)
    # ========================================
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    apollo_api_key: str = field(
        default_factory=lambda: os.environ.get("APOLLO_API_KEY", "")
    )
    resend_api_key: str = field(
        default_factory=lambda: os.environ.get("RESEND_API_KEY", "")
    )
    twilio_account_sid: str = field(
        default_factory=lambda: os.environ.get("TWILIO_ACCOUNT_SID", "")
    )
    twilio_auth_token: str = field(
        default_factory=lambda: os.environ.get("TWILIO_AUTH_TOKEN", "")
    )
    apify_api_key: str = field(
        default_factory=lambda: os.environ.get("APIFY_API_KEY", "")
    )

    # ========================================
    # Test Control
    # ========================================
    skip_email_tests: bool = field(
        default_factory=lambda: os.environ.get("SKIP_EMAIL_TESTS", "false").lower() == "true"
    )
    skip_sms_tests: bool = field(
        default_factory=lambda: os.environ.get("SKIP_SMS_TESTS", "true").lower() == "true"
    )
    skip_linkedin_tests: bool = field(
        default_factory=lambda: os.environ.get("SKIP_LINKEDIN_TESTS", "true").lower() == "true"
    )
    dry_run: bool = field(
        default_factory=lambda: os.environ.get("LIVE_TEST_DRY_RUN", "true").lower() == "true"
    )

    def validate(self) -> list[str]:
        """Validate configuration and return list of missing items."""
        errors = []

        # Required for all tests
        if not self.database_url:
            errors.append("DATABASE_URL or TEST_DATABASE_URL not set")
        if not self.supabase_url:
            errors.append("SUPABASE_URL not set")
        if not self.supabase_key:
            errors.append("SUPABASE_SERVICE_KEY not set")

        # Required for ICP extraction
        if not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY not set")
        if not self.apify_api_key:
            errors.append("APIFY_API_KEY not set (needed for website scraping)")

        # Required for enrichment
        if not self.apollo_api_key:
            errors.append("APOLLO_API_KEY not set (needed for lead enrichment)")

        # Required for email tests
        if not self.skip_email_tests:
            if not self.resend_api_key:
                errors.append("RESEND_API_KEY not set (needed for email tests)")
            if not self.test_lead_email:
                errors.append("TEST_LEAD_EMAIL not set (your email for receiving test emails)")

        # Required for SMS tests
        if not self.skip_sms_tests:
            if not self.twilio_account_sid or not self.twilio_auth_token:
                errors.append("TWILIO credentials not set (needed for SMS tests)")
            if not self.test_lead_phone:
                errors.append("TEST_LEAD_PHONE not set (your phone for receiving test SMS)")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0

    def print_status(self) -> None:
        """Print configuration status."""
        print("\n" + "=" * 60)
        print("LIVE TEST CONFIGURATION STATUS")
        print("=" * 60)

        print(f"\nDatabase URL: {'✅ Set' if self.database_url else '❌ Missing'}")
        print(f"Supabase URL: {'✅ Set' if self.supabase_url else '❌ Missing'}")
        print(f"API Base URL: {self.api_base_url}")
        print(f"Frontend URL: {self.frontend_url}")

        print(f"\nTest Lead Email: {self.test_lead_email or '❌ Not set'}")
        print(f"Test Lead Phone: {self.test_lead_phone or '⏭️ Not set (SMS skipped)'}")

        print("\nIntegrations:")
        print(f"  Anthropic: {'✅' if self.anthropic_api_key else '❌'}")
        print(f"  Apollo: {'✅' if self.apollo_api_key else '❌'}")
        print(f"  Apify: {'✅' if self.apify_api_key else '❌'}")
        print(f"  Resend: {'✅' if self.resend_api_key else '❌'}")
        print(f"  Twilio: {'✅' if self.twilio_account_sid else '❌'}")

        print("\nTest Modes:")
        print(f"  Dry Run: {'✅ Enabled (no real sends)' if self.dry_run else '⚠️ DISABLED (real sends!)'}")
        print(f"  Skip Email: {'✅' if self.skip_email_tests else '❌'}")
        print(f"  Skip SMS: {'✅' if self.skip_sms_tests else '❌'}")
        print(f"  Skip LinkedIn: {'✅' if self.skip_linkedin_tests else '❌'}")

        errors = self.validate()
        if errors:
            print("\n⚠️ VALIDATION ERRORS:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("\n✅ Configuration valid!")

        print("=" * 60 + "\n")


# Singleton instance
_config: Optional[LiveTestConfig] = None


def get_config() -> LiveTestConfig:
    """Get the live test configuration singleton."""
    global _config
    if _config is None:
        _config = LiveTestConfig()
    return _config


def require_valid_config() -> LiveTestConfig:
    """Get config and raise if invalid."""
    config = get_config()
    errors = config.validate()
    if errors:
        raise ValueError(
            f"Invalid live test configuration:\n" +
            "\n".join(f"  - {e}" for e in errors)
        )
    return config


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials (all from env)
# [x] Dataclass for configuration
# [x] Validation method for required fields
# [x] Print status for debugging
# [x] Dry run mode for safety
# [x] Skip flags for optional integrations
# [x] Singleton pattern for config access
