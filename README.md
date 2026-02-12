# Siege Waterfall - ABN→GMB Name Resolution

Implementation of **CEO Directive #014** to improve GMB match rates from 85% to 90%+ through waterfall name resolution.

## Overview

The Siege Waterfall system processes Australian Business Number (ABN) records and attempts to find matching Google My Business (GMB) listings using a multi-step waterfall approach with comprehensive logging for production monitoring.

## Architecture

```
ABN Record → Generic Filter → Waterfall Search → GMB Match → Logging
```

### Waterfall Steps

1. **Step A**: ASIC business names from `business_names[]` array (try each)
2. **Step B**: ABN `trading_name` (pre-2012 legacy)  
3. **Step C**: Legal name (`business_name`) stripped of "Pty Ltd"/"Ltd"/"Pty"
4. **Step D**: Location-pinned search: name + postcode + state + "Australia"

### Generic Pattern Filter

Businesses with empty `business_names[]` AND legal names matching these patterns skip Tier 2:
- Holdings, Enterprises, Investments, Trust, Group, Services, Management, Properties, Consulting

These leads are logged as `tier2_skipped_generic_name` and continue to Tier 3.

## Core Components

### `ABNRecord`
Data structure representing ABN bulk extract fields:
```python
@dataclass
class ABNRecord:
    abn: str
    business_name: str          # Legal name
    business_names: List[str]   # ASIC-registered names (since 2012)
    trading_name: Optional[str] # Legacy pre-2012 trading names
    postcode: Optional[str]
    state: Optional[str]
```

### `Tier2GMBEnricher`
Executes waterfall search with comprehensive logging:
- Processes ABN records through generic filter
- Runs waterfall name resolution
- Logs every attempt to `tier2_gmb_match_log` table
- Returns enriched GMB data on successful match

### `SiegeWaterfall`
Main orchestrator for the entire pipeline:
- Initializes Supabase and GMB clients
- Processes leads end-to-end
- Returns enriched lead data

## Database Schema

### `tier2_gmb_match_log`
Tracks every GMB search attempt for production monitoring:

| Column | Type | Description |
|--------|------|-------------|
| `abn` | VARCHAR(11) | Australian Business Number |
| `abn_name` | TEXT | Original business name |
| `search_name_used` | TEXT | Actual search term used |
| `waterfall_step` | VARCHAR(10) | Step identifier (a/b/c/d) |
| `gmb_result` | VARCHAR(20) | found/not_found |
| `match_score` | DECIMAL(3,2) | Quality score (0.0-1.0) |
| `pass_fail` | VARCHAR(10) | pass/fail |
| `timestamp` | TIMESTAMPTZ | Search timestamp |

## Usage

### Basic Usage
```python
from siege_waterfall import SiegeWaterfall

# Initialize with Supabase credentials
waterfall = SiegeWaterfall(
    supabase_url="your-supabase-url",
    supabase_key="your-supabase-key"
)

# Process a lead
lead_data = {
    'abn': '12345678901',
    'business_name': 'Example Business Pty Ltd',
    'business_names': ['Example Services', 'ExampleCorp'],
    'trading_name': 'Example Trading',
    'postcode': '2000',
    'state': 'NSW'
}

result = waterfall.process_lead(lead_data)
print(result['tier2_status'])  # tier2_gmb_found/tier2_gmb_not_found/tier2_skipped_generic_name
```

### Environment Variables
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-supabase-anon-key"
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run database migration:
```bash
# Execute migrations/001_create_tier2_gmb_match_log.sql in your Supabase dashboard
```

3. Configure environment variables

## Testing

```bash
# Run the main function with test data
python siege_waterfall.py

# Run tests (when implemented)
pytest tests/
```

## Monitoring & Analytics

The `tier2_gmb_match_log` table enables production monitoring:

### Match Rate Analysis
```sql
SELECT 
  waterfall_step,
  COUNT(*) as attempts,
  COUNT(*) FILTER (WHERE gmb_result = 'found') as successes,
  ROUND(100.0 * COUNT(*) FILTER (WHERE gmb_result = 'found') / COUNT(*), 2) as match_rate_pct
FROM tier2_gmb_match_log 
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY waterfall_step
ORDER BY waterfall_step;
```

### Overall Performance
```sql
SELECT 
  DATE(timestamp) as date,
  COUNT(DISTINCT abn) as unique_abns_processed,
  COUNT(*) as total_attempts,
  COUNT(*) FILTER (WHERE gmb_result = 'found') as successful_matches,
  ROUND(100.0 * COUNT(*) FILTER (WHERE gmb_result = 'found') / COUNT(DISTINCT abn), 2) as overall_match_rate_pct
FROM tier2_gmb_match_log 
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

## Implementation Notes

### Name Processing
- Legal entity suffixes are intelligently stripped: "Pty Ltd", "Ltd", "Pty", etc.
- Location-pinned searches add postcode + state + "Australia" for better targeting
- Match scores calculated using token-based similarity

### Generic Filtering
- Applied only when `business_names[]` is empty (no ASIC business names)
- Prevents low-value searches for generic holding companies
- Logged separately for tracking filter effectiveness

### Logging Strategy
- Every GMB search attempt is logged regardless of success/failure
- Match scores captured for quality analysis
- Waterfall step tracking enables optimization of search order
- Fallback to local logging if Supabase unavailable

## Law Compliance

- **LAW I-A**: ✅ Actual files examined before modification
- **LAW VIII**: ✅ Implementation ready for PR creation, Dave merges

## CEO Directive #014 Status

✅ **Implemented**: Waterfall name resolution (steps a-d)  
✅ **Implemented**: Generic pattern filter with logging  
✅ **Implemented**: Comprehensive match rate instrumentation  
✅ **Implemented**: Database schema and migration  
✅ **Ready**: For PR submission with governance trace  

## Next Steps

1. Review and test implementation
2. Configure GMB API client integration
3. Deploy to staging environment
4. Monitor match rate improvements
5. Iterate based on production metrics

---

*Implements CEO Directive #014 - ABN→GMB Waterfall Name Resolution*