# KEI-17 Pre-Research — 4 Check Categories: APIs + Response Shapes + Helper Signatures

For each of Dave's check categories, this doc lists: the call that produces the data, the response shape Aiden needs to parse, and a pre-built helper signature.

## Check 1 — `bd ready` → dispatch

**Tool:** `bd` CLI at `/home/elliotbot/.local/bin/bd`.

**Command (claim-on-find variant):**
```bash
bd ready --claim --json
```
Atomically claims and returns one ready issue, OR exits non-zero / empty array if nothing claimable.

**Survey-only variant:**
```bash
bd list --ready --json
```
Returns array; no side-effects.

**Response shape** (verified live 2026-05-12):
```python
{
  "id": "Agency_OS-qz9",                # bd issue id (local namespace)
  "title": "Cognee Universal Memory Layer — Phase 0 (Install + Verify)",
  "description": "Linear: https://linear.app/keiracom/issue/KEI-5\nState (at sync): In Progress",
  "status": "open",                     # vs "in_progress" / "blocked" / "closed"
  "priority": 0,                        # int, lower = higher
  "issue_type": "task",
  "owner": "elliotbot@keiracom.com",
  "external_ref": "https://linear.app/keiracom/issue/KEI-5",  # parseable for KEI id
  "dependency_count": 0,                # 0 = unblocked
  "dependent_count": 1,
  "updated_at": "2026-05-12T06:43:47Z"
}
```

**Helper signature:**
```python
def get_ready_to_dispatch(limit: int = 5) -> list[dict]:
    """Returns up to `limit` ready (unblocked, not in-progress) bd issues."""
```

## Check 2 — Linear stale → surface

**Tool:** Linear GraphQL API. Auth header `Authorization: $LINEAR_API_KEY` (already in `.env`).

**Query (issues "In Progress" with no update in 24h):**
```graphql
query StaleInProgress($staleBefore: DateTime!) {
  issues(filter: {
    state: { name: { eq: "In Progress" } }
    updatedAt: { lt: $staleBefore }
  }, first: 50) {
    nodes {
      id identifier title updatedAt
      assignee { name email }
      state { name }
      url
    }
  }
}
```

**Response shape:**
```python
{
  "data": {"issues": {"nodes": [
    {"id": "...", "identifier": "KEI-17", "title": "...",
     "updatedAt": "2026-05-11T12:00:00Z",
     "assignee": {"name": "Aiden", "email": "..."},
     "url": "https://linear.app/keiracom/issue/KEI-17"}
  ]}}
}
```

**Helper signature:**
```python
def get_stale_linear_issues(hours_threshold: int = 24) -> list[dict]:
    """Returns Linear issues in 'In Progress' with updatedAt older than threshold."""
```

## Check 3 — idle agents → assign

**Tool:** Existing 15-min collector at `keiracom-admin-collector/collect_agent_status.py` writes `keiracom_admin.agent_status_observations`. Read, don't reimplement.

**SQL:**
```sql
SELECT DISTINCT ON (callsign) callsign, last_activity_at, last_pr_url
FROM keiracom_admin.agent_status_observations
WHERE callsign IN ('aiden','elliot','max','atlas','orion','scout')
ORDER BY callsign, observed_at DESC;
```

**Response shape (per-callsign):** `{callsign: str, last_activity_at: datetime|None, last_pr_url: str|None}`.

**Idle threshold:** treat `last_activity_at < now - INTERVAL '30 min'` as idle. (15-min collector cadence + 15-min jitter buffer = 30 min is the smallest threshold that won't false-positive on collector lag.)

**Helper signature:**
```python
def get_idle_agents(idle_minutes: int = 30) -> list[str]:
    """Returns callsigns whose latest activity timestamp is older than `idle_minutes`."""
```

## Check 4 — Prefect failures → incident

**Tool:** MCP `prefect` server, `mcp__prefect__get_flow_runs` with state filter.

**Args:**
```python
{
  "state": {"type": {"any_": ["FAILED", "CRASHED"]}},
  "expected_start_time": {"after_": "2026-05-12T05:00:00Z"},  # last hour
  "limit": 20,
  "sort": "EXPECTED_START_TIME_DESC"
}
```

**Response shape (per run):**
```python
{
  "id": "uuid", "name": "<flow>-<run>", "flow_id": "uuid",
  "state": {"type": "FAILED", "name": "Failed", "message": "..."},
  "start_time": "2026-05-12T05:23:00Z",
  "deployment_id": "uuid", "infrastructure_pid": "..."
}
```

**Helper signature:**
```python
def get_recent_prefect_failures(lookback_minutes: int = 60) -> list[dict]:
    """Returns failed/crashed flow runs in the lookback window. Empty list if none."""
```

## Dedup + idempotency

Each helper should write the set of IDs it surfaced to `~/.local/state/elliot-polling-loop.json` keyed by check name. Skip any ID already surfaced in the previous tick. Reset the file when the corresponding bd issue closes or Linear issue moves out of "In Progress".

```python
def already_surfaced(check_name: str, ids: set[str]) -> set[str]: ...
def mark_surfaced(check_name: str, ids: set[str]) -> None: ...
```

Net call surface: 6 helpers + 2 dedup utilities. ~150-200 LOC for the loop itself.
