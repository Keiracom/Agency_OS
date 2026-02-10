# Tool Evaluation: EspoCRM

**Evaluated:** 2026-01-30
**Source:** https://github.com/espocrm/espocrm
**Stars:** 2,768

## What It Does
EspoCRM is an open-source CRM application providing:
- Lead/contact/account management
- Sales opportunities tracking
- Marketing campaign management
- Support case management
- Calendar and task management
- REST API for integrations

## Pricing
- **Open Source** (AGPLv3)
- Self-hosted: Free
- Paid cloud hosting available

## Integration Complexity with Our Stack
| Factor | Assessment |
|--------|------------|
| Stack | **PHP** - incompatible with FastAPI/Python |
| Database | MySQL/MariaDB/PostgreSQL |
| Architecture | Monolithic - can't use as library |
| API | REST API exists, could sync via API calls |

**Complexity: HIGH** - Different tech stack entirely (PHP vs Python)

## Competitors/Alternatives
- **Supabase + Custom** (what we're building)
- **Twenty** - Open source CRM (TypeScript)
- **Salesforce** - Enterprise
- **HubSpot** - SMB/Enterprise
- **Pipedrive** - SMB focused

## Analysis
EspoCRM is a solid open-source CRM but doesn't fit our needs:
- We're building our own lead/contact management in Supabase
- PHP codebase can't be integrated with our Python backend
- Would be redundant to our existing Supabase data model
- No value-add over what we're already building

## Recommendation: **SKIP**

**Reasoning:**
1. PHP stack incompatible with our FastAPI/Python architecture
2. Redundant - we already have CRM functionality in Supabase
3. Would add operational complexity (separate PHP service)
4. No unique capabilities we lack

**Action:** None. Continue building CRM features natively in Agency OS.
