chunk_id: ndb-trigger
source_url: https://www.oaic.gov.au/privacy/notifiable-data-breaches
source_date: 2018-02-22

OAIC Notifiable Data Breaches (NDB) scheme — trigger. An eligible data breach must be notified when (a) there is unauthorised access to, or unauthorised disclosure of, personal information, OR loss of personal information that is likely to result in unauthorised access or disclosure; AND (b) the access, disclosure or loss is likely to result in serious harm to one or more of the individuals to whom the information relates; AND (c) the entity has not been able to prevent the likely risk of serious harm with remedial action. 'Serious harm' includes serious physical, psychological, emotional, financial, or reputational harm. Encryption + tokenisation that meaningfully reduces the access risk can be the basis for concluding remedial action has succeeded.
---
chunk_id: ndb-assessment-window
source_url: https://www.oaic.gov.au/privacy/notifiable-data-breaches/notifiable-data-breach-statistics
source_date: 2018-02-22

OAIC NDB — 30-day assessment window. If an entity suspects an eligible data breach has occurred, it must carry out a 'reasonable and expeditious' assessment within 30 days of becoming aware of the suspicion. The assessment determines whether (a) a breach has actually occurred and (b) whether it's likely to result in serious harm. If both YES, notification is required 'as soon as practicable' — there is no separate 72-hour rule (unlike GDPR). Document the assessment process — the regulator looks at the assessment record post-incident.
---
chunk_id: ndb-notification-content
source_url: https://www.oaic.gov.au/privacy/notifiable-data-breaches
source_date: 2018-02-22

OAIC NDB — notification content. A statement to the OAIC and to affected individuals must include: identity and contact details of the entity; description of the eligible data breach; the kinds of information involved; recommendations about the steps individuals should take in response to the breach. Notification to individuals is by the means the entity normally communicates (email is acceptable for online services) and must be 'reasonably practicable'. If direct notification not practicable, publish the statement on the entity's website and take reasonable steps to publicise it.
---
chunk_id: ndb-multi-entity-assessment
source_url: https://www.oaic.gov.au/privacy/notifiable-data-breaches/data-breach-preparation-and-response
source_date: 2019-07-01

OAIC NDB — multi-entity breaches (processor pattern). Where personal information held by an entity is breached BUT another entity (e.g. cloud provider, BYO-key custodian, payment processor) holds responsibility for protecting the information, both entities have NDB obligations. The entity with the closest relationship to the affected individuals typically notifies; the other entity may be relieved of its own notification obligation if the first entity notifies — but each must independently assess. For Keiracom as a SaaS dispatcher using BYO API keys + Paddle as MoR: a breach of the Paddle billing surface triggers Paddle's notification; a breach of Keiracom-held customer-task content triggers Keiracom's notification.
---
chunk_id: ndb-remedial-action-doctrine
source_url: https://www.oaic.gov.au/privacy/notifiable-data-breaches
source_date: 2018-02-22

OAIC NDB — remedial action doctrine. Notification is NOT required if the entity successfully takes remedial action before the breach is likely to result in serious harm. Typical successful remediations: recovery of the lost device/data before it's accessed; effective encryption (where keys are not also breached); revoking unauthorised access before exfiltration; rapid password resets where credential theft is the only vector. The entity bears the burden of demonstrating that remediation reasonably prevented serious harm. Document the remediation evidence — the regulator will look at the audit trail after the fact.
