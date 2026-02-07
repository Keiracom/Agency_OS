# Sales Infrastructure Setup

Created: 2026-02-07 | Stream F - Autonomous Run

## Overview

Sales infrastructure for Agency OS covering:
1. **Sales Pipeline** - Lead stage tracking from prospect to close
2. **Demo Bookings** - Cal.com/Calendly integration
3. **Stripe Billing** - Subscriptions and founding member plans
4. **Founding Members** - 20-spot tracking with benefits

---

## 1. Sales Pipeline

### Database Schema
**Migration:** `migrations/003_sales_pipeline.sql`

**Tables:**
- `sales_pipeline` - Main pipeline tracking
- `sales_pipeline_history` - Stage change audit log

**Stages (in order):**
```
prospect → contacted → demo_booked → demo_done → proposal_sent → negotiation → closed_won/closed_lost
```

**Key Fields:**
| Field | Type | Description |
|-------|------|-------------|
| lead_id | UUID | Foreign key to leads table |
| stage | enum | Current pipeline stage |
| next_action | text | Next step description |
| next_action_date | timestamp | When to take action |
| assigned_to | text | Sales rep email/ID |
| deal_value_aud | decimal | Expected value in AUD |
| probability | int | Win probability (0-100) |

**Views:**
- `sales_pipeline_summary` - Aggregate stats by stage

---

## 2. Demo Booking Integration

### Files
- **Integration:** `src/integrations/calendar_booking.py`
- **Migration:** `migrations/005_demo_bookings.sql`

### Recommended Provider: Cal.com
- Open source, self-hostable
- Better webhook support
- Native Stripe integration

### Setup Steps
1. Create Cal.com account (or self-host)
2. Create "Agency OS Demo" event type (30 min)
3. Generate API key and webhook secret
4. Set environment variables:
```bash
CAL_API_KEY=cal_live_xxx
CAL_WEBHOOK_SECRET=whsec_xxx
```

### Webhook Endpoints
```
POST /bookings/webhook/cal      # Cal.com webhooks
POST /bookings/webhook/calendly # Calendly (backup)
```

### Pipeline Integration
| Booking Event | Pipeline Action |
|--------------|-----------------|
| created | stage → demo_booked |
| cancelled | stage → contacted |
| rescheduled | Update next_action_date |

### Embedding on Landing Page
```html
<button data-cal-link="keiracom/demo">Book a Demo</button>
```

---

## 3. Stripe Billing

### Files
- **Integration:** `src/integrations/stripe_billing.py`
- **Migration:** `migrations/004_founding_members.sql`

### Environment Variables
```bash
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_FOUNDING_PRICE_ID=price_xxx  # 40% discount price
STRIPE_STANDARD_PRICE_ID=price_xxx  # Regular price
```

### API Endpoints
```
POST /billing/create-checkout   # Create Checkout session
POST /billing/customer-portal   # Self-service billing portal
GET  /billing/founding-spots    # Get remaining spots (for landing page)
POST /billing/webhook           # Stripe webhooks
```

### Webhook Events Handled
- `checkout.session.completed` - Update pipeline to closed_won
- `customer.subscription.updated` - Track status changes
- `invoice.paid` - Payment confirmation
- `invoice.payment_failed` - Payment failure alerts

### Checkout Flow
```python
# Create checkout for founding member
result = await create_checkout_session(
    email="founder@example.com",
    plan_type=PlanType.FOUNDING,
    success_url="https://app.keiracom.com/welcome",
    cancel_url="https://keiracom.com/pricing"
)
# Returns: {"checkout_url": "https://checkout.stripe.com/..."}
```

---

## 4. Founding Members

### Database Schema
**Migration:** `migrations/004_founding_members.sql`

**Tables:**
- `founding_members` - 20 founding spots
- `founding_waitlist` - Overflow waitlist

**Benefits (locked at signup):**
```json
{
  "lifetime_discount_percent": 40,
  "priority_support": true,
  "early_feature_access": true,
  "founding_badge": true,
  "locked_price": true
}
```

### Helper Functions (SQL)
```sql
-- Get next available spot number (1-20)
SELECT get_next_founding_spot();

-- Get remaining spots count
SELECT get_remaining_founding_spots();
```

### API Usage
```python
# Check spots for landing page
spots = await get_remaining_founding_spots()
# Returns: 17 (3 taken, 17 remaining)

# Reserve a spot
spot_num = await reserve_founding_spot(
    email="early@customer.com",
    company_name="Acme Corp"
)
# Returns: 4 (spot number) or None (full → added to waitlist)
```

### Landing Page Display
```html
<!-- Fetch from /billing/founding-spots -->
<div class="founding-banner">
  <span class="spots-remaining">{{ spots_remaining }}</span> of 20 founding spots left
  <span class="discount">40% lifetime discount</span>
</div>
```

---

## Migration Order

Run in sequence:
```bash
# 1. Sales pipeline (depends on leads table)
psql -f migrations/003_sales_pipeline.sql

# 2. Founding members (depends on leads table)
psql -f migrations/004_founding_members.sql

# 3. Demo bookings (depends on leads + sales_pipeline)
psql -f migrations/005_demo_bookings.sql
```

---

## FastAPI Integration

Add routers to main.py:
```python
from src.integrations import stripe_billing_router, calendar_booking_router

app.include_router(stripe_billing_router)
app.include_router(calendar_booking_router)
```

---

## Next Steps

1. [ ] Create Stripe products/prices (founding + standard)
2. [ ] Set up Cal.com account and event type
3. [ ] Configure webhooks in Stripe dashboard
4. [ ] Run database migrations
5. [ ] Add founding spots widget to landing page
6. [ ] Test end-to-end booking → pipeline → checkout flow
