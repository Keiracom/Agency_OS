# Compliance Scaffolds — Entry Point

> **Status:** Engineering scaffolds ONLY. None of these documents are published or legally effective.  
> All files marked `DRAFT — pending [LAWYER] review`.  
> **SOC 2:** Deferred to enterprise phase per KEI-118 spec.

---

## Deliverables in This Directory

| File | Type | Description |
|---|---|---|
| `right_to_erasure_engineering_flow.md` | Engineering doc | Technical spec: how Keiracom honours a data-deletion request across Supabase, Valkey, Weaviate, Cognee, logs, and backups. Includes SQL/CLI/API call sequence, SLA window, audit log design. |
| `privacy_policy_TEMPLATE.md` | Legal scaffold | AU Privacy Act + GDPR + CCPA compliant section structure with bracketed placeholders. Covers data collection, use, sharing, cross-border transfers, retention, rights, breach notification. |
| `terms_of_service_TEMPLATE.md` | Legal scaffold | AU-governed ToS section structure. Covers acceptable use, IP, pricing, liability cap, indemnification, dispute resolution, termination. |
| `data_processing_agreement_TEMPLATE.md` | Legal scaffold | GDPR Art 28 DPA structure + CCPA service provider provisions. Sub-processor table, audit rights, breach notification SLA, international transfer mechanism. |

---

## SOC 2 Deferral

SOC 2 Type II certification is deferred to the enterprise sales phase. No engineering work targeting SOC 2 controls is in scope for KEI-118.  
When SOC 2 is initiated, raise a new KEI and engage an auditor; do not repurpose these templates.

---

## Lawyer Engagement Checklist

Questions and confirmations the engaged lawyer must address before any of these documents are published:

### Company identity
- [ ] Confirm [COMPANY LEGAL NAME] and [ABN]
- [ ] Confirm [REGISTERED ADDRESS]
- [ ] Designate [CONTROLLER DPO EMAIL] (or privacy contact if DPO not required)

### Jurisdiction scope
- [ ] Confirm which privacy regimes apply today (AU only? GDPR because of EU users? CCPA because of CA users?)
- [ ] Confirm adequacy / SCC requirement for AU → US transfers (note: Australia lacks GDPR adequacy decision)
- [ ] Confirm whether CCPA applies now (pre-revenue — likely threshold not met, but confirm)

### Key SLAs and thresholds
- [ ] Confirm erasure SLA (engineering proposes 7 calendar days)
- [ ] Confirm breach notification SLA: AU NDB "as soon as practicable" vs GDPR 72 hours — what is our internal process target?
- [ ] Confirm minimum age for service access (engineering placeholder: 18 for contracts)
- [ ] Confirm children's data minimum age (13 for most AU services; GDPR Art 8: 16 or lower per member state)
- [ ] Confirm data retention periods for each data category (account data, logs, billing, audit logs)

### Security claims
- [ ] Review security controls section with engineering before finalising — do NOT publish claims not empirically verified
- [ ] Confirm what evidence of compliance we can provide to enterprise customers today (no SOC 2; what do we have?)
- [ ] Agree backup retention period (Supabase plan-level) + how it intersects with erasure obligations

### Legal mechanisms
- [ ] Confirm GDPR transfer mechanism (SCCs 2021 or other)
- [ ] Confirm ACL consumer guarantee applicability to B2B customers
- [ ] Confirm refund policy under Australian Consumer Law
- [ ] Confirm dispute resolution mechanism (negotiation → mediation → [GOVERNING STATE] courts vs arbitration)
- [ ] Confirm force majeure clause inclusion and scope
- [ ] Confirm ToS liability cap formulation is enforceable under AU law

### Sub-processors
- [ ] Review sub-processor table in DPA template with engineering (complete list, accurate jurisdictions)
- [ ] Confirm Data Processing Agreements are in place with each sub-processor
- [ ] Set sub-processor change notice period

### Pricing and payment
- [ ] Confirm GST treatment for AU B2B customers
- [ ] Confirm VAT/reverse-charge obligations for EU customers
- [ ] Confirm tax record retention period (AU GST typically 5 years)

---

## Related KEIs

| KEI | Description | Status |
|---|---|---|
| KEI-118 | Compliance scaffold templates + right-to-erasure engineering flow | This PR |
| KEI-116 | `customer_api_keys` table (merged PR #954) | Merged |
| KEI-117A | Valkey per-tenant namespace (merged PR #961) | Merged |
| _new KEI needed_ | `public.erasure_requests` + `public.erasure_audit_log` tables | Not started |
| _new KEI needed_ | Verify Weaviate `tenant_id` property on Discoveries/Decisions/Keis collections | Not started |
| _new KEI needed_ | Confirm Cognee `prune_data` API with vendor | Not started |
| _new KEI needed_ | Implement Better Stack log deletion endpoint | Not started |
| _new KEI needed_ | Wire Prefect flow for orchestrated erasure | Not started |

---

## How to Use These Templates

1. Engage Australian tech/privacy lawyer with this directory as the starting brief.
2. Provide the lawyer with the [Lawyer Engagement Checklist](#lawyer-engagement-checklist) above.
3. For each `[BRACKETED PLACEHOLDER]`, the lawyer fills in the legally correct value.
4. Engineering verifies all security claims in the Privacy Policy and DPA are accurate before lawyer signs off.
5. On final approval, rename `*_TEMPLATE.md` to the published filename, remove the DRAFT header, and update this README.
6. Publish via the product website; add the URL to the ToS and Privacy Policy cross-references.
