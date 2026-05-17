# Data Processing Agreement (DPA)

> **DRAFT — pending [LAWYER] review. Do NOT publish. All `[BRACKETED PLACEHOLDERS]` must be completed by engaged Australian tech/privacy lawyer before this document is made public.**  
> **Document version:** 0.1 scaffold  
> **Prepared:** Engineering (KEI-118)  
> **Jurisdiction baseline:** GDPR (EU) 2016/679 Arts 28–29 + AU Privacy Act 1988 (Cth) APP 8 + CCPA § 1798.140 "service provider" requirements

---

## Background

This Data Processing Agreement ("DPA") forms part of the agreement between:

**Controller / Customer:** [CUSTOMER COMPANY LEGAL NAME] ("Controller")  
**Processor / Provider:** [COMPANY LEGAL NAME] (ABN [ABN]) ("Processor")

The Processor provides the [PRODUCT/SERVICE NAME] service to the Controller under the [Master Services Agreement / Terms of Service] dated [CONTRACT DATE] ("Principal Agreement").

This DPA governs the processing of personal data by the Processor on behalf of the Controller.

---

## 1. Definitions

In this DPA:

- **"Personal Data"** has the meaning given in the GDPR and/or the AU Privacy Act 1988 (Cth) as applicable.
- **"Processing"** has the meaning given in GDPR Art 4(2).
- **"Data Subject"** means the individual to whom Personal Data relates.
- **"Sub-processor"** means any processor engaged by the Processor to process Personal Data.
- **"Controller"**, **"Processor"**, **"Supervisory Authority"** have the meanings in GDPR Art 4.
- **"GDPR"** means Regulation (EU) 2016/679.
- **"AU Privacy Act"** means the Privacy Act 1988 (Cth).

`[CONFIRM DEFINITIONS WITH LAWYER — confirm whether "personal data" under CCPA "personal information" definition requires separate treatment for California-resident data subjects]`

---

## 2. Processing Details

| Element | Detail |
|---|---|
| Subject matter | [DESCRIBE PROCESSING SUBJECT MATTER — e.g., "outbound sales lead management and CRM data for the Controller's business"] |
| Duration | Term of the Principal Agreement + [POST-TERMINATION RETENTION — e.g., 30 days for data export, then deletion] |
| Nature of processing | [DESCRIBE — e.g., "storage, enrichment, analysis, outbound communication triggering"] |
| Purpose of processing | [CONFIRM WITH LAWYER — match exactly to Controller's documented purpose] |
| Types of personal data | [LIST — e.g., business contact names, email addresses, phone numbers, job titles, company names, LinkedIn profile URLs] |
| Categories of data subjects | [LIST — e.g., "employees and representatives of the Controller's prospect companies"] |

`[CONFIRM PROCESSING DETAILS WITH LAWYER — GDPR Art 28(3) requires these be specified in the DPA]`

---

## 3. Obligations of the Processor

The Processor agrees to:

1. Process Personal Data only on documented instructions from the Controller, including with regard to transfers to third countries (GDPR Art 28(3)(a)). `[CONFIRM INSTRUCTION MECHANISM — e.g., via API configuration, written notice]`
2. Ensure persons authorised to process Personal Data are bound by confidentiality obligations (GDPR Art 28(3)(b)).
3. Implement appropriate technical and organisational security measures per §7 below (GDPR Art 28(3)(c)).
4. Respect conditions for engaging Sub-processors per §5 (GDPR Art 28(3)(d)).
5. Assist the Controller with responding to Data Subject rights requests per §6 (GDPR Art 28(3)(e)).
6. Assist the Controller with security, breach notification, DPIAs, and prior consultation obligations (GDPR Art 28(3)(f)).
7. Delete or return Personal Data on termination of the Principal Agreement per §8 (GDPR Art 28(3)(g)).
8. Provide all information necessary to demonstrate compliance with GDPR Art 28 and permit audits per §9 (GDPR Art 28(3)(h)).

---

## 4. Controller Obligations

The Controller represents and warrants that:

1. It has a lawful basis for processing Personal Data and for instructing the Processor.
2. All Data Subjects whose Personal Data is uploaded to the Service have been notified about the processing in accordance with applicable law.
3. It will not instruct the Processor to process Personal Data in a way that violates applicable law.

---

## 5. Sub-processors

The Processor currently engages the following Sub-processors:

| Sub-processor | Location | Processing activity |
|---|---|---|
| Supabase Inc. | [CONFIRM HOSTING REGION — US / EU] | Database hosting |
| [VALKEY HOSTING PROVIDER — e.g., Upstash, Redis Cloud] | [LOCATION] | Cache / queue |
| [WEAVIATE HOSTING PROVIDER] | [LOCATION] | Vector database / knowledge graph |
| [COGNEE HOSTING PROVIDER] | [LOCATION] | AI memory / graph |
| Resend Inc. | [LOCATION] | Transactional email |
| Telnyx LLC | [LOCATION] | SMS |
| Better Stack | [LOCATION] | Log management |
| [ADD FURTHER SUB-PROCESSORS] | | |

`[CONFIRM SUB-PROCESSOR LIST WITH ENGINEERING — ensure list is complete and accurate at time of publication. GDPR Art 28(2) requires Controller consent for each Sub-processor (general or specific).]`

**New Sub-processors:** The Processor will give the Controller [CONFIRM NOTICE PERIOD — e.g., 30 days] advance notice before engaging a new Sub-processor. The Controller may object by notifying the Processor in writing within [CONFIRM OBJECTION PERIOD]. If the Controller objects and the Processor cannot accommodate the objection, the Controller may terminate the Principal Agreement.

---

## 6. Data Subject Rights

The Processor will provide reasonable assistance to the Controller in fulfilling its obligations to respond to Data Subject rights requests (access, rectification, erasure, restriction, portability, objection).

Erasure requests will be processed per the engineering flow documented in `docs/compliance/right_to_erasure_engineering_flow.md`.

The Processor will notify the Controller within [CONFIRM TIMEFRAME — e.g., 3 business days] if it receives a rights request directly from a Data Subject, and will not respond to the request without the Controller's instruction unless required by law.

---

## 7. Security

The Processor will implement technical and organisational measures appropriate to the risk, including:

- `[LIST CONFIRMED SECURITY CONTROLS — do NOT claim controls not empirically verified; e.g., TLS 1.2+ in transit, row-level security in Supabase, API key hashing]`
- Access controls restricted to authorised personnel
- `[CONFIRM ADDITIONAL CONTROLS — e.g., MFA for production systems, audit logging, penetration testing schedule]`

`[CONFIRM SECURITY ANNEX CONTENTS WITH ENGINEERING AND LAWYER — do NOT insert placeholder security claims]`

The Processor will notify the Controller of a personal data breach affecting the Controller's data without undue delay and in any event within [BREACH NOTIFICATION SLA — confirm AU NDB "as soon as practicable" vs GDPR Art 33 72 hours with lawyer].

---

## 8. Retention and Deletion

On termination of the Principal Agreement, the Processor will, at the Controller's election:

(a) Return all Personal Data to the Controller in [CONFIRM FORMAT] within [CONFIRM PERIOD] days; or  
(b) Delete all Personal Data and provide written confirmation of deletion within [CONFIRM PERIOD] days.

The Processor may retain Personal Data to the extent required by applicable law (e.g., tax records), subject to continued confidentiality obligations.

---

## 9. Audits

The Controller may, on [CONFIRM NOTICE PERIOD — e.g., 30 days] written notice and no more than [CONFIRM FREQUENCY — e.g., once per year] (unless a breach has occurred), audit the Processor's compliance with this DPA.  
`[CONFIRM AUDIT RIGHTS SCOPE WITH LAWYER — full on-site audit vs questionnaire + third-party certification. Note: SOC 2 deferred to enterprise phase; confirm what evidence is available now]`

The costs of any audit are borne by [CONFIRM COST ALLOCATION WITH LAWYER].

---

## 10. International Transfers

Transfers of Personal Data from the EEA or UK to third countries are governed by:

`[CONFIRM TRANSFER MECHANISM WITH LAWYER — e.g., EU Standard Contractual Clauses (2021 SCCs), UK International Data Transfer Agreement, adequacy decisions for Australia (note: Australia does NOT have GDPR adequacy; confirm SCCs or BCRs required)]`

---

## 11. CCPA Service Provider Provisions

Where the Processor acts as a "service provider" under the CCPA in relation to California residents' personal information:

- The Processor will not sell or share the personal information.
- The Processor will not retain, use, or disclose the personal information for any purpose other than performing the services under the Principal Agreement.
- The Processor will not combine the personal information with personal information received from other sources except as permitted under the CCPA.
- The Processor certifies it understands and will comply with the CCPA service provider restrictions.

`[CONFIRM CCPA PROVISIONS WITH LAWYER — confirm whether Controller qualifies as a CCPA "business" (>$25M revenue OR >100K consumers data handled). If pre-revenue, confirm applicability now vs at scale]`

---

## 12. Liability

Each party's liability under this DPA is subject to the liability limitations in the Principal Agreement, except to the extent applicable law prevents limitation of liability in connection with data protection obligations.

`[CONFIRM LIABILITY ALLOCATION WITH LAWYER — GDPR Art 82 joint and several liability between controllers and processors]`

---

## 13. Term and Termination

This DPA is coterminous with the Principal Agreement. On termination for any reason, §8 (Retention and Deletion) survives.

---

## 14. Governing Law

This DPA is governed by [GOVERNING LAW — match Principal Agreement; note GDPR requires EU law may apply in some SCCs contexts — confirm with lawyer].

---

## 15. Signatures

**[COMPANY LEGAL NAME]**  
Signed by: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Name: [AUTHORISED SIGNATORY NAME]  
Title: [TITLE]  
Date: \_\_\_\_\_\_\_

**[CUSTOMER COMPANY LEGAL NAME]**  
Signed by: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Name: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Title: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Date: \_\_\_\_\_\_\_

---

*DRAFT v0.1 — [COMPANY LEGAL NAME] — prepared by Engineering for lawyer review. Not for publication.*
