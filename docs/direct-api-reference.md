# Direct API Reference

Quick reference for services without MCP/SDK configured. Use these patterns for direct HTTP requests.

---

## HubSpot

**Base URL:** `https://api.hubapi.com`

**Auth:** Header `Authorization: Bearer {ACCESS_TOKEN}`

OAuth 2.0 access tokens (recommended) or static auth tokens for single-account apps. Tokens expire after ~6 hours; use refresh tokens for long-lived access.

**Common Operations:**

1. **Create Contact** - `POST /crm/v3/objects/contacts`
   - Creates a new contact with specified properties (email, firstname, lastname, etc.)
   ```bash
   curl -X POST "https://api.hubapi.com/crm/v3/objects/contacts" \
     -H "Authorization: Bearer {TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{"properties": {"email": "user@example.com", "firstname": "John"}}'
   ```

2. **Get Deals** - `GET /crm/v3/objects/deals`
   - Retrieves deals with optional filters, pagination, and property selection
   ```bash
   curl "https://api.hubapi.com/crm/v3/objects/deals?limit=10" \
     -H "Authorization: Bearer {TOKEN}"
   ```

3. **Update Contact** - `PATCH /crm/v3/objects/contacts/{contactId}`
   - Updates contact properties by ID
   ```bash
   curl -X PATCH "https://api.hubapi.com/crm/v3/objects/contacts/123" \
     -H "Authorization: Bearer {TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{"properties": {"phone": "555-1234"}}'
   ```

---

## GoHighLevel (HighLevel)

**Base URL:** `https://services.leadconnectorhq.com`

**Auth:** Header `Authorization: Bearer {ACCESS_TOKEN}`

OAuth 2.0 tokens for marketplace/private apps. Private integration tokens available for single-location use.

**Common Operations:**

1. **Create Contact** - `POST /contacts/`
   - Creates a new contact in a location
   ```bash
   curl -X POST "https://services.leadconnectorhq.com/contacts/" \
     -H "Authorization: Bearer {TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{"locationId": "xxx", "email": "user@example.com", "name": "John Doe"}'
   ```

2. **Get Opportunities** - `GET /opportunities/`
   - Retrieves sales pipeline opportunities with filters
   ```bash
   curl "https://services.leadconnectorhq.com/opportunities/?locationId=xxx" \
     -H "Authorization: Bearer {TOKEN}"
   ```

3. **Send SMS** - `POST /conversations/messages`
   - Sends an SMS message to a contact
   ```bash
   curl -X POST "https://services.leadconnectorhq.com/conversations/messages" \
     -H "Authorization: Bearer {TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{"type": "SMS", "contactId": "xxx", "message": "Hello!"}'
   ```

---

## Stripe

**Base URL:** `https://api.stripe.com/v1`

**Auth:** HTTP Basic with secret key as username (leave password empty)

Alternative: Header `Authorization: Bearer {sk_live_xxx}` or `Authorization: Bearer {sk_test_xxx}`

**Common Operations:**

1. **Create Customer** - `POST /v1/customers`
   - Creates a new Stripe customer
   ```bash
   curl -X POST "https://api.stripe.com/v1/customers" \
     -u sk_test_xxx: \
     -d email="customer@example.com" \
     -d name="Jane Doe"
   ```

2. **Create Subscription** - `POST /v1/subscriptions`
   - Creates a subscription for a customer
   ```bash
   curl -X POST "https://api.stripe.com/v1/subscriptions" \
     -u sk_test_xxx: \
     -d customer="cus_xxx" \
     -d "items[0][price]"="price_xxx"
   ```

3. **Get Invoices** - `GET /v1/invoices`
   - Lists invoices with optional customer filter
   ```bash
   curl "https://api.stripe.com/v1/invoices?customer=cus_xxx&limit=10" \
     -u sk_test_xxx:
   ```

---

## Twilio

**Base URL:** `https://api.twilio.com/2010-04-01`

**Auth:** HTTP Basic authentication

- Username: Account SID (or API Key SID)
- Password: Auth Token (or API Key Secret)

**Common Operations:**

1. **Send SMS** - `POST /Accounts/{AccountSid}/Messages.json`
   - Sends an SMS or MMS message
   ```bash
   curl -X POST "https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages.json" \
     -u {ACCOUNT_SID}:{AUTH_TOKEN} \
     -d "From=+15551234567" \
     -d "To=+15559876543" \
     -d "Body=Hello from Twilio!"
   ```

2. **Make Call** - `POST /Accounts/{AccountSid}/Calls.json`
   - Initiates an outbound phone call
   ```bash
   curl -X POST "https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Calls.json" \
     -u {ACCOUNT_SID}:{AUTH_TOKEN} \
     -d "From=+15551234567" \
     -d "To=+15559876543" \
     -d "Url=http://example.com/twiml"
   ```

3. **Get Message Status** - `GET /Accounts/{AccountSid}/Messages/{MessageSid}.json`
   - Retrieves message details and delivery status
   ```bash
   curl "https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages/{MESSAGE_SID}.json" \
     -u {ACCOUNT_SID}:{AUTH_TOKEN}
   ```

---

## ElevenLabs

**Base URL:** `https://api.elevenlabs.io/v1`

**Auth:** Header `xi-api-key: {ELEVENLABS_API_KEY}`

**Common Operations:**

1. **Text-to-Speech** - `POST /text-to-speech/{voice_id}`
   - Converts text to speech audio
   ```bash
   curl -X POST "https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}" \
     -H "xi-api-key: {API_KEY}" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello world", "model_id": "eleven_monolingual_v1"}' \
     --output audio.mp3
   ```

2. **List Voices** - `GET /voices`
   - Retrieves all available voices
   ```bash
   curl "https://api.elevenlabs.io/v1/voices" \
     -H "xi-api-key: {API_KEY}"
   ```

3. **Get Voice** - `GET /voices/{voice_id}`
   - Gets details for a specific voice
   ```bash
   curl "https://api.elevenlabs.io/v1/voices/{VOICE_ID}" \
     -H "xi-api-key: {API_KEY}"
   ```

---

## ClickSend

**Base URL:** `https://rest.clicksend.com/v3`

**Auth:** HTTP Basic authentication

- Username: Your ClickSend username
- Password: Your API key
- Base64 encode as: `base64(username:api_key)`

Header: `Authorization: Basic {base64_encoded_credentials}`

**Common Operations:**

1. **Send SMS** - `POST /sms/send`
   - Sends SMS messages
   ```bash
   curl -X POST "https://rest.clicksend.com/v3/sms/send" \
     -H "Authorization: Basic {BASE64_CREDENTIALS}" \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"to": "+15551234567", "body": "Hello!", "from": "YourName"}]}'
   ```

2. **Send Email** - `POST /email/send`
   - Sends transactional emails
   ```bash
   curl -X POST "https://rest.clicksend.com/v3/email/send" \
     -H "Authorization: Basic {BASE64_CREDENTIALS}" \
     -H "Content-Type: application/json" \
     -d '{"to": [{"email": "user@example.com"}], "from": {"email": "sender@example.com"}, "subject": "Test", "body": "Hello!"}'
   ```

3. **Get Delivery Report** - `GET /sms/receipts`
   - Retrieves SMS delivery receipts
   ```bash
   curl "https://rest.clicksend.com/v3/sms/receipts" \
     -H "Authorization: Basic {BASE64_CREDENTIALS}"
   ```

---

## Groq

**Base URL:** `https://api.groq.com/openai/v1`

**Auth:** Header `Authorization: Bearer {GROQ_API_KEY}`

OpenAI-compatible API format.

**Common Operations:**

1. **Chat Completion** - `POST /chat/completions`
   - Generates chat completions (main inference endpoint)
   ```bash
   curl -X POST "https://api.groq.com/openai/v1/chat/completions" \
     -H "Authorization: Bearer {GROQ_API_KEY}" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "llama-3.3-70b-versatile",
       "messages": [{"role": "user", "content": "Hello!"}]
     }'
   ```

2. **List Models** - `GET /models`
   - Retrieves available models
   ```bash
   curl "https://api.groq.com/openai/v1/models" \
     -H "Authorization: Bearer {GROQ_API_KEY}"
   ```

3. **Audio Transcription** - `POST /audio/transcriptions`
   - Transcribes audio using Whisper
   ```bash
   curl -X POST "https://api.groq.com/openai/v1/audio/transcriptions" \
     -H "Authorization: Bearer {GROQ_API_KEY}" \
     -H "Content-Type: multipart/form-data" \
     -F file="@audio.mp3" \
     -F model="whisper-large-v3"
   ```

---

## Quick Reference Table

| Service      | Base URL                                | Auth Header                              |
|--------------|----------------------------------------|------------------------------------------|
| HubSpot      | `https://api.hubapi.com`               | `Authorization: Bearer {TOKEN}`          |
| GoHighLevel  | `https://services.leadconnectorhq.com` | `Authorization: Bearer {TOKEN}`          |
| Stripe       | `https://api.stripe.com/v1`            | Basic auth with `sk_xxx:` or Bearer      |
| Twilio       | `https://api.twilio.com/2010-04-01`    | Basic auth with `{SID}:{AUTH_TOKEN}`     |
| ElevenLabs   | `https://api.elevenlabs.io/v1`         | `xi-api-key: {API_KEY}`                  |
| ClickSend    | `https://rest.clicksend.com/v3`        | `Authorization: Basic {BASE64}`          |
| Groq         | `https://api.groq.com/openai/v1`       | `Authorization: Bearer {API_KEY}`        |

---

*Last updated: 2026-02-26*
