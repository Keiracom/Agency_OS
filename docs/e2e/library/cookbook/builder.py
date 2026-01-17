"""
Builder Agent Skill for Agency OS

The Builder Agent creates production-ready code following PROJECT_BLUEPRINT.md
and skill files. This module defines patterns, standards, and workflows for building.

Version: 2.0
Author: CTO (Claude)
Created: December 24, 2025

Key Responsibilities:
- Create new files following templates
- Complete stubs and placeholders
- Update PROGRESS.md after tasks
- Follow import hierarchy strictly

Dynamic Context Detection:
1. Read builder_tasks/pending.md - If not empty, build these FIRST (QA found gaps)
2. Read PROGRESS.md - Find current phase and next task
3. Read skills/SKILL_INDEX.md - Find skill file for current phase
4. Read the skill file - Get required files, patterns, standards
"""

from typing import Dict, List


def get_instructions() -> str:
    """Return the key instructions for the Builder agent."""
    return """
BUILDER AGENT INSTRUCTIONS
==========================

1. CONTEXT DETECTION (Before building anything):
   - Check builder_tasks/pending.md first (QA-found gaps have priority)
   - Read PROGRESS.md to find current phase and next task
   - Read the relevant skill file for requirements

2. CODE STANDARDS:
   - Every file needs a contract comment (FILE, TASK, PHASE, PURPOSE)
   - Follow import hierarchy strictly (models -> integrations -> engines -> orchestration)
   - Use dependency injection (db passed as argument, never instantiated)
   - Soft delete only (deleted_at column, never hard DELETE)
   - Type hints on all functions
   - No placeholder code (pass, TODO, FIXME, ...)

3. CHECKLIST BEFORE COMMITTING:
   [ ] Contract comment with FILE, TASK, PHASE, PURPOSE
   [ ] Follows import hierarchy (no violations)
   [ ] Uses dependency injection
   [ ] Soft delete support
   [ ] Type hints on all functions
   [ ] No placeholder code
   [ ] Error handling present
   [ ] PROGRESS.md updated

4. WORKFLOW:
   1. Check builder_tasks/pending.md
   2. Read PROGRESS.md -> find next task
   3. Read relevant skill file
   4. Create file with template
   5. Update PROGRESS.md
   6. Clear from builder_tasks/pending.md if applicable
"""


def get_code_templates() -> Dict[str, str]:
    """Return code templates for the Builder agent."""
    return {
        "python_module": PYTHON_MODULE_TEMPLATE,
        "python_engine": PYTHON_ENGINE_TEMPLATE,
        "typescript_page": TYPESCRIPT_PAGE_TEMPLATE,
    }


def get_import_hierarchy() -> Dict[str, Dict[str, List[str]]]:
    """Return the import hierarchy rules."""
    return {
        "layer_1_models": {
            "path": "src/models/",
            "can_import": ["src/exceptions.py", "external packages"],
            "cannot_import": ["src/integrations/", "src/engines/", "src/orchestration/"],
        },
        "layer_2_integrations": {
            "path": "src/integrations/",
            "can_import": ["src/models/", "src/exceptions.py", "external packages"],
            "cannot_import": ["src/engines/", "src/orchestration/"],
        },
        "layer_3_engines": {
            "path": "src/engines/",
            "can_import": ["src/models/", "src/integrations/", "src/exceptions.py"],
            "cannot_import": ["src/engines/* (other engines)", "src/orchestration/"],
        },
        "layer_4_orchestration": {
            "path": "src/orchestration/",
            "can_import": ["Everything below"],
            "cannot_import": [],
        },
    }


def get_common_mistakes() -> List[Dict[str, str]]:
    """Return common mistakes to avoid."""
    return [
        {
            "mistake": "db = AsyncSessionLocal()",
            "why_bad": "Violates DI (Rule 11)",
            "correct": "async def func(db: AsyncSession)",
        },
        {
            "mistake": "from src.engines.x import y in engine",
            "why_bad": "Cross-engine import (Rule 12)",
            "correct": "Pass data via orchestration",
        },
        {
            "mistake": "await db.delete(obj)",
            "why_bad": "Hard delete (Rule 14)",
            "correct": "obj.deleted_at = datetime.utcnow()",
        },
        {
            "mistake": "data: any in TypeScript",
            "why_bad": "No type safety",
            "correct": "Define interface",
        },
        {
            "mistake": "pass or ... in function",
            "why_bad": "Incomplete code",
            "correct": "Full implementation",
        },
    ]


# =============================================================================
# CODE TEMPLATES
# =============================================================================

PYTHON_MODULE_TEMPLATE = '''"""
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
'''

PYTHON_ENGINE_TEMPLATE = '''"""
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
'''

TYPESCRIPT_PAGE_TEMPLATE = '''/**
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
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
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

  // Loading/Error/Success states...
  return (
    <div className="p-6 space-y-6">
      {/* Page content */}
    </div>
  );
}
'''


if __name__ == "__main__":
    print(get_instructions())
