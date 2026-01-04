# Phase 16E: Engine Modifications Specification

## Technical Specification Document

**Version**: 1.0  
**Date**: December 27, 2025  
**Depends On**: Phase 16A-D (All Detectors)  
**Status**: Ready for Development  
**Estimated Tasks**: 5  

---

## Overview

Phase 16E modifies existing engines to:
1. **Capture content snapshots** when sending messages (for WHAT Detector learning)
2. **Consume patterns** to optimize real-time decisions
3. **Track touch numbers** for sequence analysis

**Engines Modified**:
- Email Engine (content capture + pattern consumption)
- SMS Engine (content capture)
- LinkedIn Engine (content capture)
- Voice Engine (content capture)
- Scorer Engine (WHO pattern consumption)
- Allocator Engine (HOW/WHEN pattern consumption)

---

## 1. Email Engine Modifications

### File: `src/engines/email.py`

```python
"""
Email Engine - Modified for Conversion Intelligence

Changes:
1. Store content_snapshot on activity creation
2. Track touch_number in sequence
3. Extract pain points and CTAs used
4. Flag personalization elements
"""

import re
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.lead import Lead
from src.models.client import Client


# =============================================================================
# PAIN POINT EXTRACTION (matches WHAT Detector vocabulary)
# =============================================================================

PAIN_POINT_KEYWORDS = {
    "leads": ["leads", "pipeline", "prospects", "opportunities", "qualified", "mql", "sql", "inbound"],
    "revenue": ["revenue", "sales", "growth", "roi", "profit", "income", "deals", "closed", "won"],
    "time": ["time", "hours", "manual", "automate", "efficiency", "busy", "bandwidth", "overwhelmed"],
    "scaling": ["scale", "scaling", "growth", "capacity", "bandwidth", "hire", "team", "expand"],
    "competition": ["competitors", "competition", "market share", "behind", "catching up", "losing"],
    "cost": ["cost", "expensive", "budget", "waste", "spending", "save", "afford", "price"],
    "quality": ["quality", "results", "performance", "outcomes", "better", "improve", "consistent"],
    "clients": ["clients", "customers", "retention", "churn", "satisfaction", "referrals"],
}

CTA_PATTERNS = [
    "open to a quick chat",
    "worth 15 minutes",
    "worth a conversation",
    "free audit",
    "free analysis",
    "quick call",
    "schedule a call",
    "book a time",
    "interested in learning",
    "happy to share",
    "let me know",
    "thoughts?",
    "make sense to connect",
    "grab 15 minutes",
]


def extract_pain_points(text: str) -> list[str]:
    """Extract pain points mentioned in text"""
    text_lower = text.lower()
    found = []
    
    for pain_point, keywords in PAIN_POINT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                found.append(pain_point)
                break
    
    return found


def extract_cta(text: str) -> Optional[str]:
    """Extract CTA from text"""
    text_lower = text.lower()
    
    for cta in CTA_PATTERNS:
        if cta in text_lower:
            return cta
    
    return None


def detect_personalization(
    text: str, 
    lead: Lead
) -> dict:
    """Detect personalization elements in message"""
    text_lower = text.lower()
    
    return {
        "has_company_mention": (
            lead.company_name.lower() in text_lower 
            if lead.company_name else False
        ),
        "has_first_name": (
            lead.first_name.lower() in text_lower 
            if lead.first_name else False
        ),
        "has_recent_news": bool(
            re.search(r"(noticed|saw|congrats|congratulations|just saw)", text_lower)
        ),
        "has_mutual_connection": (
            "mutual" in text_lower or 
            "connection" in text_lower or
            "referred" in text_lower
        ),
        "has_industry_specific": (
            lead.industry.lower() in text_lower 
            if lead.industry else False
        ),
    }


# =============================================================================
# EMAIL ENGINE CLASS
# =============================================================================

class EmailEngine:
    """
    Sends emails and tracks content for learning.
    
    MODIFIED: Now captures content_snapshot on every send.
    """
    
    async def send(
        self,
        db: AsyncSession,
        lead: Lead,
        client: Client,
        subject: str,
        body: str,
        template_id: Optional[str] = None,
        touch_number: int = 1,
        sequence_id: Optional[str] = None,
    ) -> Activity:
        """
        Send an email and create activity with content snapshot.
        
        Args:
            db: Database session
            lead: Target lead
            client: Client sending the email
            subject: Email subject line
            body: Email body content
            template_id: Optional template ID used
            touch_number: Position in sequence (1-indexed)
            sequence_id: Parent sequence ID
            
        Returns:
            Activity record with content_snapshot
        """
        # 1. Actually send the email (existing logic)
        send_result = await self._send_via_provider(
            to_email=lead.email,
            from_email=client.sending_email,
            subject=subject,
            body=body,
            client=client,
        )
        
        # 2. Extract content features for learning
        pain_points = extract_pain_points(body)
        cta = extract_cta(body)
        personalization = detect_personalization(body, lead)
        
        # 3. Build content snapshot
        content_snapshot = {
            # Core content
            "subject": subject,
            "body": body,
            "template_id": template_id,
            
            # Metrics
            "word_count": len(body.split()),
            "subject_word_count": len(subject.split()),
            "char_count": len(body),
            
            # Extracted features
            "pain_points_used": pain_points,
            "cta_used": cta,
            
            # Personalization flags
            **personalization,
            
            # Sequence context
            "touch_number": touch_number,
            "sequence_id": sequence_id,
            
            # Timing
            "sent_at": datetime.utcnow().isoformat(),
            "day_of_week": datetime.utcnow().strftime("%A"),
            "hour_of_day": datetime.utcnow().hour,
        }
        
        # 4. Create activity record
        activity = Activity(
            id=generate_uuid(),
            client_id=client.id,
            lead_id=lead.id,
            action="email_sent",
            channel="email",
            content_snapshot=content_snapshot,
            metadata={
                "provider_message_id": send_result.message_id,
                "touch_number": touch_number,
                "sequence_id": sequence_id,
            },
            created_at=datetime.utcnow(),
        )
        
        db.add(activity)
        await db.flush()
        
        # 5. Update lead's last_contacted
        lead.last_contacted_at = datetime.utcnow()
        lead.touch_count = (lead.touch_count or 0) + 1
        
        return activity
    
    async def _send_via_provider(
        self,
        to_email: str,
        from_email: str,
        subject: str,
        body: str,
        client: Client,
    ) -> "SendResult":
        """
        Send via configured email provider (Resend, SendGrid, etc.)
        
        This method remains unchanged - just the actual send logic.
        """
        # Existing provider logic...
        pass
```

---

## 2. SMS Engine Modifications

### File: `src/engines/sms.py`

```python
"""
SMS Engine - Modified for Conversion Intelligence

Changes:
1. Store content_snapshot on activity creation
2. Track touch_number in sequence
3. Extract CTAs used
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.lead import Lead
from src.models.client import Client


# Reuse extraction functions from email engine
from src.engines.email import extract_cta, detect_personalization


class SMSEngine:
    """
    Sends SMS messages and tracks content for learning.
    
    MODIFIED: Now captures content_snapshot on every send.
    """
    
    async def send(
        self,
        db: AsyncSession,
        lead: Lead,
        client: Client,
        message: str,
        touch_number: int = 1,
        sequence_id: Optional[str] = None,
    ) -> Activity:
        """
        Send an SMS and create activity with content snapshot.
        """
        # 1. Send via provider (Twilio)
        send_result = await self._send_via_twilio(
            to_phone=lead.phone,
            from_phone=client.sending_phone,
            message=message,
            client=client,
        )
        
        # 2. Extract content features
        cta = extract_cta(message)
        personalization = detect_personalization(message, lead)
        
        # 3. Build content snapshot
        content_snapshot = {
            # Core content
            "body": message,
            
            # Metrics
            "char_count": len(message),
            "segment_count": (len(message) // 160) + 1,
            
            # Extracted features
            "cta_used": cta,
            
            # Personalization flags
            "has_company_mention": personalization["has_company_mention"],
            "has_first_name": personalization["has_first_name"],
            
            # Sequence context
            "touch_number": touch_number,
            "sequence_id": sequence_id,
            
            # Timing
            "sent_at": datetime.utcnow().isoformat(),
            "day_of_week": datetime.utcnow().strftime("%A"),
            "hour_of_day": datetime.utcnow().hour,
        }
        
        # 4. Create activity record
        activity = Activity(
            id=generate_uuid(),
            client_id=client.id,
            lead_id=lead.id,
            action="sms_sent",
            channel="sms",
            content_snapshot=content_snapshot,
            metadata={
                "provider_message_id": send_result.sid,
                "touch_number": touch_number,
                "sequence_id": sequence_id,
            },
            created_at=datetime.utcnow(),
        )
        
        db.add(activity)
        await db.flush()
        
        # 5. Update lead
        lead.last_contacted_at = datetime.utcnow()
        lead.touch_count = (lead.touch_count or 0) + 1
        
        return activity
    
    async def _send_via_twilio(
        self,
        to_phone: str,
        from_phone: str,
        message: str,
        client: Client,
    ) -> "TwilioResult":
        """Send via Twilio - existing logic"""
        pass
```

---

## 3. LinkedIn Engine Modifications

### File: `src/engines/linkedin.py`

```python
"""
LinkedIn Engine - Modified for Conversion Intelligence

Changes:
1. Store content_snapshot on activity creation
2. Track message type (connection request, InMail, message)
3. Track touch_number in sequence
"""

from datetime import datetime
from typing import Optional, Literal
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.lead import Lead
from src.models.client import Client

from src.engines.email import extract_pain_points, extract_cta, detect_personalization


MessageType = Literal["connection_request", "inmail", "message"]


class LinkedInEngine:
    """
    Sends LinkedIn messages and tracks content for learning.
    
    MODIFIED: Now captures content_snapshot on every send.
    """
    
    async def send(
        self,
        db: AsyncSession,
        lead: Lead,
        client: Client,
        message: str,
        message_type: MessageType = "message",
        connection_note: Optional[str] = None,
        touch_number: int = 1,
        sequence_id: Optional[str] = None,
    ) -> Activity:
        """
        Send a LinkedIn message and create activity with content snapshot.
        """
        # 1. Send via LinkedIn API/automation
        send_result = await self._send_via_linkedin(
            lead=lead,
            client=client,
            message=message,
            message_type=message_type,
            connection_note=connection_note,
        )
        
        # 2. Determine which text to analyze
        content_to_analyze = connection_note if message_type == "connection_request" else message
        
        # 3. Extract content features
        pain_points = extract_pain_points(content_to_analyze or "")
        cta = extract_cta(content_to_analyze or "")
        personalization = detect_personalization(content_to_analyze or "", lead)
        
        # 4. Build content snapshot
        content_snapshot = {
            # Core content
            "message_type": message_type,
            "body": message,
            "connection_note": connection_note,
            
            # Metrics
            "word_count": len((content_to_analyze or "").split()),
            "char_count": len(content_to_analyze or ""),
            
            # Extracted features
            "pain_points_used": pain_points,
            "cta_used": cta,
            
            # Personalization flags
            **personalization,
            
            # Sequence context
            "touch_number": touch_number,
            "sequence_id": sequence_id,
            
            # Timing
            "sent_at": datetime.utcnow().isoformat(),
            "day_of_week": datetime.utcnow().strftime("%A"),
            "hour_of_day": datetime.utcnow().hour,
        }
        
        # 5. Create activity record
        activity = Activity(
            id=generate_uuid(),
            client_id=client.id,
            lead_id=lead.id,
            action="linkedin_sent",
            channel="linkedin",
            content_snapshot=content_snapshot,
            metadata={
                "message_type": message_type,
                "touch_number": touch_number,
                "sequence_id": sequence_id,
                "linkedin_profile_url": lead.linkedin_url,
            },
            created_at=datetime.utcnow(),
        )
        
        db.add(activity)
        await db.flush()
        
        # 6. Update lead
        lead.last_contacted_at = datetime.utcnow()
        lead.touch_count = (lead.touch_count or 0) + 1
        
        return activity
    
    async def _send_via_linkedin(
        self,
        lead: Lead,
        client: Client,
        message: str,
        message_type: MessageType,
        connection_note: Optional[str],
    ) -> "LinkedInResult":
        """Send via LinkedIn - existing logic"""
        pass
```

---

## 4. Voice Engine Modifications

### File: `src/engines/voice.py`

```python
"""
Voice Engine - Modified for Conversion Intelligence

Changes:
1. Store content_snapshot with call metadata
2. Track script used
3. Store call outcome and duration
"""

from datetime import datetime
from typing import Optional, Literal
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.lead import Lead
from src.models.client import Client

from src.engines.email import extract_pain_points


CallOutcome = Literal[
    "connected", "voicemail", "no_answer", 
    "busy", "wrong_number", "meeting_booked"
]


class VoiceEngine:
    """
    Handles voice calls and tracks content for learning.
    
    MODIFIED: Now captures content_snapshot on call completion.
    """
    
    async def complete_call(
        self,
        db: AsyncSession,
        lead: Lead,
        client: Client,
        script_id: Optional[str] = None,
        script_content: Optional[str] = None,
        outcome: CallOutcome = "connected",
        duration_seconds: int = 0,
        notes: Optional[str] = None,
        touch_number: int = 1,
        sequence_id: Optional[str] = None,
    ) -> Activity:
        """
        Record a completed voice call with content snapshot.
        """
        # 1. Extract features from script if available
        pain_points = []
        if script_content:
            pain_points = extract_pain_points(script_content)
        
        # 2. Build content snapshot
        content_snapshot = {
            # Script info
            "script_id": script_id,
            "script_content": script_content,
            
            # Call metrics
            "outcome": outcome,
            "duration_seconds": duration_seconds,
            "duration_minutes": round(duration_seconds / 60, 1),
            
            # Agent notes
            "notes": notes,
            
            # Extracted features
            "pain_points_used": pain_points,
            
            # Sequence context
            "touch_number": touch_number,
            "sequence_id": sequence_id,
            
            # Timing
            "completed_at": datetime.utcnow().isoformat(),
            "day_of_week": datetime.utcnow().strftime("%A"),
            "hour_of_day": datetime.utcnow().hour,
        }
        
        # 3. Create activity record
        activity = Activity(
            id=generate_uuid(),
            client_id=client.id,
            lead_id=lead.id,
            action="voice_completed",
            channel="voice",
            content_snapshot=content_snapshot,
            metadata={
                "outcome": outcome,
                "duration_seconds": duration_seconds,
                "touch_number": touch_number,
                "sequence_id": sequence_id,
            },
            created_at=datetime.utcnow(),
        )
        
        # 4. Mark as converting if meeting booked
        if outcome == "meeting_booked":
            activity.led_to_booking = True
        
        db.add(activity)
        await db.flush()
        
        # 5. Update lead
        lead.last_contacted_at = datetime.utcnow()
        lead.touch_count = (lead.touch_count or 0) + 1
        
        if outcome == "meeting_booked":
            lead.status = "converted"
        
        return activity
```

---

## 5. Scorer Engine Modifications

### File: `src/engines/scorer.py`

```python
"""
Scorer Engine - Modified for Conversion Intelligence

Changes:
1. Load learned weights from WHO patterns
2. Store als_components snapshot for future learning
3. Track which weights were used
"""

from datetime import datetime
from typing import Optional
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.lead import Lead
from src.models.client import Client
from src.models.conversion_patterns import ConversionPattern


# =============================================================================
# DEFAULT WEIGHTS (used when no learned patterns)
# =============================================================================

DEFAULT_WEIGHTS = {
    "data_quality": 0.20,
    "authority": 0.25,
    "company_fit": 0.25,
    "timing": 0.15,
}

# Component max scores for normalization
COMPONENT_MAX = {
    "data_quality": 20,
    "authority": 25,
    "company_fit": 25,
    "timing": 15,
    "risk": 15,
}


# =============================================================================
# SCORER ENGINE CLASS
# =============================================================================

class ScorerEngine:
    """
    Calculates ALS (Automated Lead Score) for leads.
    
    MODIFIED: 
    - Loads learned weights from conversion patterns
    - Stores component snapshot for future learning
    """
    
    async def score_lead(
        self,
        db: AsyncSession,
        lead: Lead,
        client: Optional[Client] = None,
    ) -> int:
        """
        Calculate ALS score for a lead.
        
        Args:
            db: Database session
            lead: Lead to score
            client: Client (for ICP matching). Loaded if not provided.
            
        Returns:
            Integer score 0-100
        """
        # 1. Load client if not provided
        if client is None:
            client = await self._get_client(db, lead.client_id)
        
        # 2. Load learned weights (or use defaults)
        weights = await self._get_weights(db, client.id)
        
        # 3. Calculate component scores
        data_quality = self._score_data_quality(lead)
        authority = self._score_authority(lead)
        company_fit = self._score_company_fit(lead, client)
        timing = self._score_timing(lead)
        risk = self._score_risk(lead)
        
        # 4. Store component snapshot for learning
        lead.als_components = {
            "data_quality": data_quality,
            "authority": authority,
            "company_fit": company_fit,
            "timing": timing,
            "risk": risk,
            "scored_at": datetime.utcnow().isoformat(),
        }
        
        # 5. Store which weights were used
        lead.als_weights_used = weights
        lead.scored_at = datetime.utcnow()
        
        # 6. Apply weighted formula
        # Normalize each component to 0-1, multiply by weight, scale to 100
        raw_score = (
            (data_quality / COMPONENT_MAX["data_quality"]) * weights["data_quality"] * 100 +
            (authority / COMPONENT_MAX["authority"]) * weights["authority"] * 100 +
            (company_fit / COMPONENT_MAX["company_fit"]) * weights["company_fit"] * 100 +
            (timing / COMPONENT_MAX["timing"]) * weights["timing"] * 100 -
            risk  # Risk is a direct deduction
        )
        
        # 7. Clamp to 0-100
        final_score = int(np.clip(raw_score, 0, 100))
        
        # 8. Update lead
        lead.als_score = final_score
        
        return final_score
    
    async def _get_weights(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> dict:
        """
        Load learned weights from WHO patterns.
        Falls back to defaults if not available.
        """
        # Check for WHO pattern
        query = select(ConversionPattern).where(
            ConversionPattern.client_id == client_id,
            ConversionPattern.pattern_type == "who",
            ConversionPattern.valid_until > datetime.utcnow(),
        )
        result = await db.execute(query)
        pattern = result.scalar_one_or_none()
        
        if pattern and pattern.patterns:
            recommended = pattern.patterns.get("recommended_weights")
            if recommended:
                # Validate weights
                if self._validate_weights(recommended):
                    return recommended
        
        # Fallback to client-stored weights
        client = await self._get_client(db, client_id)
        if client.als_learned_weights:
            if self._validate_weights(client.als_learned_weights):
                return client.als_learned_weights
        
        return DEFAULT_WEIGHTS
    
    def _validate_weights(self, weights: dict) -> bool:
        """Validate weight dictionary"""
        required_keys = ["data_quality", "authority", "company_fit", "timing"]
        
        # Check all keys present
        if not all(k in weights for k in required_keys):
            return False
        
        # Check values are reasonable
        for key in required_keys:
            value = weights[key]
            if not isinstance(value, (int, float)):
                return False
            if value < 0.05 or value > 0.50:
                return False
        
        # Check sum is close to 0.85
        total = sum(weights[k] for k in required_keys)
        if not (0.80 <= total <= 0.90):
            return False
        
        return True
    
    # =========================================================================
    # COMPONENT SCORING (existing logic, included for completeness)
    # =========================================================================
    
    def _score_data_quality(self, lead: Lead) -> int:
        """Score based on data completeness and verification"""
        score = 0
        
        # Email verification (0-8 points)
        if lead.email_verified:
            score += 8
        elif lead.email:
            score += 4
        
        # Phone (0-6 points)
        if lead.phone_verified:
            score += 6
        elif lead.phone:
            score += 3
        
        # LinkedIn (0-4 points)
        if lead.linkedin_url:
            score += 4
        
        # Personal email flag (0-2 points)
        if lead.is_personal_email:
            score += 2
        
        return min(score, COMPONENT_MAX["data_quality"])
    
    def _score_authority(self, lead: Lead) -> int:
        """Score based on job title/seniority"""
        title = (lead.title or "").lower()
        
        # Owner/Founder
        if any(t in title for t in ["owner", "founder", "co-founder", "partner"]):
            return 25
        
        # C-Suite
        if any(t in title for t in ["ceo", "cfo", "cmo", "coo", "cto", "chief"]):
            return 22
        
        # VP
        if "vp" in title or "vice president" in title:
            return 18
        
        # Director
        if "director" in title:
            return 15
        
        # Head of
        if "head of" in title or "head" in title:
            return 12
        
        # Manager
        if "manager" in title:
            if "senior" in title:
                return 10
            return 7
        
        # Default
        return 5
    
    def _score_company_fit(self, lead: Lead, client: Client) -> int:
        """Score based on ICP match"""
        score = 0
        icp = client.icp or {}
        
        # Industry match (0-10 points)
        target_industries = icp.get("industries", [])
        if lead.industry and lead.industry in target_industries:
            score += 10
        
        # Company size (0-8 points)
        target_min = icp.get("employee_min", 5)
        target_max = icp.get("employee_max", 50)
        if lead.employee_count:
            if target_min <= lead.employee_count <= target_max:
                score += 8
            elif lead.employee_count < target_min * 2:
                score += 4
        
        # Location (0-7 points)
        target_countries = icp.get("countries", ["Australia"])
        if lead.country and lead.country in target_countries:
            score += 7
        
        return min(score, COMPONENT_MAX["company_fit"])
    
    def _score_timing(self, lead: Lead) -> int:
        """Score based on timing signals"""
        score = 0
        
        # New role < 6 months (0-6 points)
        if lead.is_new_role:
            score += 6
        
        # Hiring signals (0-5 points)
        if lead.is_hiring:
            score += 5
        
        # Recent funding (0-4 points)
        if lead.recently_funded:
            score += 4
        
        return min(score, COMPONENT_MAX["timing"])
    
    def _score_risk(self, lead: Lead) -> int:
        """Calculate risk deductions"""
        deductions = 0
        
        # Previous bounce
        if lead.has_bounced:
            deductions += 15
        
        # Unsubscribed
        if lead.is_unsubscribed:
            deductions += 15
        
        # Competitor
        if lead.is_competitor:
            deductions += 10
        
        # Do not contact
        if lead.do_not_contact:
            deductions += 50
        
        return min(deductions, COMPONENT_MAX["risk"])
    
    async def _get_client(self, db: AsyncSession, client_id: str) -> Client:
        """Load client by ID"""
        result = await db.execute(
            select(Client).where(Client.id == client_id)
        )
        return result.scalar_one()
```

---

## 6. Allocator Engine Modifications

### File: `src/engines/allocator.py`

```python
"""
Allocator Engine - Modified for Conversion Intelligence

Changes:
1. Load WHEN patterns for optimal timing
2. Load HOW patterns for channel selection
3. Make data-driven allocation decisions
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.lead import Lead
from src.models.client import Client
from src.models.conversion_patterns import ConversionPattern


# =============================================================================
# DEFAULT PATTERNS (used when no learned patterns)
# =============================================================================

DEFAULT_SEQUENCE = ["email", "linkedin", "email", "sms", "voice", "email"]

DEFAULT_GAPS = {
    "touch_1_to_2": 2,
    "touch_2_to_3": 3,
    "touch_3_to_4": 4,
    "touch_4_to_5": 5,
    "touch_5_to_6": 7,
}

DEFAULT_BEST_DAYS = [1, 2, 3]  # Tuesday, Wednesday, Thursday (0=Monday)
DEFAULT_BEST_HOURS = [10, 14, 9]  # 10am, 2pm, 9am


# =============================================================================
# ALLOCATOR ENGINE CLASS
# =============================================================================

class AllocatorEngine:
    """
    Allocates leads to sequences and schedules touches.
    
    MODIFIED:
    - Uses WHEN patterns for timing optimization
    - Uses HOW patterns for channel selection
    """
    
    async def allocate_lead(
        self,
        db: AsyncSession,
        lead: Lead,
        client: Client,
        sequence_override: Optional[List[dict]] = None,
    ) -> dict:
        """
        Allocate a lead to a sequence with optimized timing.
        
        Returns allocation plan with channel sequence and scheduled times.
        """
        # 1. Load patterns
        when_patterns = await self._load_patterns(db, client.id, "when")
        how_patterns = await self._load_patterns(db, client.id, "how")
        
        # 2. Determine channel sequence
        if sequence_override:
            sequence = sequence_override
        else:
            sequence = self._build_sequence(lead, how_patterns)
        
        # 3. Schedule touches with optimal timing
        scheduled_touches = self._schedule_sequence(
            sequence=sequence,
            when_patterns=when_patterns,
            lead=lead,
        )
        
        return {
            "lead_id": lead.id,
            "sequence": sequence,
            "scheduled_touches": scheduled_touches,
            "patterns_used": {
                "when": when_patterns is not None,
                "how": how_patterns is not None,
            },
        }
    
    async def _load_patterns(
        self,
        db: AsyncSession,
        client_id: str,
        pattern_type: str,
    ) -> Optional[dict]:
        """Load patterns from database"""
        query = select(ConversionPattern).where(
            ConversionPattern.client_id == client_id,
            ConversionPattern.pattern_type == pattern_type,
            ConversionPattern.valid_until > datetime.utcnow(),
        )
        result = await db.execute(query)
        pattern = result.scalar_one_or_none()
        
        if pattern:
            return pattern.patterns
        return None
    
    def _build_sequence(
        self,
        lead: Lead,
        how_patterns: Optional[dict],
    ) -> List[dict]:
        """
        Build channel sequence based on patterns and lead tier.
        """
        # Determine lead tier
        als_tier = self._get_als_tier(lead.als_score or 50)
        
        # Start with default or winning sequence
        if how_patterns and how_patterns.get("winning_sequences"):
            top_sequence = how_patterns["winning_sequences"][0]["sequence"]
            channels = top_sequence[:6]
        else:
            channels = DEFAULT_SEQUENCE.copy()
        
        # Adjust first channel based on patterns
        if how_patterns and how_patterns.get("best_first_channel"):
            channels[0] = how_patterns["best_first_channel"]
        
        # Adjust for tier
        if als_tier == "hot" and how_patterns:
            tier_data = how_patterns.get("channel_effectiveness_by_tier", {}).get("hot", {})
            if tier_data.get("voice", {}).get("conversion_rate", 0) > 0.15:
                # Insert voice earlier for hot leads
                if len(channels) > 3 and "voice" not in channels[:3]:
                    channels[2] = "voice"
        
        # Build sequence with touch numbers
        sequence = []
        for i, channel in enumerate(channels):
            sequence.append({
                "touch_number": i + 1,
                "channel": channel,
            })
        
        return sequence
    
    def _schedule_sequence(
        self,
        sequence: List[dict],
        when_patterns: Optional[dict],
        lead: Lead,
    ) -> List[dict]:
        """
        Schedule all touches with optimal timing.
        """
        # Get timing preferences
        if when_patterns:
            gaps = when_patterns.get("optimal_sequence_gaps", DEFAULT_GAPS)
            best_days = [
                d["day_index"] 
                for d in when_patterns.get("best_days", [])[:3]
            ] or DEFAULT_BEST_DAYS
            best_hours = [
                h["hour"] 
                for h in when_patterns.get("best_hours", [])[:3]
            ] or DEFAULT_BEST_HOURS
        else:
            gaps = DEFAULT_GAPS
            best_days = DEFAULT_BEST_DAYS
            best_hours = DEFAULT_BEST_HOURS
        
        # Schedule first touch
        now = datetime.utcnow()
        first_time = self._find_next_slot(now, best_days, best_hours)
        
        scheduled = []
        prev_time = first_time
        
        for touch in sequence:
            touch_num = touch["touch_number"]
            
            if touch_num == 1:
                scheduled_time = first_time
            else:
                # Get gap from previous touch
                gap_key = f"touch_{touch_num - 1}_to_{touch_num}"
                gap_days = gaps.get(gap_key, 3)
                
                # Add gap and find optimal slot
                base_time = prev_time + timedelta(days=gap_days)
                scheduled_time = self._find_next_slot(base_time, best_days, best_hours)
            
            scheduled.append({
                **touch,
                "scheduled_at": scheduled_time.isoformat(),
                "day_of_week": scheduled_time.strftime("%A"),
                "hour": scheduled_time.hour,
            })
            
            prev_time = scheduled_time
        
        return scheduled
    
    def _find_next_slot(
        self,
        base_time: datetime,
        preferred_days: List[int],
        preferred_hours: List[int],
    ) -> datetime:
        """
        Find next available slot matching preferences.
        """
        # Start from base time
        candidate = base_time.replace(
            hour=preferred_hours[0] if preferred_hours else 10,
            minute=0,
            second=0,
            microsecond=0,
        )
        
        # If candidate is in the past, move to next day
        if candidate <= base_time:
            candidate += timedelta(days=1)
        
        # Find next preferred day
        max_attempts = 14  # Look up to 2 weeks ahead
        for _ in range(max_attempts):
            if candidate.weekday() in preferred_days:
                # Skip weekends unless preferred
                if candidate.weekday() < 5 or candidate.weekday() in preferred_days:
                    return candidate
            candidate += timedelta(days=1)
        
        # Fallback: just return next business day
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        
        return candidate
    
    def _get_als_tier(self, score: int) -> str:
        """Map ALS score to tier"""
        if score >= 80:
            return "hot"
        elif score >= 50:
            return "warm"
        else:
            return "cool"
```

---

## 7. Shared Utilities Module

### File: `src/engines/content_utils.py`

```python
"""
Shared utilities for content extraction across engines.

Centralizes:
- Pain point extraction
- CTA extraction
- Personalization detection
"""

import re
from typing import Optional, List

from src.models.lead import Lead


# =============================================================================
# VOCABULARIES (must match WHAT Detector)
# =============================================================================

PAIN_POINT_KEYWORDS = {
    "leads": [
        "leads", "pipeline", "prospects", "opportunities", 
        "qualified", "mql", "sql", "inbound"
    ],
    "revenue": [
        "revenue", "sales", "growth", "roi", "profit", 
        "income", "deals", "closed", "won"
    ],
    "time": [
        "time", "hours", "manual", "automate", "efficiency", 
        "busy", "bandwidth", "overwhelmed", "tedious"
    ],
    "scaling": [
        "scale", "scaling", "growth", "capacity", "bandwidth", 
        "hire", "team", "expand", "growing"
    ],
    "competition": [
        "competitors", "competition", "market share", "behind", 
        "catching up", "losing", "threat"
    ],
    "cost": [
        "cost", "expensive", "budget", "waste", "spending", 
        "save", "afford", "price", "investment"
    ],
    "quality": [
        "quality", "results", "performance", "outcomes", 
        "better", "improve", "consistent"
    ],
    "clients": [
        "clients", "customers", "retention", "churn", 
        "satisfaction", "referrals", "testimonials"
    ],
}

CTA_PATTERNS = [
    "open to a quick chat",
    "worth 15 minutes",
    "worth a conversation",
    "free audit",
    "free analysis",
    "quick call",
    "schedule a call",
    "book a time",
    "interested in learning",
    "happy to share",
    "let me know",
    "thoughts?",
    "make sense to connect",
    "grab 15 minutes",
    "coffee chat",
]


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_pain_points(text: str) -> List[str]:
    """
    Extract pain points mentioned in text.
    Returns list of pain point categories found.
    """
    if not text:
        return []
    
    text_lower = text.lower()
    found = []
    
    for pain_point, keywords in PAIN_POINT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                found.append(pain_point)
                break  # Only count each pain point once
    
    return found


def extract_cta(text: str) -> Optional[str]:
    """
    Extract call-to-action from text.
    Returns the CTA phrase if found, None otherwise.
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    for cta in CTA_PATTERNS:
        if cta in text_lower:
            return cta
    
    return None


def detect_personalization(text: str, lead: Lead) -> dict:
    """
    Detect personalization elements in message.
    Returns dict of boolean flags.
    """
    if not text:
        return {
            "has_company_mention": False,
            "has_first_name": False,
            "has_recent_news": False,
            "has_mutual_connection": False,
            "has_industry_specific": False,
        }
    
    text_lower = text.lower()
    
    return {
        "has_company_mention": (
            lead.company_name.lower() in text_lower 
            if lead.company_name else False
        ),
        "has_first_name": (
            lead.first_name.lower() in text_lower 
            if lead.first_name else False
        ),
        "has_recent_news": bool(
            re.search(
                r"(noticed|saw|congrats|congratulations|just saw|read about)", 
                text_lower
            )
        ),
        "has_mutual_connection": (
            "mutual" in text_lower or 
            "connection" in text_lower or
            "referred" in text_lower or
            "introduced" in text_lower
        ),
        "has_industry_specific": (
            lead.industry.lower() in text_lower 
            if lead.industry else False
        ),
    }


def build_content_snapshot(
    body: str,
    lead: Lead,
    subject: Optional[str] = None,
    touch_number: int = 1,
    sequence_id: Optional[str] = None,
    channel: str = "email",
) -> dict:
    """
    Build a complete content snapshot for any channel.
    
    This is the standard format stored in activity.content_snapshot.
    """
    from datetime import datetime
    
    pain_points = extract_pain_points(body)
    cta = extract_cta(body)
    personalization = detect_personalization(body, lead)
    
    snapshot = {
        # Core content
        "body": body,
        "channel": channel,
        
        # Metrics
        "word_count": len(body.split()) if body else 0,
        "char_count": len(body) if body else 0,
        
        # Extracted features
        "pain_points_used": pain_points,
        "cta_used": cta,
        
        # Personalization flags
        **personalization,
        
        # Sequence context
        "touch_number": touch_number,
        "sequence_id": sequence_id,
        
        # Timing
        "sent_at": datetime.utcnow().isoformat(),
        "day_of_week": datetime.utcnow().strftime("%A"),
        "hour_of_day": datetime.utcnow().hour,
    }
    
    # Add subject for email
    if subject is not None:
        snapshot["subject"] = subject
        snapshot["subject_word_count"] = len(subject.split())
    
    return snapshot
```

---

## Tasks

| Task | Description | File(s) | Est. Hours |
|------|-------------|---------|------------|
| 16E.1 | Create shared content_utils module | `src/engines/content_utils.py` | 1 |
| 16E.2 | Modify Email engine with content capture | `src/engines/email.py` | 1.5 |
| 16E.3 | Modify SMS + LinkedIn + Voice engines | `src/engines/sms.py`, `linkedin.py`, `voice.py` | 2 |
| 16E.4 | Modify Scorer engine with pattern consumption | `src/engines/scorer.py` | 1.5 |
| 16E.5 | Modify Allocator engine with pattern consumption | `src/engines/allocator.py` | 2 |

**Total: 5 tasks, ~8 hours**

---

## Testing

```python
# tests/engines/test_content_utils.py

import pytest
from src.engines.content_utils import (
    extract_pain_points,
    extract_cta,
    detect_personalization,
    build_content_snapshot,
)

class TestContentUtils:
    
    def test_extract_pain_points(self):
        text = "Struggling to generate enough qualified leads for your pipeline?"
        result = extract_pain_points(text)
        
        assert "leads" in result
    
    def test_extract_multiple_pain_points(self):
        text = "Save time and generate more revenue with automation"
        result = extract_pain_points(text)
        
        assert "time" in result
        assert "revenue" in result
    
    def test_extract_cta(self):
        text = "Would you be open to a quick chat next week?"
        result = extract_cta(text)
        
        assert result == "open to a quick chat"
    
    def test_detect_personalization(self):
        lead = MockLead(
            company_name="Acme Corp",
            first_name="John",
            industry="Dental",
        )
        text = "Hi John, I noticed Acme Corp is growing rapidly in the Dental space"
        
        result = detect_personalization(text, lead)
        
        assert result["has_company_mention"] == True
        assert result["has_first_name"] == True
        assert result["has_recent_news"] == True
        assert result["has_industry_specific"] == True
    
    def test_build_content_snapshot(self):
        lead = MockLead(company_name="Test Co", first_name="Jane")
        
        snapshot = build_content_snapshot(
            body="Hi Jane, quick question about Test Co",
            lead=lead,
            subject="Quick question",
            touch_number=2,
            channel="email",
        )
        
        assert snapshot["subject"] == "Quick question"
        assert snapshot["touch_number"] == 2
        assert snapshot["has_company_mention"] == True
        assert snapshot["has_first_name"] == True
        assert "sent_at" in snapshot


# tests/engines/test_scorer.py

class TestScorerEngine:
    
    @pytest.mark.asyncio
    async def test_uses_learned_weights(self):
        """Scorer should use learned weights when available"""
        # Setup: Create pattern with custom weights
        pattern = ConversionPattern(
            client_id="test-client",
            pattern_type="who",
            patterns={
                "recommended_weights": {
                    "data_quality": 0.10,
                    "authority": 0.15,
                    "company_fit": 0.40,
                    "timing": 0.20,
                }
            },
            valid_until=datetime.utcnow() + timedelta(days=7),
        )
        
        # Score a lead
        scorer = ScorerEngine()
        score = await scorer.score_lead(db, lead, client)
        
        # Verify weights were used
        assert lead.als_weights_used["company_fit"] == 0.40
    
    @pytest.mark.asyncio
    async def test_falls_back_to_defaults(self):
        """Scorer should use defaults when no patterns"""
        scorer = ScorerEngine()
        score = await scorer.score_lead(db, lead, client)
        
        assert lead.als_weights_used == DEFAULT_WEIGHTS
```

---

**End of Phase 16E Specification**
