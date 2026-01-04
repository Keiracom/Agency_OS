# SKILL.md — Builder Agent

**Skill:** Builder Agent for Agency OS  
**Author:** CTO (Claude)  
**Version:** 2.0  
**Created:** December 24, 2025

---

## Purpose

The Builder Agent creates production-ready code following PROJECT_BLUEPRINT.md and skill files. This skill file defines patterns, standards, and workflows for building.

---

## Dynamic Context Detection

Before building anything, always detect context:

```python
# Pseudocode for context detection
1. Read builder_tasks/pending.md
   - If not empty → Build these FIRST (QA found gaps)

2. Read PROGRESS.md
   - Find current phase (🟡 in progress)
   - Find next task (🔴 not started)
   - Extract TASK-ID

3. Read skills/SKILL_INDEX.md
   - Find skill file for current phase
   
4. Read the skill file
   - Get required files, patterns, standards
```

---

## Code Templates

### Python Module Template

```python
"""
FILE: src/[layer]/[filename].py
TASK: [TASK-ID]
PHASE: [X]
PURPOSE: [One-line description]

DEPENDENCIES:
- [List internal imports]

EXPORTS:
- [List what this module exports]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from src.models.client import Client

# Local imports following hierarchy
from src.models.base import Base, SoftDeleteMixin, generate_uuid7
from src.exceptions import ValidationError, NotFoundError


class MyModel(Base, SoftDeleteMixin):
    """SQLAlchemy model description."""
    
    __tablename__ = "my_table"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid7)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete


class MyModelCreate(BaseModel):
    """Pydantic schema for creation."""
    name: str = Field(..., min_length=1, max_length=255)


class MyModelResponse(BaseModel):
    """Pydantic schema for response."""
    id: str
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


async def create_my_model(
    db: AsyncSession,
    data: MyModelCreate
) -> MyModelResponse:
    """
    Create a new model instance.
    
    Args:
        db: Database session (injected by caller)
        data: Creation data
        
    Returns:
        Created model as response schema
        
    Raises:
        ValidationError: If validation fails
    """
    model = MyModel(**data.model_dump())
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return MyModelResponse.from_orm(model)


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12)
- [x] Uses dependency injection (Rule 11)
- [x] Soft delete column present (Rule 14)
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Pydantic schemas for input/output
"""
```

### Python Engine Template

```python
"""
FILE: src/engines/[name]_engine.py
TASK: [TASK-ID]
PHASE: [X]
PURPOSE: [Engine description]

DEPENDENCIES:
- src/models/[models used]
- src/integrations/[integrations used]

EXPORTS:
- [EngineName]
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.lead import Lead
from src.integrations.redis import RedisClient
from src.exceptions import EngineError


class MyEngine:
    """
    Engine description.
    
    This engine handles [specific responsibility].
    It does NOT instantiate database sessions (Rule 11).
    It does NOT import from other engines (Rule 12).
    """
    
    def __init__(self, redis: RedisClient):
        """
        Initialize engine with dependencies.
        
        Args:
            redis: Redis client for caching
        """
        self.redis = redis
        self.cache_prefix = "v1:my_engine"  # Rule 16: versioned keys
    
    async def process(
        self,
        db: AsyncSession,  # Injected, never instantiated
        lead_id: str
    ) -> Dict[str, Any]:
        """
        Process a lead.
        
        Args:
            db: Database session (injected)
            lead_id: Lead UUID
            
        Returns:
            Processing result
            
        Raises:
            EngineError: If processing fails
        """
        # Check cache first
        cache_key = f"{self.cache_prefix}:{lead_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return cached
        
        # Query with soft delete check (Rule 14)
        query = select(Lead).where(
            Lead.id == lead_id,
            Lead.deleted_at.is_(None)
        )
        result = await db.execute(query)
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise EngineError(f"Lead {lead_id} not found")
        
        # Process...
        processed = {"lead_id": lead_id, "status": "processed"}
        
        # Cache result (90 day TTL)
        await self.redis.set(cache_key, processed, ttl=86400 * 90)
        
        return processed


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top
- [x] Does NOT import from src.engines/* (Rule 12)
- [x] Does NOT import from src.orchestration/* (Rule 12)
- [x] db: AsyncSession passed as argument (Rule 11)
- [x] Soft delete check in queries (Rule 14)
- [x] Cache key has version prefix (Rule 16)
- [x] Type hints on all methods
- [x] No TODO/FIXME/pass statements
"""
```

### TypeScript Page Template

```typescript
/**
 * FILE: frontend/app/[path]/page.tsx
 * TASK: [TASK-ID]
 * PHASE: [X]
 * PURPOSE: [Page description]
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase';

// UI Components from shared library
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

// Icons
import { Plus, Search, RefreshCw } from 'lucide-react';

// Types - NEVER use 'any'
interface DataItem {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'pending';
  createdAt: string;
  updatedAt: string;
}

interface PageState {
  data: DataItem[];
  loading: boolean;
  error: string | null;
  searchQuery: string;
}

export default function MyPage() {
  const router = useRouter();
  const [state, setState] = useState<PageState>({
    data: [],
    loading: true,
    error: null,
    searchQuery: '',
  });

  const fetchData = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const supabase = createClient();
      
      let query = supabase
        .from('my_table')
        .select('*')
        .is('deleted_at', null) // Soft delete check
        .order('created_at', { ascending: false });
      
      if (state.searchQuery) {
        query = query.ilike('name', `%${state.searchQuery}%`);
      }
      
      const { data, error } = await query;
      
      if (error) throw error;
      
      setState(prev => ({ ...prev, data: data || [], loading: false }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to fetch data',
        loading: false,
      }));
    }
  }, [state.searchQuery]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setState(prev => ({ ...prev, searchQuery: e.target.value }));
  };

  // Loading state
  if (state.loading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map(i => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (state.error) {
    return (
      <div className="p-6">
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">Error: {state.error}</p>
            <Button onClick={fetchData} variant="outline" className="mt-4">
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Success state
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Page Title</h1>
        <Button onClick={() => router.push('/path/new')}>
          <Plus className="mr-2 h-4 w-4" />
          Add New
        </Button>
      </div>

      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search..."
            value={state.searchQuery}
            onChange={handleSearch}
            className="pl-10"
          />
        </div>
      </div>

      {/* Data Grid */}
      {state.data.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            No items found
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {state.data.map((item) => (
            <Card
              key={item.id}
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => router.push(`/path/${item.id}`)}
            >
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {item.name}
                  <Badge variant={item.status === 'active' ? 'default' : 'secondary'}>
                    {item.status}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Created: {new Date(item.createdAt).toLocaleDateString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Import Hierarchy (Rule 12)

```
LAYER 1 (Bottom): src/models/
├── Can import: src/exceptions.py, external packages
├── Cannot import: src/integrations/, src/engines/, src/orchestration/

LAYER 2: src/integrations/
├── Can import: src/models/, src/exceptions.py, external packages
├── Cannot import: src/engines/, src/orchestration/

LAYER 3: src/engines/
├── Can import: src/models/, src/integrations/, src/exceptions.py
├── Cannot import: src/engines/* (other engines), src/orchestration/

LAYER 4 (Top): src/orchestration/
├── Can import: Everything below
├── Coordinates engines, passes data between them
```

---

## Checklist Before Committing

Before marking a task as complete:

- [ ] Contract comment with FILE, TASK, PHASE, PURPOSE
- [ ] Follows import hierarchy (no violations)
- [ ] Uses dependency injection (db passed as argument)
- [ ] Soft delete support (deleted_at column, query filters)
- [ ] Type hints on all functions/methods
- [ ] No placeholder code (pass, TODO, FIXME, ...)
- [ ] No hardcoded secrets
- [ ] Error handling present
- [ ] Verification checklist at bottom of file
- [ ] PROGRESS.md updated

---

## Common Mistakes to Avoid

| Mistake | Why It's Bad | Correct Approach |
|---------|--------------|------------------|
| `db = AsyncSessionLocal()` | Violates DI (Rule 11) | `async def func(db: AsyncSession)` |
| `from src.engines.x import y` in engine | Cross-engine import (Rule 12) | Pass data via orchestration |
| `await db.delete(obj)` | Hard delete (Rule 14) | `obj.deleted_at = datetime.utcnow()` |
| `data: any` in TypeScript | No type safety | Define interface |
| `pass` or `...` in function | Incomplete code | Full implementation |
| `# TODO: implement` | Placeholder | Implement now |

---

## Workflow

```
1. Check builder_tasks/pending.md
   └── If QA found missing files, build those FIRST

2. Read PROGRESS.md
   └── Find next task

3. Read relevant skill file
   └── Understand requirements

4. Create file with template
   └── Contract comment
   └── Imports
   └── Implementation
   └── Verification checklist

5. Update PROGRESS.md
   └── 🔴 → 🟢
   └── Add file path

6. Clear from builder_tasks/pending.md if applicable
```

---
