# Right-to-Erasure Engineering Flow

**Status:** DRAFT — pending [LAWYER] review and SLA confirmation  
**Jurisdiction baseline:** AU Privacy Act (APP 11) + GDPR Article 17 + CCPA § 1798.105  
**Maintainer:** Engineering (Max / Agency OS CTO track)  
**Related KEIs:** KEI-118 (compliance scaffold), KEI-116 (customer_api_keys), KEI-117A (Valkey per-tenant namespace)  
**Follow-up KEI needed:** `public.erasure_audit_log` table creation (flagged below)

---

## Overview

When a data subject submits a Right-to-Erasure (RTbE) / "Right to be Forgotten" request, Keiracom must delete all personally identifiable and customer-linked data from every data store within the agreed SLA window. This document specifies the call sequence, data stores affected, out-of-scope data, and audit obligations.

**Proposed SLA:** 7 calendar days from verified request receipt.  
`[CONFIRM SLA WITH LAWYER — AU Privacy Act allows "reasonable time"; GDPR Art 17 requires "without undue delay"; 7 days is a conservative engineering target]`

---

## Triggering Conditions

A RTbE request is valid and must be actioned when:
1. A verified data subject (confirmed identity via email + OTP or account re-auth) submits a deletion request via the in-product form or direct email to `[CONTROLLER DPO EMAIL — see Privacy Policy template]`.
2. The request does not fall into an exemption (legal hold, compliance archive, anonymised aggregate — see §9 Out-of-Scope).
3. The request is logged to `public.erasure_requests` (table creation also pending — bundle with `erasure_audit_log` KEI).

---

## Execution Sequence

Run steps 1–6 atomically within a single orchestration job (Prefect recommended). If any step fails, abort and alert on-call engineer — do NOT partially delete.

## 1. Supabase Public Schema

Tables containing customer-linked data:

```sql
-- Revoke API keys first (KEI-116: customer_api_keys)
DELETE FROM public.customer_api_keys
WHERE customer_id = $1
RETURNING id, key_prefix, created_at;

-- Tasks and verifications
DELETE FROM public.task_verifications
WHERE task_id IN (SELECT id FROM public.tasks WHERE customer_id = $1)
RETURNING id;

DELETE FROM public.tasks
WHERE customer_id = $1
RETURNING id;

-- Agent memories attributed to this tenant/customer
DELETE FROM public.agent_memories
WHERE callsign = $1   -- if customer-mapped to a callsign
   OR typed_metadata->>'customer_id' = $1::text
RETURNING id;

-- Write audit row (see §8 Audit Log)
INSERT INTO public.erasure_audit_log
  (request_id, table_name, rows_deleted, deleted_at)
VALUES
  ($2, 'customer_api_keys', <count>, NOW()),
  ($2, 'tasks',             <count>, NOW()),
  ($2, 'task_verifications',<count>, NOW()),
  ($2, 'agent_memories',    <count>, NOW());
```

> **Note:** `public.erasure_audit_log` does not yet exist. **Flag for follow-up KEI** — create this table before activating erasure flow in production. Minimal schema: `(id uuid PK, request_id uuid, table_name text, rows_deleted int, deleted_at timestamptz)`.

## 2. Supabase Per-Tenant Schemas

If per-tenant schemas (`tenant_<id>.*`) are provisioned for a customer:

```sql
-- List tenant schemas for this customer_id
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name = 'tenant_' || $1;

-- If exists, cascade-drop the entire schema
DROP SCHEMA IF EXISTS tenant_<id> CASCADE;

-- Audit row
INSERT INTO public.erasure_audit_log
  (request_id, table_name, rows_deleted, deleted_at)
VALUES ($2, 'tenant_schema_drop:tenant_' || $1, NULL, NOW());
```

> `[VERIFY WITH LAWYER — schema-level drop is irreversible. Confirm no legal-hold obligation before executing.]`

## 3. Valkey (Redis-compatible cache)

Per-tenant namespacing per KEI-117A uses the prefix `tenant:<id>:`.

```bash
# List all keys for this tenant
KEYS tenant:<customer_id>:*

# Delete atomically via UNLINK (non-blocking DEL)
UNLINK tenant:<customer_id>:*
```

Python client equivalent:
```python
async def delete_tenant_keys(redis_client, tenant_id: str) -> int:
    pattern = f"tenant:{tenant_id}:*"
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.unlink(*keys)
    return len(keys)
```

Log deleted key count to audit log.

## 4. Weaviate

Three collections hold tenant-linked objects: `Discoveries`, `Decisions`, `Keis`.

```python
import weaviate
from weaviate.classes.query import Filter

client = weaviate.connect_to_local()  # or weaviate.connect_to_weaviate_cloud(...)

for collection_name in ["Discoveries", "Decisions", "Keis"]:
    collection = client.collections.get(collection_name)
    result = collection.data.delete_many(
        where=Filter.by_property("tenant_id").equal(tenant_id)
    )
    # log result.matches (count deleted) to audit log
```

> Confirm `tenant_id` is a stored property on all three collections in the live schema. If absent, the filter returns 0 matches and no data is deleted — silent failure risk. `[VERIFY WEAVIATE SCHEMA — run describe on each collection before enabling this step in production]`.

## 5. Cognee Graph DB

```python
import cognee

# Prune all data attributed to this tenant
await cognee.prune_data(tenant_id=tenant_id)
```

> `[VERIFY COGNEE API — confirm method name is cognee.prune_data(tenant_id=...) against vendor docs. If not available, use cognee.prune() which nukes ALL data — NOT safe for multi-tenant; raise with vendor before production use.]`

Log confirmation response to audit log.

## 6. Logs and Backups

**Application logs (Better Stack):**  
Better Stack stores structured logs. Tenant-scoped log purge requires the Better Stack Logs REST API `DELETE /v2/logs` endpoint with a query filter.  
`[VERIFY BETTER STACK LOG DELETION API — confirm endpoint + auth pattern before implementing]`

**Database backups:**  
Supabase daily backups are stored for [RETENTION DAYS — confirm with Supabase plan]. Backups contain the data prior to deletion.  
`[CONFIRM WITH LAWYER — AU Privacy Act allows retention of backups for a reasonable period. Agree on backup expiry window, e.g., "backups containing deleted data expire within 30 days of erasure request."]`

**Local filesystem / agent tmux artifacts:**  
Any on-disk agent logs at `/tmp/telegram-relay-*/`, `/tmp/cognee-context-*.md`, and similar ephemeral paths are not persisted beyond process lifetime. No action required for erasure unless a persistent log daemon is running.

---

## 7. SLA

| Step | Target |
|---|---|
| Request acknowledgement | 24 hours |
| Identity verification | 48 hours |
| Full erasure completed | 7 calendar days from verified request |
| Audit log written | Same transaction as erasure |
| Confirmation to data subject | Within 1 business day of completion |

`[CONFIRM SLA WITH LAWYER — AU 30-day outer bound vs GDPR 30-day + 2-month extension vs CCPA 45-day. 7 days is internal engineering SLA, not the legal outer bound.]`

---

## 8. Audit Log

Every erasure write MUST produce a row in `public.erasure_audit_log` (to be created — see §1 note). The audit log is:
- **Not deletable** by the erasure flow itself (write-once, append-only, delete permission revoked at DB level).
- Retained for `[CONFIRM RETENTION PERIOD WITH LAWYER — GDPR Art 5(2) accountability; AU Privacy Act s 13G]`.
- Accessible to the DPO / privacy officer on request.

Minimum columns: `id`, `request_id`, `requestor_email_hash` (bcrypt — never store raw PII in audit log), `table_name`, `rows_deleted`, `deleted_at`, `performed_by` (service account or agent callsign).

---

## 9. Out-of-Scope (What We Do NOT Delete)

| Data type | Reason retained |
|---|---|
| Anonymised aggregates (e.g. CIS score distributions) | No PII linkage; lawful retention |
| Compliance archives required by law | Legal hold obligation `[CONFIRM RETENTION CLASSES WITH LAWYER]` |
| `public.erasure_audit_log` rows | Write-once accountability record |
| Aggregated pipeline metrics (non-customer-linked) | No PII; operational necessity |
| Billing records | Tax compliance `[CONFIRM TAX RETENTION PERIOD — AU GST typically 5 years]` |

---

## 10. Testing the Erasure Flow

Before production enablement:
1. Create a test tenant with synthetic data across all 6 stores.
2. Execute erasure flow against test tenant ID.
3. Verify: 0 rows remain in Supabase public tables for `customer_id = test_id`.
4. Verify: 0 Valkey keys matching `tenant:<test_id>:*`.
5. Verify: 0 Weaviate objects with `tenant_id = test_id` in all 3 collections.
6. Verify: Cognee prune confirmed.
7. Audit log contains one row per store per `request_id`.

---

## Follow-up KEIs Required

| Item | Status |
|---|---|
| Create `public.erasure_requests` table | Flag for new KEI |
| Create `public.erasure_audit_log` table (write-once) | Flag for new KEI |
| Verify Weaviate `tenant_id` property on all 3 collections | Flag for new KEI |
| Confirm Cognee `prune_data` API | Flag for new KEI |
| Implement Better Stack log purge endpoint | Flag for new KEI |
| Wire Prefect flow for orchestrated erasure | Flag for new KEI |
