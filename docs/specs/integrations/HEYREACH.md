# HeyReach Integration

**File:** `src/integrations/heyreach.py`  
**Purpose:** LinkedIn automation  
**API Docs:** https://docs.heyreach.io/

---

## Capabilities

- LinkedIn connection requests
- LinkedIn messaging
- Profile viewing
- Proxy rotation (avoid detection)
- Webhook callbacks

---

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /campaigns` | Create LinkedIn campaign |
| `POST /leads` | Add leads to campaign |
| `GET /leads/{id}/status` | Check connection status |
| `POST /messages` | Send direct message |

---

## Usage Pattern

```python
class HeyReachClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.heyreach.io/v1",
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def send_connection_request(
        self,
        seat_id: str,
        linkedin_url: str,
        note: str
    ) -> ConnectionResult:
        """Send LinkedIn connection request."""
        response = await self.client.post(
            "/connections",
            json={
                "seat_id": seat_id,
                "linkedin_url": linkedin_url,
                "note": note  # Max 300 chars
            }
        )
        return ConnectionResult(**response.json())
    
    async def send_message(
        self,
        seat_id: str,
        linkedin_url: str,
        message: str
    ) -> MessageResult:
        """Send message to connected profile."""
        response = await self.client.post(
            "/messages",
            json={
                "seat_id": seat_id,
                "linkedin_url": linkedin_url,
                "message": message
            }
        )
        return MessageResult(**response.json())
    
    async def check_connection_status(
        self,
        seat_id: str,
        linkedin_url: str
    ) -> ConnectionStatus:
        """Check if already connected."""
        response = await self.client.get(
            "/connections/status",
            params={
                "seat_id": seat_id,
                "linkedin_url": linkedin_url
            }
        )
        return ConnectionStatus(**response.json())
```

---

## Webhook Events

| Event | Description |
|-------|-------------|
| `connection.sent` | Request sent |
| `connection.accepted` | Request accepted |
| `connection.rejected` | Request rejected |
| `message.sent` | Message sent |
| `message.replied` | Reply received |

---

## Rate Limits (Per Seat)

| Action | Daily Limit |
|--------|-------------|
| Connection requests | 17 |
| Messages | 50 |
| Profile views | 100 |

---

## Seat Allocation by Tier

| Tier | Seats | Monthly Cost |
|------|-------|--------------|
| Ignition | 1 | $122 |
| Velocity | 3 | $366 |
| Dominance | 5 | $610 |

---

## Best Practices

- Warm up new seats gradually (start with 5 requests/day)
- Randomize timing (don't send at exact intervals)
- Use natural message variations
- Respect LinkedIn's daily limits
