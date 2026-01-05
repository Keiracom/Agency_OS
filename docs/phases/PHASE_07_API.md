# Phase 7: API Routes

**Status:** ✅ Complete  
**Tasks:** 8  
**Dependencies:** Phase 6 complete  
**Checkpoint:** CEO approval required

---

## Overview

Create FastAPI routes for all client-facing endpoints.

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| API-001 | FastAPI app | Main app, middleware | `src/api/main.py` | M |
| API-002 | Dependencies | Auth via memberships | `src/api/dependencies.py` | M |
| API-003 | Health routes + test | Health check | `src/api/routes/health.py`, `tests/test_api/test_health.py` | S |
| API-004 | Campaign routes + test | CRUD (soft delete) | `src/api/routes/campaigns.py`, `tests/test_api/test_campaigns.py` | L |
| API-005 | Lead routes + test | CRUD + enrichment | `src/api/routes/leads.py`, `tests/test_api/test_leads.py` | L |
| API-006 | Webhook routes | Inbound (Postmark/Twilio) | `src/api/routes/webhooks.py` | M |
| API-007 | Outbound webhooks | Client dispatch + HMAC | `src/api/routes/webhooks_outbound.py` | M |
| API-008 | Report routes + test | Metrics | `src/api/routes/reports.py`, `tests/test_api/test_reports.py` | M |

---

## Route Summary

| Route | Method | Purpose |
|-------|--------|---------|
| `/health` | GET | Health check |
| `/api/v1/campaigns` | GET, POST | List/create campaigns |
| `/api/v1/campaigns/{id}` | GET, PUT, DELETE | Single campaign |
| `/api/v1/leads` | GET, POST | List/create leads |
| `/api/v1/leads/{id}` | GET, PUT, DELETE | Single lead |
| `/api/v1/leads/{id}/enrich` | POST | Trigger enrichment |
| `/api/v1/webhooks/postmark` | POST | Inbound email |
| `/api/v1/webhooks/twilio` | POST | Inbound SMS |
| `/api/v1/reports/campaign/{id}` | GET | Campaign metrics |

---

## Authentication

Auth is via Supabase Auth + Memberships:

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    payload = verify_supabase_token(token)
    user = await db.get(User, payload["sub"])
    return user

async def get_current_client(
    user: User = Depends(get_current_user),
    client_id: UUID = Header(...),
    db: AsyncSession = Depends(get_db)
) -> Client:
    membership = await db.execute(
        select(Membership)
        .where(Membership.user_id == user.id)
        .where(Membership.client_id == client_id)
        .where(Membership.accepted_at.isnot(None))
    )
    if not membership:
        raise HTTPException(403, "Not a member of this client")
    return await db.get(Client, client_id)
```

---

## Soft Delete Pattern

```python
@router.delete("/campaigns/{id}")
async def delete_campaign(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_current_client)
):
    campaign = await db.get(Campaign, id)
    campaign.deleted_at = datetime.utcnow()  # Soft delete
    await db.commit()
    return {"status": "deleted"}
```

---

## Checkpoint 4 Criteria

- [ ] All routes implemented
- [ ] Auth via memberships working
- [ ] Webhooks receive and process
- [ ] Soft deletes working
