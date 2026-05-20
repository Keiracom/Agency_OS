chunk_id: art-5-principles
source_url: https://gdpr-info.eu/art-5-gdpr/
source_date: 2018-05-25

GDPR Article 5 — Principles relating to processing of personal data. Personal data shall be: (a) processed lawfully, fairly, and in a transparent manner ('lawfulness, fairness, transparency'); (b) collected for specified, explicit, and legitimate purposes ('purpose limitation'); (c) adequate, relevant, and limited to what is necessary ('data minimisation'); (d) accurate and kept up to date ('accuracy'); (e) kept in a form which permits identification no longer than necessary ('storage limitation'); (f) processed in a manner that ensures appropriate security ('integrity and confidentiality'). The controller is responsible for, and must be able to demonstrate, compliance ('accountability'). These six principles are the foundation that every operational decision (logging, retention, sharing) must trace back to.
---
chunk_id: art-6-lawful-bases
source_url: https://gdpr-info.eu/art-6-gdpr/
source_date: 2018-05-25

GDPR Article 6 — Lawfulness of processing. Processing is lawful only if (and to the extent that) at least one of six bases applies: (a) consent; (b) necessary for performance of a contract with the data subject (or pre-contractual steps); (c) necessary for compliance with a legal obligation; (d) necessary to protect vital interests of the data subject or another person; (e) necessary for the performance of a task carried out in the public interest; (f) necessary for the purposes of legitimate interests pursued by the controller (except where overridden by data subject rights, particularly for children). For a B2B SaaS dispatcher, primary bases are typically (b) contract for core service operation and (f) legitimate interests for security/analytics — both must be documented and the latter requires a balancing test.
---
chunk_id: art-13-information-at-collection
source_url: https://gdpr-info.eu/art-13-gdpr/
source_date: 2018-05-25

GDPR Article 13 — Information to be provided where personal data are collected from the data subject. At the time of collection the controller must provide: identity and contact details of the controller (and DPO if applicable); purposes of the processing AND legal basis; legitimate interests pursued (if Art 6(1)(f)); recipients or categories of recipients; transfers to third countries + safeguards; retention period (or criteria to determine it); existence of data subject rights (access / rectification / erasure / restriction / portability / objection); right to withdraw consent (where Art 6(1)(a) applies); right to lodge a complaint with a supervisory authority; whether provision is statutory/contractual and consequences of not providing; automated decision-making (incl. profiling) details. This is the disclosure surface a GDPR-compliant signup flow must satisfy.
---
chunk_id: art-17-right-to-erasure
source_url: https://gdpr-info.eu/art-17-gdpr/
source_date: 2018-05-25

GDPR Article 17 — Right to erasure ('right to be forgotten'). Data subject has the right to obtain erasure of personal data without undue delay where: the data are no longer necessary for the purposes collected; the subject withdraws consent and there's no other legal basis; the subject objects (Art 21) and there are no overriding legitimate grounds; data have been unlawfully processed; erasure is required for legal compliance. Exceptions include freedom of expression, legal compliance, public interest, legal claims. Practical implication: soft-delete via `deleted_at` is INSUFFICIENT for a GDPR erasure request — must implement true purge + cascade across backups within reasonable timeframe, with audit log noting the erasure.
---
chunk_id: art-20-data-portability
source_url: https://gdpr-info.eu/art-20-gdpr/
source_date: 2018-05-25

GDPR Article 20 — Right to data portability. Data subject has the right to receive their personal data — which they provided to the controller — in a structured, commonly used, machine-readable format AND to transmit that data to another controller without hindrance. Applies where (a) processing is based on consent or contract AND (b) processing is by automated means. Practical implication: build an export endpoint that returns the user's task history + key inventory + memory pins in JSON (or CSV) format. Does NOT apply to data the controller derived (analytics, model outputs) — only data the subject provided.
---
chunk_id: art-28-processor
source_url: https://gdpr-info.eu/art-28-gdpr/
source_date: 2018-05-25

GDPR Article 28 — Processor obligations. Where processing is carried out on behalf of a controller, the controller must use only processors providing sufficient guarantees to implement appropriate technical and organisational measures. Processing by a processor must be governed by a contract binding the processor: subject-matter, duration, nature/purpose, type of personal data, categories of data subjects, controller obligations + rights. The contract must stipulate: process only on documented instructions; ensure persons authorised are bound by confidentiality; take all measures required by Art 32 (security); engage no sub-processor without prior authorisation; assist controller with data subject requests; assist with breach notification + DPIAs; delete or return all personal data at end of services; make available all info necessary to demonstrate compliance + allow audits. This is the DPA template structure.
