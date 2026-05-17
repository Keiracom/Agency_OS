# Privacy Policy

> **DRAFT — pending [LAWYER] review. Do NOT publish. All `[BRACKETED PLACEHOLDERS]` must be completed by engaged Australian tech/privacy lawyer before this document is made public.**  
> **Document version:** 0.1 scaffold  
> **Prepared:** Engineering (KEI-118)  
> **Jurisdiction baseline:** AU Privacy Act 1988 (Cth) + GDPR (EU) 2016/679 + CCPA (California) § 1798.100 et seq.

---

## 1. About This Policy

This Privacy Policy explains how [COMPANY LEGAL NAME] (ABN [ABN]) ("we", "us", "our") collects, uses, stores, discloses, and protects personal information in connection with [PRODUCT/SERVICE NAME].

**Registered address:** [REGISTERED ADDRESS]  
**Privacy contact:** [CONTROLLER DPO EMAIL]  
**Effective date:** [EFFECTIVE DATE — to be set on legal sign-off]

We are bound by the Australian Privacy Principles (APPs) contained in the Privacy Act 1988 (Cth). Where we have customers or users located in the European Economic Area, we also comply with the GDPR. Where we have users in California, we comply with the CCPA.

---

## 2. Information We Collect

We may collect the following categories of personal information:

### 2.1 Information you provide directly

- Name and contact details (email address, phone number)
- Business details (company name, ABN/ACN, registered address)
- Account credentials ([DESCRIBE AUTHENTICATION METHOD — e.g., email + password, Google SSO])
- Payment information ([DESCRIBE PAYMENT PROCESSOR — e.g., "processed by [PAYMENT PROCESSOR NAME]; we do not store raw card numbers"])
- Communications you send us

### 2.2 Information collected automatically

- Usage data (pages visited, features used, timestamps)
- Device and browser information
- IP addresses and approximate geolocation
- API usage logs (request counts, latency, error codes — not payload content)
- [LIST ANY ADDITIONAL TELEMETRY — e.g., Better Stack structured logs; confirm retention period]

### 2.3 Information from third parties

- [LIST THIRD-PARTY ENRICHMENT SOURCES — e.g., business registry data, LinkedIn public profiles. Confirm GDPR Art 14 notice requirements if collecting from third parties about EU data subjects]

### 2.4 Special categories of personal data

We do not intentionally collect sensitive personal information as defined under APP 3.3 (health information, racial or ethnic origin, political opinions, religious beliefs, biometric data, etc.) or GDPR Article 9 special category data.  
`[CONFIRM WITH LAWYER — if any enrichment pipeline touches any of these categories, additional safeguards apply]`

---

## 3. How We Use Personal Information

We use personal information for the following purposes:

| Purpose | Lawful basis (GDPR) | AU APP basis |
|---|---|---|
| Providing and operating the service | Contract performance (Art 6(1)(b)) | APP 6.1 — primary purpose |
| Billing and payment processing | Contract performance | APP 6.1 |
| Customer support | Legitimate interests (Art 6(1)(f)) | APP 6.2(a) |
| Security and fraud prevention | Legitimate interests | APP 6.2(a) |
| Service improvement and analytics | Legitimate interests `[CONFIRM — or consent]` | APP 6.2(a) |
| Marketing communications | Consent (Art 6(1)(a)) | Spam Act 2003 consent |
| Legal compliance | Legal obligation (Art 6(1)(c)) | Privacy Act s 13B |

`[CONFIRM LAWFUL BASIS MAPPING WITH LAWYER — ensure no purpose lacks a valid basis, especially for analytics and marketing]`

---

## 4. How We Share Personal Information

We do not sell personal information.  
`[AU context: "sell" under CCPA has a specific definition — confirm with lawyer whether any data sharing constitutes a "sale" under CCPA]`

We may share personal information with:

- **Service providers** acting as processors on our behalf: [LIST CURRENT PROCESSORS — e.g., Supabase (database), Resend (email), Telnyx (SMS), Better Stack (logging). Confirm Data Processing Agreements in place with each.]
- **Professional advisers** (lawyers, accountants, auditors) under confidentiality obligations
- **Government or regulatory bodies** when required by law
- **Successors** in the event of a merger, acquisition, or asset sale `[CONFIRM NOTIFICATION OBLIGATIONS WITH LAWYER]`
- **Other parties** with your explicit consent

We require all third-party processors to implement appropriate technical and organisational measures protecting personal data.

---

## 5. Cross-Border Data Transfers

[COMPANY LEGAL NAME] is based in Australia. Your data may be processed or stored by service providers located in:

- [LIST PROCESSOR JURISDICTIONS — e.g., United States (Supabase/AWS, Weaviate cloud), European Union, [OTHER]]

**GDPR transfers:** Data transferred from the EEA to countries without an adequacy decision is protected by [CONFIRM TRANSFER MECHANISM — e.g., Standard Contractual Clauses (EU SCCs), adequacy decision, or binding corporate rules].

**AU Privacy Act APP 8:** Before disclosing personal information to an overseas recipient, we take reasonable steps to ensure the recipient does not breach the APPs.  
`[CONFIRM TRANSFER SAFEGUARDS WITH LAWYER — list each processor + safeguard]`

---

## 6. Data Retention

We retain personal information only as long as necessary for the purposes collected, or as required by law.

| Data category | Retention period |
|---|---|
| Account data | Duration of account + [RETENTION PERIOD — e.g., 7 years] after closure |
| API usage logs | [CONFIRM RETENTION PERIOD] |
| Billing records | [CONFIRM — AU GST typically 5 years] |
| Support communications | [CONFIRM RETENTION PERIOD] |
| Erasure audit logs | [CONFIRM RETENTION PERIOD — GDPR accountability Art 5(2)] |

`[CONFIRM ALL RETENTION PERIODS WITH LAWYER]`

---

## 7. Your Rights

### 7.1 Under the Australian Privacy Act

You have the right to:
- Access the personal information we hold about you (APP 12)
- Correct inaccurate personal information (APP 13)
- Complain to us about a privacy breach (APP 1.4)
- Complain to the Office of the Australian Information Commissioner (OAIC) if unsatisfied with our response

### 7.2 Under GDPR (EEA residents)

You have the right to:
- Access (Art 15), rectification (Art 16), erasure (Art 17), restriction of processing (Art 18)
- Data portability (Art 20)
- Object to processing (Art 21)
- Withdraw consent at any time where processing is consent-based (Art 7(3))
- Lodge a complaint with your local supervisory authority

### 7.3 Under CCPA (California residents)

You have the right to:
- Know what personal information is collected, disclosed, or sold
- Delete personal information (subject to exceptions)
- Opt-out of the sale of personal information `[CONFIRM — do we sell data under CCPA definition?]`
- Non-discrimination for exercising privacy rights

### 7.4 How to exercise your rights

Submit requests to: [CONTROLLER DPO EMAIL]  
We will respond within [CONFIRM RESPONSE SLA — GDPR: 30 days + 2-month extension; AU: reasonable time; CCPA: 45 days + 45-day extension].

We may need to verify your identity before actioning a request.

---

## 8. Right to Erasure (Deletion Requests)

See the engineering flow for how we process deletion requests: `docs/compliance/right_to_erasure_engineering_flow.md` (internal reference).

Upon a verified erasure request, we will delete your personal information from:
- Our databases (Supabase)
- Our cache layer (Valkey)
- Our AI/knowledge graph stores (Weaviate, Cognee)
- Application logs (subject to legal retention obligations)

**SLA:** `[CONFIRM ERASURE SLA WITH LAWYER — 7 calendar days is our engineering target; legal outer bound differs per jurisdiction]`

Erasure will not apply to data we are required to retain by law (see §6 Retention and §9 Out-of-Scope in the engineering flow).

---

## 9. Security

We implement appropriate technical and organisational measures including:
- `[LIST CONFIRMED SECURITY CONTROLS — only list what is empirically true, e.g., TLS in transit, Supabase RLS policies, API key hashing. Do NOT claim AES-256-GCM at rest unless confirmed with engineering.]`
- Access controls limited to personnel with a need to know
- [CONFIRM ADDITIONAL CONTROLS — e.g., MFA for production access, audit logging]

We do not hold SOC 2 certification at this time. `[SOC 2 deferred to enterprise phase per KEI-118 spec]`

---

## 10. Children's Data

Our services are not directed at children under the age of [CONFIRM MINIMUM AGE — AU: 13 for most services; GDPR Art 8: 16 years (or 13–16 per member state local law); CCPA COPPA: 13]. We do not knowingly collect personal information from minors.  
`[CONFIRM MINIMUM AGE AND PARENTAL CONSENT OBLIGATIONS WITH LAWYER]`

---

## 11. Cookies and Tracking Technologies

`[DESCRIBE COOKIE USAGE — e.g., session cookies for authentication, analytics cookies. Confirm ePrivacy Directive / AU consent requirements]`

You can control cookies through your browser settings. `[CONFIRM COOKIE BANNER REQUIREMENTS FOR TARGET JURISDICTIONS]`

---

## 12. Data Breach Notification

In the event of a notifiable data breach, we will:
- Notify the OAIC within [CONFIRM — AU Notifiable Data Breaches scheme: "as soon as practicable"]
- Notify affected individuals where required
- Notify the relevant EEA supervisory authority within [BREACH NOTIFICATION SLA — confirm AU 30 days vs GDPR 72 hours with lawyer]

`[CONFIRM BREACH NOTIFICATION THRESHOLDS AND TIMELINES WITH LAWYER — AU NDB scheme vs GDPR Art 33/34 differ materially]`

---

## 13. Changes to This Policy

We may update this Privacy Policy from time to time. We will notify you of material changes by [CONFIRM NOTIFICATION METHOD — e.g., email, in-app notice] at least [CONFIRM NOTICE PERIOD] before changes take effect.

---

## 14. Contact and Complaints

**Privacy contact:** [CONTROLLER DPO EMAIL]  
**Postal address:** [REGISTERED ADDRESS]

If you are unsatisfied with our response, you may contact:
- **Australia:** Office of the Australian Information Commissioner (OAIC) — oaic.gov.au
- **EU/EEA:** Your local data protection authority — edpb.europa.eu/about-edpb/about-edpb/members_en
- **California:** California Attorney General — oag.ca.gov

---

*DRAFT v0.1 — [COMPANY LEGAL NAME] — prepared by Engineering for lawyer review. Not for publication.*
