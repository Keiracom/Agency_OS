# Distribution Channels — Agency OS

**Purpose:** Channel specifications for multi-channel outreach.
**Last Updated:** January 22, 2026

---

## Documents

| Doc | Channel | Provider | Status |
|-----|---------|----------|--------|
| [EMAIL.md](EMAIL.md) | Email | Salesforge | ✅ Complete |
| [SMS.md](SMS.md) | SMS | ClickSend | ✅ Complete |
| [VOICE.md](VOICE.md) | Voice | Vapi + ElevenLabs | ✅ Complete |
| [LINKEDIN.md](LINKEDIN.md) | LinkedIn | Unipile | ✅ Complete |
| [MAIL.md](MAIL.md) | Direct Mail | ClickSend | 🔴 Spec only |
| [RESOURCE_POOL.md](RESOURCE_POOL.md) | Shared Resources | — | ✅ Complete |
| [SCRAPER_WATERFALL.md](SCRAPER_WATERFALL.md) | Web Scraping | Cheerio/Playwright/Camoufox | ✅ Complete |

---

## Channel Summary

| Channel | Engine | Integration | ALS Minimum |
|---------|--------|-------------|-------------|
| Email | `email.py` | `salesforge.py` | 20 (all tiers) |
| SMS | `sms.py` | `clicksend.py` | 85 (Hot only) |
| Voice | `voice.py` | `vapi.py` | 70 (Warm+) |
| LinkedIn | `linkedin.py` | `unipile.py` | 60 (Warm+) |
| Mail | `mail.py` | `clicksend.py` | Not implemented |

---

## Resource Model

```
Platform Level:
├── resource_pool (domains, phone numbers, LinkedIn seats)
│   └── Unassigned resources available for new clients

Client Level:
├── client_resources (assigned from pool on signup)
│   └── Dedicated resources for this client's lifetime

Campaign Level:
├── campaign_resources (inherited from client_resources)
│   └── Used by allocator for round-robin distribution
```

---

## Default Sequence

| Step | Day | Channel | Fallback |
|------|-----|---------|----------|
| 1 | 0 | Email | — |
| 2 | 3 | Voice | Email |
| 3 | 5 | LinkedIn | Skip |
| 4 | 8 | Email | — |
| 5 | 12 | SMS | Email |

---

## Cross-References

- [Master Index](../ARCHITECTURE_INDEX.md)
- [TODO.md](../TODO.md) — Gaps and priorities

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
