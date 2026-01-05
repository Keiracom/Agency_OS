# Database: Conversion Patterns

**Migration:** `014_conversion_intelligence.sql`  
**Phase:** 16 (Conversion Intelligence)

---

## Conversion Patterns Table

```sql
CREATE TABLE conversion_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    pattern_type TEXT NOT NULL,  -- 'who', 'what', 'when', 'how'
    
    -- Pattern data (varies by type)
    pattern_data JSONB NOT NULL,
    
    -- Confidence metrics
    sample_size INTEGER NOT NULL,
    confidence FLOAT NOT NULL,  -- 0.0 to 1.0
    
    -- Validity
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_pattern_type CHECK (
        pattern_type IN ('who', 'what', 'when', 'how')
    )
);

CREATE INDEX idx_patterns_client_type ON conversion_patterns(client_id, pattern_type);
CREATE INDEX idx_patterns_active ON conversion_patterns(is_active) WHERE is_active = TRUE;
```

---

## Pattern Types

### WHO Pattern (Scorer optimization)

```json
{
    "optimized_weights": {
        "data_quality": 0.15,
        "authority": 0.35,
        "company_fit": 0.25,
        "timing": 0.15,
        "risk": 0.10
    },
    "significant_factors": [
        {"factor": "title_ceo_founder", "lift": 2.3},
        {"factor": "industry_digital_marketing", "lift": 1.8}
    ]
}
```

### WHAT Pattern (Content optimization)

```json
{
    "effective_subjects": [
        {"pattern": "question_format", "open_rate": 0.45},
        {"pattern": "personalized_company", "open_rate": 0.42}
    ],
    "effective_ctas": [
        {"type": "soft_ask", "conversion_rate": 0.12},
        {"type": "direct_meeting", "conversion_rate": 0.08}
    ],
    "optimal_length": {
        "email": {"min": 75, "max": 125},
        "linkedin": {"min": 50, "max": 100}
    },
    "pain_points": ["scaling", "lead_quality", "time_to_close"]
}
```

### WHEN Pattern (Timing optimization)

```json
{
    "optimal_days": ["tuesday", "wednesday", "thursday"],
    "optimal_hours": [9, 10, 14, 15],
    "timezone": "Australia/Sydney",
    "avoid": {
        "days": ["monday_morning", "friday_afternoon"],
        "hours": [12, 13]
    }
}
```

### HOW Pattern (Channel sequence optimization)

```json
{
    "winning_sequences": [
        {
            "sequence": ["email", "linkedin", "email", "voice"],
            "conversion_rate": 0.15,
            "avg_touches": 3.2
        }
    ],
    "channel_effectiveness": {
        "email": {"opens": 0.35, "replies": 0.08},
        "linkedin": {"accepts": 0.25, "replies": 0.12},
        "voice": {"answers": 0.15, "meetings": 0.08}
    }
}
```

---

## Conversion Pattern History

```sql
CREATE TABLE conversion_pattern_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_id UUID NOT NULL REFERENCES conversion_patterns(id),
    pattern_data JSONB NOT NULL,
    sample_size INTEGER NOT NULL,
    confidence FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pattern_history ON conversion_pattern_history(pattern_id, created_at DESC);
```

---

## Confidence Thresholds

| Threshold | Meaning | Action |
|-----------|---------|--------|
| < 0.5 | Low confidence | Use defaults |
| 0.5 - 0.7 | Medium confidence | Blend with defaults |
| > 0.7 | High confidence | Use learned weights |

---

## Minimum Sample Sizes

| Pattern Type | Minimum Samples | For Confidence > 0.7 |
|--------------|-----------------|----------------------|
| WHO | 30 conversions | 50+ conversions |
| WHAT | 50 sends | 100+ sends |
| WHEN | 30 conversions | 50+ conversions |
| HOW | 30 conversions | 50+ conversions |
