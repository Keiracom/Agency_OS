# LinkedIn Distribution Architecture

**Status:** 🟡 PARTIALLY IMPLEMENTED
**Provider:** Unipile (internal — not visible to clients)
**Seat Ownership:** Client-owned LinkedIn accounts
**Rate Limit:** 20 connections/day/seat (conservative)
**Last Updated:** January 22, 2026

---

## Executive Summary

LinkedIn is Step 3 in the default sequence (Day 5 - connection request). Clients connect their existing LinkedIn accounts via Agency OS dashboard (white-label, no third-party branding visible). Uses humanized timing to avoid account flags.

---

## CTO Decisions (2026-01-20)

| Decision | Choice |
|----------|--------|
| Seat allocation | **Ignition: 4, Velocity: 7, Dominance: 14** |
| Tier access | **Hot + Warm + Cool** (ALS ≥ 35) |
| Connection note | **No note by default** |
| Note exception | **Include note if ≥2 mutual connections** |
| Post-accept follow-up | **3-5 days** (random) |
| Ignored threshold | **14 days pending → mark ignored** |
| Weekend activity | **Saturday 50%, Sunday off** |
| Profile view first | **Yes**, 10-30 min before connecting |
| Mutual priority | **Sort queue by mutual connection count** |
| Seat warmup | **2-week ramp** (5→10→15→20/day) |
| Health monitoring | **Reduce 25% if accept rate <30%** |
| Restriction recovery | **Pause seat, alert admin, manual re-auth** |
| InMail | **Do NOT use** — connection + message is better |
| Client experience | **White-label** — no third-party branding visible |

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Unipile integration | ✅ | `src/integrations/unipile.py` |
| LinkedIn engine | ✅ | `src/engines/linkedin.py` |
| Timing engine | ✅ | `src/engines/timing.py` |
| Multi-seat model | ✅ | `src/models/linkedin_seat.py` |
| Connection tracking | ✅ | `src/models/linkedin_connection.py` |
| Connection service | ✅ | `src/services/linkedin_connection_service.py` |
| Warmup service | ✅ | `src/services/linkedin_warmup_service.py` |
| Health service | ✅ | `src/services/linkedin_health_service.py` |
| Daily health flow | ✅ | `src/orchestration/flows/linkedin_health_flow.py` (6 AM AEST) |
| Migrations | ✅ | `042_client_personas.sql`, `043_linkedin_seats.sql` |
| White-label auth flow | 🟡 | API exists, frontend integration pending |

---

## Seat Allocation (Aligned with RESOURCE_POOL.md)

| Tier | LinkedIn Seats | Daily Capacity | Monthly Capacity |
|------|----------------|----------------|------------------|
| Ignition | 4 | 80 | 1,760 |
| Velocity | 7 | 140 | 3,080 |
| Dominance | 14 | 280 | 6,160 |

*Monthly = seats × 20/day × 22 business days*

### Capacity vs Demand

| Tier | Leads (Cool+) | LinkedIn Touches | Capacity | Status |
|------|---------------|------------------|----------|--------|
| Ignition | 937 (75%) | ~1,030 | 1,760 | ✅ 70% buffer |
| Velocity | 1,687 (75%) | ~1,855 | 3,080 | ✅ 66% buffer |
| Dominance | 3,375 (75%) | ~3,712 | 6,160 | ✅ 66% buffer |

---

## Account Connection (White-Label)

### Principle

**Client never sees third-party branding.** The entire connection flow happens within Agency OS dashboard.

### Connection Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AGENCY OS DASHBOARD                             │
│                                                                      │
│   Settings → LinkedIn Accounts                                       │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  Seat 1: ✅ Connected (john.smith@sparro.com)               │   │
│   │  Seat 2: ✅ Connected (jane.doe@sparro.com)                 │   │
│   │  Seat 3: 🔄 Awaiting verification                           │   │
│   │  Seat 4: ⬜ [Connect Account]                                │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Step 1: Client Enters Credentials (Agency OS UI)

```
┌─────────────────────────────────────────────────────────────────────┐
│           Connect Your LinkedIn Account                              │
│                                                                      │
│   LinkedIn Email: [_________________________]                        │
│   LinkedIn Password: [_________________________]                     │
│                                                                      │
│   🔒 Your credentials are encrypted and used only to establish      │
│      a secure connection. We do not store your password.            │
│                                                                      │
│                    [Connect LinkedIn]                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Step 2: If 2FA Required (Agency OS UI)

```
┌─────────────────────────────────────────────────────────────────────┐
│           Verify Your Identity                                       │
│                                                                      │
│   LinkedIn sent a verification code to your email/phone.            │
│                                                                      │
│   Verification Code: [______]                                        │
│                                                                      │
│                      [Verify]                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Backend Flow

```python
# src/services/linkedin_seat_service.py

class LinkedInSeatService:

    async def connect_account(
        self,
        db: AsyncSession,
        seat_id: UUID,
        linkedin_email: str,
        linkedin_password: str,
    ) -> dict:
        """
        Connect LinkedIn account via direct API.

        SECURITY: Credentials are passed through to provider API.
        We NEVER store email or password.
        """
        seat = await self.get_seat(db, seat_id)

        # Pass directly to provider - credentials not stored
        result = await unipile.connect_account(
            provider="LINKEDIN",
            credentials={
                "username": linkedin_email,
                "password": linkedin_password,
            },
        )

        if result.get("status") == "2fa_required":
            seat.status = "awaiting_2fa"
            seat.pending_connection_id = result.get("connection_id")
            await db.commit()

            return {
                "status": "2fa_required",
                "method": result.get("2fa_method"),
                "message": "Enter the verification code sent to your device",
            }

        if result.get("status") == "connected":
            await self._mark_seat_connected(db, seat, result)
            return {"status": "connected"}

        return {"status": "failed", "error": result.get("error")}

    async def submit_2fa_code(
        self,
        db: AsyncSession,
        seat_id: UUID,
        code: str,
    ) -> dict:
        """Submit 2FA verification code."""
        seat = await self.get_seat(db, seat_id)

        result = await unipile.verify_2fa(
            connection_id=seat.pending_connection_id,
            code=code,
        )

        if result.get("status") == "connected":
            await self._mark_seat_connected(db, seat, result)
            return {"status": "connected"}

        return {"status": "failed", "error": result.get("error")}

    async def _mark_seat_connected(
        self,
        db: AsyncSession,
        seat: LinkedInSeat,
        result: dict,
    ):
        """Mark seat as connected and start warmup."""
        seat.unipile_account_id = result.get("account_id")
        seat.account_email = result.get("email")
        seat.account_name = result.get("name")
        seat.profile_url = result.get("profile_url")
        seat.status = "warmup"
        seat.activated_at = datetime.utcnow()
        seat.pending_connection_id = None
        await db.commit()
```

### Security

| Concern | Mitigation |
|---------|------------|
| Credentials in transit | HTTPS only, TLS 1.3 |
| Credentials in memory | Pass-through only, never stored, garbage collected |
| Credentials in logs | Explicitly excluded from all logging |
| API endpoint security | Authenticated, rate-limited, client-scoped |

```python
# CRITICAL: Never log credentials
logger.info(f"LinkedIn connection attempt for seat {seat_id}")
# DO NOT: logger.info(f"Email: {email}, Password: {password}")
```

---

## Concurrent Usage (Client Using Their Account)

### Reality

Clients will continue using their LinkedIn accounts normally while we automate. Both sessions coexist.

### Shared Rate Limits

LinkedIn's daily limits apply to the ACCOUNT, not per-session:

| Scenario | Our Quota |
|----------|-----------|
| Client sends 0 manual connections | 20 available |
| Client sends 5 manual connections | 15 available |
| Client sends 15 manual connections | 5 available |

### Quota Tracking

```python
async def get_available_quota(seat: LinkedInSeat) -> int:
    """
    Check remaining quota after client's manual activity.
    """
    # Provider tracks all activity on the account
    today_activity = await unipile.get_account_activity(
        account_id=seat.unipile_account_id,
        since=today_start(),
    )

    total_connections_today = len([
        a for a in today_activity
        if a['type'] == 'invitation_sent'
    ])

    return max(0, 20 - total_connections_today)
```

### Client Guidance

Dashboard shows:
> "Today: 5 connections sent (3 automated, 2 manual). 15 remaining."

Onboarding guidance:
> "For best results, limit manual connection requests during business hours (8 AM - 6 PM). Your automation runs during these times."

---

## Database Schema

### Table: `linkedin_seats`

```sql
CREATE TABLE linkedin_seats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    resource_pool_id UUID REFERENCES resource_pool(id),

    -- Provider connection (internal, not exposed to client)
    unipile_account_id VARCHAR(255),

    -- Account info (from provider, displayed to client)
    account_email VARCHAR(255),
    account_name VARCHAR(255),
    profile_url TEXT,

    -- Persona mapping
    persona_id UUID REFERENCES client_personas(id),

    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    -- pending: awaiting client connection
    -- awaiting_2fa: 2FA code needed
    -- warmup: in 2-week ramp
    -- active: full capacity
    -- restricted: LinkedIn flagged
    -- disconnected: client removed

    -- Connection flow
    pending_connection_id VARCHAR(255),

    -- Warmup tracking
    activated_at TIMESTAMPTZ,
    warmup_completed_at TIMESTAMPTZ,

    -- Capacity override
    daily_limit_override INTEGER,

    -- Health metrics
    accept_rate_7d DECIMAL(5,4),
    accept_rate_30d DECIMAL(5,4),
    pending_count INTEGER DEFAULT 0,

    -- Restriction tracking
    restricted_at TIMESTAMPTZ,
    restricted_reason TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_linkedin_seats_client ON linkedin_seats(client_id);
CREATE INDEX idx_linkedin_seats_active ON linkedin_seats(client_id)
    WHERE status IN ('warmup', 'active');
CREATE INDEX idx_linkedin_seats_persona ON linkedin_seats(persona_id);
```

### Table: `linkedin_connections`

```sql
CREATE TABLE linkedin_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES lead_pool(id) ON DELETE CASCADE,
    seat_id UUID NOT NULL REFERENCES linkedin_seats(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id),

    -- Request tracking
    unipile_request_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    -- pending: request sent, awaiting response
    -- accepted: connection accepted
    -- ignored: 14 days no response
    -- declined: explicitly declined
    -- withdrawn: we withdrew stale request

    -- Note tracking
    note_included BOOLEAN DEFAULT FALSE,
    note_content TEXT,

    -- Timestamps
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    profile_viewed_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,

    -- Follow-up tracking
    follow_up_scheduled_for TIMESTAMPTZ,
    follow_up_sent_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_lead_seat UNIQUE (lead_id, seat_id)
);

CREATE INDEX idx_linkedin_conn_lead ON linkedin_connections(lead_id);
CREATE INDEX idx_linkedin_conn_seat ON linkedin_connections(seat_id);
CREATE INDEX idx_linkedin_conn_status ON linkedin_connections(status);
CREATE INDEX idx_linkedin_conn_pending ON linkedin_connections(seat_id, requested_at)
    WHERE status = 'pending';
```

---

## Seat Warmup Schedule

New seats ramp over 2 weeks:

| Days Active | Daily Limit |
|-------------|-------------|
| 1-3 | 5 |
| 4-7 | 10 |
| 8-11 | 15 |
| 12+ | 20 |

```python
LINKEDIN_WARMUP_SCHEDULE = [
    (1, 3, 5),
    (4, 7, 10),
    (8, 11, 15),
    (12, 999, 20),
]

def get_seat_daily_limit(seat: LinkedInSeat) -> int:
    """Get daily limit based on warmup status and health."""
    if seat.daily_limit_override:
        return seat.daily_limit_override

    if seat.status == 'restricted':
        return 0

    if not seat.activated_at:
        return 0

    days_active = (datetime.utcnow() - seat.activated_at).days + 1

    for start, end, limit in LINKEDIN_WARMUP_SCHEDULE:
        if start <= days_active <= end:
            return limit

    return 20
```

---

## Persona-to-Seat Mapping

Each LinkedIn seat IS a persona's identity. The seat's profile becomes the sender.

| Tier | Seats | Persona Strategy |
|------|-------|------------------|
| Ignition (4) | 4 | 2 personas × 2 seats each |
| Velocity (7) | 7 | 3 personas × 2 seats + 1 overflow |
| Dominance (14) | 14 | 4 personas × 3 seats + 2 overflow |

When lead is assigned a persona at campaign start, all LinkedIn touches use seats mapped to that persona.

---

## Connection Request Flow

### Step 1: Pre-Flight Checks

```python
async def can_send_connection(
    db: AsyncSession,
    lead: Lead,
    seat: LinkedInSeat,
) -> tuple[bool, str | None]:
    """Check if we can send connection request."""

    if not lead.linkedin_url:
        return False, "no_linkedin_url"

    existing = await get_linkedin_connection(db, lead.id, seat.id)
    if existing:
        return False, f"existing_{existing.status}"

    daily_count = await get_seat_daily_count(db, seat.id)
    available = await get_available_quota(seat)
    if daily_count >= available:
        return False, "daily_limit"

    weekly_count = await get_seat_weekly_count(db, seat.id)
    if weekly_count >= 80:
        return False, "weekly_limit"

    if seat.status == 'restricted':
        return False, "seat_restricted"

    return True, None
```

### Step 2: Profile View (Humanization)

```python
async def view_profile_before_connect(
    seat: LinkedInSeat,
    lead: Lead,
) -> datetime:
    """View profile 10-30 min before sending connection."""
    await unipile.get_profile(
        account_id=seat.unipile_account_id,
        profile_id=lead.linkedin_url,
    )

    delay_minutes = random.randint(10, 30)
    connect_at = datetime.utcnow() + timedelta(minutes=delay_minutes)

    return connect_at
```

### Step 3: Connection Note Decision

```python
async def should_include_note(
    seat: LinkedInSeat,
    lead: Lead,
) -> tuple[bool, str | None]:
    """Include note only if ≥2 mutual connections."""
    profile = await unipile.get_profile(
        account_id=seat.unipile_account_id,
        profile_id=lead.linkedin_url,
    )

    mutual_count = profile.get("mutual_connections", 0)

    if mutual_count >= 2:
        note = f"Hi {lead.first_name}, noticed we share some connections. Would love to connect."
        return True, note

    return False, None
```

### Step 4: Send Request

```python
async def send_connection_request(
    db: AsyncSession,
    lead: Lead,
    seat: LinkedInSeat,
    campaign_id: UUID,
) -> EngineResult:
    """Send LinkedIn connection request."""
    include_note, note_content = await should_include_note(seat, lead)

    result = await unipile.send_invitation(
        account_id=seat.unipile_account_id,
        recipient_id=lead.linkedin_url,
        message=note_content,
    )

    connection = LinkedInConnection(
        lead_id=lead.id,
        seat_id=seat.id,
        campaign_id=campaign_id,
        unipile_request_id=result.get("invitation_id"),
        status="pending",
        note_included=include_note,
        note_content=note_content,
        requested_at=datetime.utcnow(),
    )
    db.add(connection)

    await log_activity(
        lead_id=lead.id,
        channel="linkedin",
        action="connection_sent",
        metadata={"seat_id": str(seat.id), "with_note": include_note},
    )

    await db.commit()

    return EngineResult.ok(data={"connection_id": str(connection.id)})
```

---

## Post-Connection Handling

### When Accepted

```python
async def handle_connection_accepted(
    db: AsyncSession,
    seat_id: UUID,
    recipient_profile_url: str,
):
    """Handle webhook when connection is accepted."""
    connection = await get_connection_by_profile(db, seat_id, recipient_profile_url)
    if not connection:
        return

    connection.status = "accepted"
    connection.responded_at = datetime.utcnow()

    lead = await get_lead(db, connection.lead_id)
    lead.linkedin_connected = True
    lead.linkedin_connected_at = datetime.utcnow()

    # Schedule follow-up (3-5 days)
    delay_days = random.randint(3, 5)
    connection.follow_up_scheduled_for = datetime.utcnow() + timedelta(days=delay_days)

    await db.commit()
```

### 14-Day Ignored Timeout

```python
async def mark_stale_connections_ignored(db: AsyncSession):
    """Daily job: Mark connections pending >14 days as ignored."""
    cutoff = datetime.utcnow() - timedelta(days=14)

    await db.execute(
        update(LinkedInConnection)
        .where(LinkedInConnection.status == "pending")
        .where(LinkedInConnection.requested_at < cutoff)
        .values(status="ignored", responded_at=datetime.utcnow())
    )
```

### 30-Day Stale Withdrawal

```python
async def withdraw_stale_requests(db: AsyncSession):
    """Weekly job: Withdraw requests pending >30 days."""
    cutoff = datetime.utcnow() - timedelta(days=30)

    stale = await db.execute(
        select(LinkedInConnection)
        .join(LinkedInSeat)
        .where(LinkedInConnection.status == "pending")
        .where(LinkedInConnection.requested_at < cutoff)
    )

    for conn in stale.scalars():
        try:
            await unipile.withdraw_invitation(
                account_id=conn.seat.unipile_account_id,
                invitation_id=conn.unipile_request_id,
            )
            conn.status = "withdrawn"
        except Exception as e:
            logger.warning(f"Failed to withdraw {conn.id}: {e}")

    await db.commit()
```

---

## Follow-Up Message Generation

```python
LINKEDIN_FOLLOWUP_PROMPT = """
Write a LinkedIn message (max 500 chars) for a new connection:

Lead: {first_name} {last_name}
Title: {title}
Company: {company_name}
Days since connected: {days_connected}
Email sent on Day 1: Yes
Voice call on Day 3: {voice_outcome}

Goal: Start conversation about their challenges
Tone: Casual, peer-to-peer
Reference: The email you sent earlier

Do NOT: Pitch directly, ask for meeting in first message
"""
```

---

## Reply Handling (Unified with reply_agent)

```python
async def handle_linkedin_message_received(
    db: AsyncSession,
    account_id: str,
    sender_profile_url: str,
    message_text: str,
    chat_id: str,
):
    """Route inbound LinkedIn message to unified reply_agent."""
    seat = await get_seat_by_unipile_account(db, account_id)
    lead = await get_lead_by_linkedin_url(db, sender_profile_url)

    if not seat or not lead:
        return

    await log_activity(
        lead_id=lead.id,
        channel="linkedin",
        action="reply_received",
        metadata={"seat_id": str(seat.id), "chat_id": chat_id},
    )

    await reply_agent.process_reply(
        lead_id=lead.id,
        channel="linkedin",
        content=message_text,
        metadata={"seat_id": str(seat.id), "chat_id": chat_id},
    )
```

---

## Health Monitoring

### Daily Health Check

```python
async def update_seat_health_metrics(db: AsyncSession):
    """Daily job: Calculate accept rates and apply limits."""
    seats = await get_all_active_seats(db)

    for seat in seats:
        stats_7d = await get_connection_stats(db, seat.id, days=7)
        if stats_7d["total"] > 0:
            seat.accept_rate_7d = stats_7d["accepted"] / stats_7d["total"]

        stats_30d = await get_connection_stats(db, seat.id, days=30)
        if stats_30d["total"] > 0:
            seat.accept_rate_30d = stats_30d["accepted"] / stats_30d["total"]

        seat.pending_count = await get_pending_count(db, seat.id)

        # Health-based limit adjustment
        if seat.accept_rate_7d and seat.accept_rate_7d < 0.20:
            seat.daily_limit_override = 10  # 50% reduction
            await alert_admin(f"Seat {seat.id} critical: {seat.accept_rate_7d:.0%}")
        elif seat.accept_rate_7d and seat.accept_rate_7d < 0.30:
            seat.daily_limit_override = 15  # 25% reduction
        else:
            seat.daily_limit_override = None

    await db.commit()
```

### Health Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Accept rate (7d) | <30% | <20% | Reduce limit 25% / 50% |
| Pending count | >50 | >80 | Alert admin |
| Restricted | — | Yes | Pause seat, alert |

### Restriction Detection

```python
async def handle_seat_restricted(
    db: AsyncSession,
    unipile_account_id: str,
    reason: str,
):
    """Handle provider restriction webhook."""
    seat = await get_seat_by_unipile_account(db, unipile_account_id)
    if not seat:
        return

    seat.status = "restricted"
    seat.restricted_at = datetime.utcnow()
    seat.restricted_reason = reason
    seat.daily_limit_override = 0

    await db.commit()

    await alert_admin(
        subject="LinkedIn Seat Restricted",
        body=f"Seat: {seat.account_name}\nClient: {seat.client_id}\nReason: {reason}",
    )
```

---

## Webhook Events

| Provider Event | Handler | Action |
|----------------|---------|--------|
| `account.created` | `handle_seat_connected` | Mark connected, start warmup |
| `account.credentials` | `handle_seat_reauth_needed` | Alert admin, pause seat |
| `account.deleted` | `handle_seat_disconnected` | Mark disconnected |
| `invitation.accepted` | `handle_connection_accepted` | Schedule follow-up |
| `invitation.declined` | `handle_connection_declined` | Mark declined |
| `message.received` | `handle_linkedin_message_received` | Route to reply_agent |

---

## Timing Engine Integration

Uses existing `src/engines/timing.py`:

- Beta distribution delays (8-45 min between actions)
- Business hours (8 AM - 6 PM recipient timezone)
- Start time jitter (0-120 min after day start)
- Max 8 actions/hour (burst prevention)

### Weekend Behavior

| Day | Limit |
|-----|-------|
| Mon-Fri | Full (20/seat) |
| Saturday | 50% (10/seat) |
| Sunday | 0 (off) |

---

## Queue Priority

1. **ALS Score** (Hot first)
2. **Mutual connections** (more = higher)
3. **Days waiting** (older leads bumped up)

```python
async def get_daily_linkedin_queue(
    db: AsyncSession,
    client_id: UUID,
) -> list[Lead]:
    """Get prioritized queue for LinkedIn today."""
    return await db.execute(
        select(Lead)
        .where(Lead.client_id == client_id)
        .where(Lead.linkedin_url.isnot(None))
        .where(Lead.linkedin_connected == False)
        .where(Lead.als_score >= 35)
        .where(~exists(
            select(LinkedInConnection.id)
            .where(LinkedInConnection.lead_id == Lead.id)
        ))
        .order_by(
            Lead.als_score.desc(),
            Lead.mutual_connection_count.desc().nullslast(),
            Lead.created_at.asc(),
        )
    )
```

---

## Configuration

### Environment Variables

```bash
UNIPILE_API_KEY=xxx
UNIPILE_API_URL=https://api.unipile.com
UNIPILE_WEBHOOK_SECRET=xxx
```

### Settings

```python
# src/config/settings.py

linkedin_max_connections_day: int = 20
linkedin_max_connections_week: int = 80
linkedin_warmup_days: int = 14
linkedin_connection_timeout_days: int = 14
linkedin_stale_request_days: int = 30
linkedin_min_delay_minutes: int = 8
linkedin_max_delay_minutes: int = 45
linkedin_business_hours_start: int = 8
linkedin_business_hours_end: int = 18
linkedin_weekend_saturday_limit: int = 10
linkedin_accept_rate_warning: float = 0.30
linkedin_accept_rate_critical: float = 0.20
```

---

## Cost Structure

| Item | Cost | Notes |
|------|------|-------|
| Provider API | ~$99/month base | Platform cost, included in tier pricing |
| Client LinkedIn accounts | $0 | Client provides their own |
| Premium LinkedIn (optional) | ~$60/month/seat | Only if client wants InMail |

**InMail Strategy:** Do NOT use. Connection request + message is free, more personal, and has higher response rates.

---

## Files Involved

| File | Purpose | Status |
|------|---------|--------|
| `src/integrations/unipile.py` | Unipile API client | ✅ |
| `src/engines/linkedin.py` | LinkedIn engine | ✅ |
| `src/engines/timing.py` | Humanized delays | ✅ |
| `src/models/linkedin_seat.py` | Seat model (warmup schedule, daily_limit) | ✅ |
| `src/models/linkedin_connection.py` | Connection tracking model | ✅ |
| `src/services/linkedin_connection_service.py` | Connection service | ✅ |
| `src/services/linkedin_warmup_service.py` | Warmup status transitions | ✅ |
| `src/services/linkedin_health_service.py` | Health metrics & limit reductions | ✅ |
| `src/orchestration/flows/linkedin_health_flow.py` | Daily health check (6 AM AEST) | ✅ |
| `src/api/routes/linkedin.py` | LinkedIn routes | ✅ |
| `supabase/migrations/043_linkedin_seats.sql` | Seats schema | ✅ |

---

## Verification Checklist

- [x] `linkedin_seats` table created
- [x] `linkedin_connections` table created
- [ ] White-label connection flow works
- [ ] 2FA handling in Agency OS UI
- [x] Multi-seat support per client
- [x] Seat warmup enforced (5→10→15→20) — `linkedin_warmup_service.py`
- [ ] Persona-to-seat mapping works
- [ ] Profile view before connect
- [ ] Connection note logic (mutual-based)
- [ ] Pre-flight checks (limits, existing)
- [ ] Quota tracking (including manual activity)
- [ ] Accept → follow-up scheduling
- [x] 14-day ignored timeout — `linkedin_health_service.mark_stale_connections_ignored()`
- [ ] 30-day stale withdrawal
- [ ] Reply routing to reply_agent
- [x] Health monitoring active — `linkedin_health_service.py` + `linkedin_health_flow.py`
- [x] Restriction detection works — `linkedin_health_service.detect_restrictions()`
- [ ] Weekend reduction applied
- [ ] Queue priority correct
- [x] RESOURCE_POOL.md updated (Ignition: 4)
