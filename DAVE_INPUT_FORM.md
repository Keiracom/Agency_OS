# Dave Input Form — One-Time Setup

**Purpose:** Everything Elliot needs to run fully autonomous.
**After this:** I don't ask you for anything unless it legally requires your signature.

---

## Section 1: Payment (REQUIRED)

```
CARD_NUMBER: 
CARD_EXPIRY: (MM/YY)
CARD_CVV: 
CARD_NAME: 
BILLING_ADDRESS: 
BILLING_POSTCODE: 
BILLING_COUNTRY: Australia

MONTHLY_SPENDING_CAP_AUD: $______ (recommend $2000)
ALERT_ME_AT_PERCENT: 50%
```

---

## Section 2: Identity (For services requiring KYC)

```
FULL_LEGAL_NAME: 
DATE_OF_BIRTH: 
DRIVERS_LICENSE_NUMBER: 
DRIVERS_LICENSE_STATE: 

(Or send photo of ID via Telegram - I'll use for Onfido verification then delete)
```

---

## Section 3: Business Details

```
KEIRACOM_ABN: 
BUSINESS_NAME: Keiracom Pty Ltd (or correct name)
BUSINESS_ADDRESS: 
BUSINESS_EMAIL: (for contracts/invoices)
BUSINESS_PHONE: (for emergencies only)
```

---

## Section 4: Existing Credentials I Should Know About

```
STRIPE_ACCOUNT_EXISTS: Yes/No
TELNYX_ACCOUNT_EXISTS: Yes (API key in .env)
MIDJOURNEY_ACCOUNT: Yes/No (Discord?)
```

---

## Section 5: Permissions

```
[x] I authorize Elliot to sign up for services using my payment method
[x] I authorize Elliot to spend up to the monthly cap without asking
[x] I authorize Elliot to deploy to production (with rollback capability)
[x] I authorize Elliot to send outreach on behalf of Agency OS
[x] I want to be notified only when: (check all that apply)
    [ ] Contract needs signature
    [ ] Spending hits alert threshold
    [ ] Critical system failure
    [ ] Weekly summary
    [ ] Daily summary
```

---

## How to Submit

1. Fill this out
2. Send to me via Telegram (I'll delete after processing)
3. Or save to a secure location and give me path

---

## After You Submit

I will:
1. Store credentials securely in .env
2. Complete all account setups
3. Start mission chain
4. Only contact you per your notification preferences

**You go live your life. I build Agency OS.**
