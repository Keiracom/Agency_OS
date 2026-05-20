chunk_id: eu-ai-act-risk-tiering
source_url: https://artificialintelligenceact.eu/the-act/
source_date: 2024-08-01

EU AI Act — risk tiering structure. The Act categorises AI systems into four tiers: (1) Unacceptable risk — banned (social scoring by governments, real-time biometric ID in public spaces with narrow exceptions, manipulative targeting of vulnerable groups, predictive policing using profiling); (2) High risk — heavy compliance obligations (CV-screening, credit-scoring, critical-infrastructure controls, education-access decisions, law-enforcement, migration/asylum, justice/democracy); (3) Limited risk — transparency obligations (chatbots, deepfakes, emotion-recognition — must disclose AI involvement to users); (4) Minimal risk — no obligations (most consumer AI tools). For a B2B AI dispatcher running customer tasks via Claude/OpenAI, the typical placement is LIMITED RISK — transparency obligation = clear disclosure that AI is involved.
---
chunk_id: eu-ai-act-gpai-providers
source_url: https://artificialintelligenceact.eu/article/53/
source_date: 2024-08-01

EU AI Act — General-Purpose AI (GPAI) provider obligations. Article 53 applies to GPAI model providers (OpenAI, Anthropic, Google for Gemini etc.). Obligations include: maintain technical documentation; provide downstream-provider information about model capabilities/limitations; comply with EU copyright law (training-data provenance); publish a sufficiently detailed summary of training content. As a downstream provider integrating these models (Keiracom uses Claude via LiteLLM), the upstream provider's compliance is largely OUR shield — but we must surface model identity to end-users + flag any system-prompt level steering that materially shapes outputs. Maintain a 'models in use' register linkable from the Privacy Policy.
---
chunk_id: eu-ai-act-deployer-obligations
source_url: https://artificialintelligenceact.eu/article/29/
source_date: 2024-08-01

EU AI Act — deployer obligations (Article 29, applies even at limited-risk tier). Deployers must: use the AI system in accordance with the provider's instructions; ensure human oversight where appropriate; monitor operation; inform persons whose personal data is used (where applicable); for limited-risk: disclose to natural persons interacting with the system that they are interacting with an AI. For Keiracom dispatcher: when a customer task uses AI to produce content downstream-visible to that customer's users, the END user (not just the Keiracom customer) needs to know AI is involved. Surface this in the customer's product UX, not just our ToS.
---
chunk_id: white-house-ai-bill-of-rights
source_url: https://www.whitehouse.gov/ostp/ai-bill-of-rights/
source_date: 2022-10-04

US AI Bill of Rights — Blueprint (non-binding, but precedent-setting). Five principles: (1) Safe and Effective Systems — pre-deployment testing, risk identification, ongoing monitoring; (2) Algorithmic Discrimination Protections — proactive equity assessments + reporting; (3) Data Privacy — privacy by design + agency over data use; (4) Notice and Explanation — clear, accessible explanations of system function + impact; (5) Human Alternatives, Consideration, and Fallback — option for human alternative + remediation. Non-binding federal guidance — but state-level versions (California AB 2058, Illinois AI Video Interview Act) and federal procurement clauses are starting to bind. Worth referencing in the AI-services part of the ToS as a transparency baseline.
---
chunk_id: nist-ai-rmf
source_url: https://www.nist.gov/itl/ai-risk-management-framework
source_date: 2023-01-26

NIST AI Risk Management Framework — voluntary but enterprise-procurement-relevant. The RMF organises AI risk management into four functions: GOVERN (cultivate risk-aware culture); MAP (context + risk identification); MEASURE (analyse, assess, benchmark); MANAGE (prioritise, respond, monitor). Enterprise procurement (especially US federal-adjacent + financial services) increasingly asks for NIST RMF alignment as a contract precondition. For Keiracom: maintain a one-page 'AI RMF alignment' document mapping our concrete practices (eval suite + monitoring + KEI-108 enforcement gates + privacy-by-design) to the four functions. Surfaces well in security-review questionnaires.
