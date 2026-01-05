# Supabase Integration

**File:** `src/integrations/supabase.py`  
**Purpose:** PostgreSQL database client  
**Docs:** https://supabase.com/docs

---

## Connection Rules

| Use Case | Port | Pooler Type |
|----------|------|-------------|
| Application/API | 6543 | Transaction Pooler |
| Prefect Workers | 6543 | Transaction Pooler |
| Migrations | 5432 | Session Pooler |

---

## Pool Configuration

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

---

## Usage Pattern

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

## RLS Integration

Row-Level Security via memberships:

```python
# In dependencies.py
async def get_current_client(
    user: User = Depends(get_current_user),
    client_id: UUID = Header(...),
    db: AsyncSession = Depends(get_db)
) -> Client:
    """Verify user has access to client via membership."""
    membership = await db.execute(
        select(Membership)
        .where(Membership.user_id == user.id)
        .where(Membership.client_id == client_id)
        .where(Membership.accepted_at.isnot(None))
    )
    if not membership.scalar():
        raise HTTPException(403, "Not a member")
    return await db.get(Client, client_id)
```

---

## Auth Integration

Supabase Auth handles:
- User signup/login
- JWT token generation
- Password reset
- OAuth providers

```python
from supabase import create_client

supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY
)

# Verify JWT in API
def verify_token(token: str) -> dict:
    return supabase.auth.get_user(token)
```
