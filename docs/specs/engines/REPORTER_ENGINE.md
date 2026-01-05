# Reporter Engine — Metrics Aggregation

**File:** `src/engines/reporter.py`  
**Purpose:** Aggregate and report campaign metrics  
**Layer:** 3 - engines

---

## Metrics Categories

### Campaign Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| leads_total | Total leads in campaign | COUNT(leads) |
| leads_enriched | Successfully enriched | COUNT(status >= enriched) |
| leads_contacted | At least 1 touch | COUNT(activities) DISTINCT lead_id |
| leads_converted | Booked meeting | COUNT(status = converted) |
| conversion_rate | % converted | converted / contacted |

### Channel Metrics

| Metric | Description |
|--------|-------------|
| emails_sent | Total emails sent |
| emails_opened | Unique opens |
| emails_clicked | Unique clicks |
| emails_replied | Replies received |
| open_rate | opened / sent |
| click_rate | clicked / sent |
| reply_rate | replied / sent |

### ALS Distribution

| Metric | Description |
|--------|-------------|
| hot_count | Leads with ALS 85-100 |
| warm_count | Leads with ALS 60-84 |
| cool_count | Leads with ALS 35-59 |
| cold_count | Leads with ALS 20-34 |
| dead_count | Leads with ALS <20 |

---

## Report Types

### Campaign Report

```python
class CampaignReport(BaseModel):
    campaign_id: UUID
    period: str  # daily, weekly, monthly, all_time
    
    # Overview
    leads_total: int
    leads_enriched: int
    leads_contacted: int
    leads_converted: int
    conversion_rate: float
    
    # By channel
    channel_metrics: dict[ChannelType, ChannelMetrics]
    
    # ALS distribution
    als_distribution: ALSDistribution
    
    # Trends
    daily_activity: list[DailyMetrics]
```

### Client Report

```python
class ClientReport(BaseModel):
    client_id: UUID
    period: str
    
    # Across all campaigns
    total_leads: int
    total_converted: int
    credits_used: int
    credits_remaining: int
    
    # Campaign breakdown
    campaigns: list[CampaignSummary]
    
    # Top performers
    best_converting_campaign: UUID
    best_converting_channel: ChannelType
```

### Admin Report (Platform-wide)

```python
class AdminReport(BaseModel):
    period: str
    
    # Platform metrics
    total_clients: int
    active_clients: int
    total_leads_processed: int
    total_conversions: int
    
    # Revenue
    mrr: float
    arr: float
    
    # By tier
    ignition_clients: int
    velocity_clients: int
    dominance_clients: int
```

---

## API

```python
class ReporterEngine:
    async def campaign_report(
        self,
        db: AsyncSession,
        campaign_id: UUID,
        period: str = "all_time"
    ) -> CampaignReport:
        """Generate campaign performance report."""
        ...
    
    async def client_report(
        self,
        db: AsyncSession,
        client_id: UUID,
        period: str = "monthly"
    ) -> ClientReport:
        """Generate client-level report."""
        ...
    
    async def admin_report(
        self,
        db: AsyncSession,
        period: str = "monthly"
    ) -> AdminReport:
        """Generate platform-wide admin report."""
        ...
    
    async def export_csv(
        self,
        report: CampaignReport | ClientReport
    ) -> bytes:
        """Export report as CSV."""
        ...
```

---

## Caching

Reports are cached for performance:

| Report Type | Cache TTL |
|-------------|-----------|
| Campaign (daily) | 1 hour |
| Campaign (weekly) | 6 hours |
| Client | 1 hour |
| Admin | 15 minutes |
