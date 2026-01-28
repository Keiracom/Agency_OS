"""
Contract: src/services/timezone_service.py
Purpose: Timezone lookup, UTC offset calculation, and optimal send time for leads
Layer: 3 - services
Imports: models
Consumers: channel engines, orchestration, WHEN detector

FILE: src/services/timezone_service.py
PURPOSE: Timezone lookup, UTC offset calculation, and optimal send time for leads
PHASE: 24C (Email Engagement Tracking), Phase D (Email Distribution)
TASK: ENGAGE-005, ED-TZ-001
DEPENDENCIES:
  - src/models/lead.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Services can import from models only
SPEC: docs/architecture/distribution/EMAIL_DISTRIBUTION.md

This service provides timezone lookup for leads based on their location data.
Used by the WHEN Detector to optimize send times based on lead's local time.

Phase D additions:
- Australian state-level timezone mapping (per CEO decision 2026-01-20)
- 9-11 AM optimal email send window (per spec)
"""

import random
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.lead import Lead

# Australian state-level timezone mapping (per EMAIL_DISTRIBUTION.md spec)
# CEO Decision 2026-01-20: State-level granularity for Australia
AUSTRALIAN_STATE_TIMEZONES = {
    # Eastern (AEST/AEDT) - observes DST
    "new south wales": "Australia/Sydney",
    "nsw": "Australia/Sydney",
    "victoria": "Australia/Melbourne",
    "vic": "Australia/Melbourne",
    "tasmania": "Australia/Hobart",
    "tas": "Australia/Hobart",
    "australian capital territory": "Australia/Sydney",
    "act": "Australia/Sydney",
    # Queensland (AEST - no DST)
    "queensland": "Australia/Brisbane",
    "qld": "Australia/Brisbane",
    # Central (ACST/ACDT) - observes DST
    "south australia": "Australia/Adelaide",
    "sa": "Australia/Adelaide",
    # Central (ACST - no DST)
    "northern territory": "Australia/Darwin",
    "nt": "Australia/Darwin",
    # Western (AWST - no DST)
    "western australia": "Australia/Perth",
    "wa": "Australia/Perth",
}


# Country to primary timezone mapping (most common/capital timezone)
# This is a simplified mapping - production should use a more comprehensive database
COUNTRY_TIMEZONE_MAP = {
    # North America
    "united states": "America/New_York",
    "us": "America/New_York",
    "usa": "America/New_York",
    "canada": "America/Toronto",
    "mexico": "America/Mexico_City",
    # Europe
    "united kingdom": "Europe/London",
    "uk": "Europe/London",
    "gb": "Europe/London",
    "germany": "Europe/Berlin",
    "france": "Europe/Paris",
    "italy": "Europe/Rome",
    "spain": "Europe/Madrid",
    "netherlands": "Europe/Amsterdam",
    "belgium": "Europe/Brussels",
    "switzerland": "Europe/Zurich",
    "austria": "Europe/Vienna",
    "sweden": "Europe/Stockholm",
    "norway": "Europe/Oslo",
    "denmark": "Europe/Copenhagen",
    "finland": "Europe/Helsinki",
    "ireland": "Europe/Dublin",
    "poland": "Europe/Warsaw",
    "portugal": "Europe/Lisbon",
    "greece": "Europe/Athens",
    "czech republic": "Europe/Prague",
    "czechia": "Europe/Prague",
    "hungary": "Europe/Budapest",
    "romania": "Europe/Bucharest",
    # Asia Pacific
    "australia": "Australia/Sydney",
    "new zealand": "Pacific/Auckland",
    "japan": "Asia/Tokyo",
    "china": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "singapore": "Asia/Singapore",
    "india": "Asia/Kolkata",
    "south korea": "Asia/Seoul",
    "korea": "Asia/Seoul",
    "taiwan": "Asia/Taipei",
    "philippines": "Asia/Manila",
    "indonesia": "Asia/Jakarta",
    "malaysia": "Asia/Kuala_Lumpur",
    "thailand": "Asia/Bangkok",
    "vietnam": "Asia/Ho_Chi_Minh",
    "pakistan": "Asia/Karachi",
    "bangladesh": "Asia/Dhaka",
    "sri lanka": "Asia/Colombo",
    # Middle East
    "israel": "Asia/Jerusalem",
    "united arab emirates": "Asia/Dubai",
    "uae": "Asia/Dubai",
    "saudi arabia": "Asia/Riyadh",
    "turkey": "Europe/Istanbul",
    "qatar": "Asia/Qatar",
    "kuwait": "Asia/Kuwait",
    # Africa
    "south africa": "Africa/Johannesburg",
    "nigeria": "Africa/Lagos",
    "egypt": "Africa/Cairo",
    "kenya": "Africa/Nairobi",
    "morocco": "Africa/Casablanca",
    # South America
    "brazil": "America/Sao_Paulo",
    "argentina": "America/Argentina/Buenos_Aires",
    "chile": "America/Santiago",
    "colombia": "America/Bogota",
    "peru": "America/Lima",
    "venezuela": "America/Caracas",
    # Central America & Caribbean
    "costa rica": "America/Costa_Rica",
    "panama": "America/Panama",
    "jamaica": "America/Jamaica",
    "puerto rico": "America/Puerto_Rico",
    # Russia & CIS
    "russia": "Europe/Moscow",
    "ukraine": "Europe/Kiev",
}

# US State to timezone mapping (for more precise US timezone detection)
US_STATE_TIMEZONE_MAP = {
    # Eastern
    "connecticut": "America/New_York",
    "delaware": "America/New_York",
    "florida": "America/New_York",
    "georgia": "America/New_York",
    "maine": "America/New_York",
    "maryland": "America/New_York",
    "massachusetts": "America/New_York",
    "new hampshire": "America/New_York",
    "new jersey": "America/New_York",
    "new york": "America/New_York",
    "north carolina": "America/New_York",
    "ohio": "America/New_York",
    "pennsylvania": "America/New_York",
    "rhode island": "America/New_York",
    "south carolina": "America/New_York",
    "vermont": "America/New_York",
    "virginia": "America/New_York",
    "west virginia": "America/New_York",
    "michigan": "America/New_York",
    "indiana": "America/New_York",
    "kentucky": "America/New_York",
    "dc": "America/New_York",
    "washington dc": "America/New_York",
    "district of columbia": "America/New_York",
    # Central
    "alabama": "America/Chicago",
    "arkansas": "America/Chicago",
    "illinois": "America/Chicago",
    "iowa": "America/Chicago",
    "kansas": "America/Chicago",
    "louisiana": "America/Chicago",
    "minnesota": "America/Chicago",
    "mississippi": "America/Chicago",
    "missouri": "America/Chicago",
    "nebraska": "America/Chicago",
    "north dakota": "America/Chicago",
    "oklahoma": "America/Chicago",
    "south dakota": "America/Chicago",
    "tennessee": "America/Chicago",
    "texas": "America/Chicago",
    "wisconsin": "America/Chicago",
    # Mountain
    "arizona": "America/Phoenix",
    "colorado": "America/Denver",
    "idaho": "America/Denver",
    "montana": "America/Denver",
    "new mexico": "America/Denver",
    "utah": "America/Denver",
    "wyoming": "America/Denver",
    # Pacific
    "california": "America/Los_Angeles",
    "nevada": "America/Los_Angeles",
    "oregon": "America/Los_Angeles",
    "washington": "America/Los_Angeles",
    # Other
    "alaska": "America/Anchorage",
    "hawaii": "Pacific/Honolulu",
}


def get_timezone_offset(tz_name: str) -> int:
    """
    Get UTC offset in minutes for a timezone.

    Args:
        tz_name: IANA timezone name (e.g., 'America/New_York')

    Returns:
        UTC offset in minutes (negative for west of UTC)
    """
    try:
        import zoneinfo

        tz = zoneinfo.ZoneInfo(tz_name)
        # Get current offset (accounts for DST)
        now = datetime.now(tz)
        offset = now.utcoffset()
        if offset:
            return int(offset.total_seconds() / 60)
        return 0
    except Exception:
        return 0


def lookup_timezone_from_location(
    country: str | None,
    state: str | None = None,
    city: str | None = None,
) -> tuple[str | None, int | None]:
    """
    Look up timezone from location data.

    Returns the most likely timezone based on country, with optional
    state-level precision for US and Australian leads.

    Args:
        country: Country name or code
        state: State/province (optional, used for US and Australia)
        city: City name (optional, for future use)

    Returns:
        Tuple of (timezone_name, utc_offset_minutes)
    """
    if not country:
        return None, None

    country_lower = country.lower().strip()

    # For US leads, try to get more precise timezone from state
    if country_lower in ("united states", "us", "usa") and state:
        state_lower = state.lower().strip()
        tz_name = US_STATE_TIMEZONE_MAP.get(state_lower)
        if tz_name:
            return tz_name, get_timezone_offset(tz_name)

    # For Australian leads, use state-level timezone (per spec)
    if country_lower in ("australia", "au", "aus"):
        if state:
            state_lower = state.lower().strip()
            tz_name = AUSTRALIAN_STATE_TIMEZONES.get(state_lower)
            if tz_name:
                return tz_name, get_timezone_offset(tz_name)
        # Default to Sydney if no state provided
        return "Australia/Sydney", get_timezone_offset("Australia/Sydney")

    # Fall back to country-level timezone
    tz_name = COUNTRY_TIMEZONE_MAP.get(country_lower)
    if tz_name:
        return tz_name, get_timezone_offset(tz_name)

    return None, None


def detect_australian_timezone(state: str | None) -> str:
    """
    Detect timezone from Australian state.

    Per EMAIL_DISTRIBUTION.md spec - state-level granularity for Australia.

    Args:
        state: State name or abbreviation

    Returns:
        IANA timezone string (defaults to Australia/Sydney)
    """
    if not state:
        return "Australia/Sydney"

    state_lower = state.lower().strip()
    return AUSTRALIAN_STATE_TIMEZONES.get(state_lower, "Australia/Sydney")


class TimezoneService:
    """
    Service for looking up and updating lead timezones.

    Used to:
    - Determine optimal send times based on lead's local time
    - Track when emails were opened relative to send time
    - Improve WHEN Detector accuracy
    """

    async def update_lead_timezone(
        self,
        db: AsyncSession,
        lead_id: UUID,
        country: str | None = None,
        state: str | None = None,
        city: str | None = None,
    ) -> tuple[str | None, int | None]:
        """
        Update a lead's timezone based on location data.

        Args:
            db: Database session
            lead_id: Lead UUID
            country: Country name or code
            state: State/province
            city: City name

        Returns:
            Tuple of (timezone_name, utc_offset_minutes)
        """
        tz_name, tz_offset = lookup_timezone_from_location(country, state, city)

        if tz_name:
            stmt = (
                update(Lead)
                .where(Lead.id == lead_id)
                .values(timezone=tz_name, timezone_offset=tz_offset)
            )
            await db.execute(stmt)
            await db.commit()

        return tz_name, tz_offset

    async def update_lead_timezone_from_enrichment(
        self,
        db: AsyncSession,
        lead: Lead,
    ) -> tuple[str | None, int | None]:
        """
        Update a lead's timezone from their enriched data.

        Extracts location from:
        1. organization_country on the lead
        2. enriched_data JSONB if available

        Args:
            db: Database session
            lead: Lead object with enrichment data

        Returns:
            Tuple of (timezone_name, utc_offset_minutes)
        """
        country = lead.organization_country
        state = None
        city = None

        # Try to extract more precise location from enriched data
        if hasattr(lead, "enriched_data") and lead.enriched_data:
            enriched = lead.enriched_data or {}
            # Try different field names used by enrichment providers
            state = enriched.get("state") or enriched.get("region") or enriched.get("province")
            city = enriched.get("city") or enriched.get("locality")
            # If country not on lead, try enriched data
            if not country:
                country = enriched.get("country")

        return await self.update_lead_timezone(
            db=db,
            lead_id=lead.id,
            country=country,
            state=state,
            city=city,
        )

    async def batch_update_timezones(
        self,
        db: AsyncSession,
        leads: list[Lead],
    ) -> dict[UUID, tuple[str | None, int | None]]:
        """
        Batch update timezones for multiple leads.

        Args:
            db: Database session
            leads: List of Lead objects

        Returns:
            Dict mapping lead_id to (timezone_name, utc_offset_minutes)
        """
        results = {}

        for lead in leads:
            if not lead.timezone:  # Only update if not already set
                tz_name, tz_offset = await self.update_lead_timezone_from_enrichment(
                    db=db,
                    lead=lead,
                )
                results[lead.id] = (tz_name, tz_offset)

        return results

    def get_lead_local_time(
        self,
        lead_timezone: str,
        utc_time: datetime | None = None,
    ) -> datetime | None:
        """
        Get the local time for a lead.

        Args:
            lead_timezone: IANA timezone name
            utc_time: UTC time to convert (defaults to now)

        Returns:
            Local datetime for the lead
        """
        if not lead_timezone:
            return None

        try:
            import zoneinfo

            tz = zoneinfo.ZoneInfo(lead_timezone)
            utc = utc_time or datetime.now(UTC)
            return utc.astimezone(tz)
        except Exception:
            return None

    def is_business_hours(
        self,
        lead_timezone: str,
        utc_time: datetime | None = None,
        start_hour: int = 9,
        end_hour: int = 17,
    ) -> bool:
        """
        Check if it's currently business hours for a lead.

        Args:
            lead_timezone: IANA timezone name
            utc_time: UTC time to check (defaults to now)
            start_hour: Start of business hours (default 9am)
            end_hour: End of business hours (default 5pm)

        Returns:
            True if within business hours
        """
        local_time = self.get_lead_local_time(lead_timezone, utc_time)
        if not local_time:
            return True  # Default to True if we can't determine

        hour = local_time.hour
        weekday = local_time.weekday()

        # Monday-Friday, 9am-5pm
        return weekday < 5 and start_hour <= hour < end_hour

    def get_optimal_email_send_time(
        self,
        lead_timezone: str,
        window_start_hour: int = 9,
        window_end_hour: int = 11,
    ) -> datetime:
        """
        Calculate optimal email send time (9-11 AM recipient local time).

        Per EMAIL_DISTRIBUTION.md spec:
        - Send window: 9-11 AM recipient local time
        - Weekdays only (Monday-Friday)
        - Random minute within window for natural distribution

        Args:
            lead_timezone: IANA timezone name (e.g., 'Australia/Sydney')
            window_start_hour: Start of send window (default 9)
            window_end_hour: End of send window (default 11)

        Returns:
            UTC datetime for optimal send time
        """
        import zoneinfo

        try:
            tz = zoneinfo.ZoneInfo(lead_timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("Australia/Sydney")

        now_local = datetime.now(tz)

        # Random minute within window (0-119 mins = 9:00-10:59)
        window_minutes = (window_end_hour - window_start_hour) * 60
        random_minute = random.randint(0, window_minutes - 1)

        target = now_local.replace(
            hour=window_start_hour + (random_minute // 60),
            minute=random_minute % 60,
            second=0,
            microsecond=0,
        )

        # If past today's window, move to tomorrow
        window_end = now_local.replace(hour=window_end_hour, minute=0, second=0, microsecond=0)
        if now_local >= window_end:
            target += timedelta(days=1)

        # Skip weekends (Saturday=5, Sunday=6)
        while target.weekday() >= 5:
            target += timedelta(days=1)

        # Return as UTC for scheduling
        return target.astimezone(UTC)

    def is_in_email_send_window(
        self,
        lead_timezone: str,
        window_start_hour: int = 9,
        window_end_hour: int = 11,
    ) -> bool:
        """
        Check if current time is within optimal email send window.

        Args:
            lead_timezone: IANA timezone name
            window_start_hour: Start of window (default 9)
            window_end_hour: End of window (default 11)

        Returns:
            True if within 9-11 AM window on a weekday
        """
        local_time = self.get_lead_local_time(lead_timezone)
        if not local_time:
            return False

        hour = local_time.hour
        weekday = local_time.weekday()

        # Monday-Friday, within window
        return weekday < 5 and window_start_hour <= hour < window_end_hour


# Standalone function for convenience (matches spec signature)
def get_optimal_send_time(
    timezone_str: str,
    window_start: int = 9,
    window_end: int = 11,
) -> datetime:
    """
    Calculate optimal send time (9-11 AM recipient local).

    Matches signature from EMAIL_DISTRIBUTION.md spec.
    Skips weekends and returns next available slot.

    Args:
        timezone_str: IANA timezone string
        window_start: Start hour (default 9)
        window_end: End hour (default 11)

    Returns:
        UTC datetime for optimal send time
    """
    service = get_timezone_service()
    return service.get_optimal_email_send_time(
        lead_timezone=timezone_str,
        window_start_hour=window_start,
        window_end_hour=window_end,
    )


# Singleton instance
_timezone_service: TimezoneService | None = None


def get_timezone_service() -> TimezoneService:
    """Get the timezone service singleton."""
    global _timezone_service
    if _timezone_service is None:
        _timezone_service = TimezoneService()
    return _timezone_service


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Country to timezone mapping
# [x] US state to timezone mapping for precision
# [x] Australian state to timezone mapping (Phase D)
# [x] get_timezone_offset() for UTC offset calculation
# [x] lookup_timezone_from_location() utility function
# [x] detect_australian_timezone() utility function (Phase D)
# [x] TimezoneService class with async methods
# [x] update_lead_timezone() for direct updates
# [x] update_lead_timezone_from_enrichment() for enriched leads
# [x] batch_update_timezones() for bulk operations
# [x] get_lead_local_time() for time conversion
# [x] is_business_hours() for send time optimization
# [x] get_optimal_email_send_time() for 9-11 AM window (Phase D)
# [x] is_in_email_send_window() for window check (Phase D)
# [x] get_optimal_send_time() standalone function (Phase D)
# [x] Singleton pattern for service access
# [x] Session passed as argument (Rule 11)
