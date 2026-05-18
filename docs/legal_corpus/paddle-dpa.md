chunk_id: paddle-mor-model
source_url: https://www.paddle.com/legal/merchant-of-record-agreement
source_date: 2024-08-01

Paddle Merchant-of-Record (MoR) model. Under the MoR agreement Paddle becomes the seller of record to the end customer; the SaaS vendor (Keiracom) sells to Paddle, and Paddle resells to the consumer. Tax collection, remittance, fraud protection, chargebacks, billing-currency conversion, and end-customer payment-method support are Paddle's responsibility. Practical effect on the data flow: Keiracom holds NO PCI-scope payment-card data — Paddle does. Keiracom holds the customer's name + email + billing address (passed back via webhook) + product/subscription metadata. The privacy policy should clearly state Paddle is the data controller for payment processing and link to Paddle's privacy notice.
---
chunk_id: paddle-controller-processor-mapping
source_url: https://www.paddle.com/legal/dpa
source_date: 2024-06-15

Paddle DPA — controller/processor mapping. For card data + billing identity collection at the checkout surface, Paddle is the CONTROLLER (MoR seller). For SaaS-vendor-side subscription state (which Keiracom receives via webhook for entitlement provisioning), Keiracom is the CONTROLLER and Paddle acts as a PROCESSOR for the subscription metadata in flight. Two DPA shapes apply depending on the data flow direction. The vendor DPA must reflect both: (a) Paddle-as-controller for checkout PII, (b) Paddle-as-processor for subscription metadata feeding back. Don't conflate the two — different obligations apply.
---
chunk_id: paddle-subprocessors
source_url: https://www.paddle.com/legal/sub-processors
source_date: 2024-09-01

Paddle sub-processors. Paddle maintains a public list of sub-processors (typically AWS for infrastructure, Stripe for some card-flows depending on region, Sift for fraud, others). Under Art 28 GDPR + Paddle's DPA, Keiracom (as a Paddle customer) inherits notification rights when sub-processors change. Practical action: link to Paddle's sub-processor list from the Keiracom privacy policy + DPA; commit to surfacing material changes within a notice window (commonly 30 days) in the privacy-policy changelog.
---
chunk_id: paddle-data-residency
source_url: https://www.paddle.com/legal/dpa
source_date: 2024-06-15

Paddle DPA — data residency + transfer mechanism. Paddle's primary infrastructure is EU/UK. Where customer data flows outside the EU/EEA, Paddle relies on Standard Contractual Clauses (SCCs) and (for UK) the UK IDTA / UK Addendum. Keiracom-side: the customer-facing privacy policy must disclose this onward transfer and the safeguards (SCCs + supplementary measures where relevant). If Keiracom-side processing happens in Australia (which it does — Vultr Sydney), the AU→EU→AU chain involves two transfer hops; both need disclosure.
---
chunk_id: paddle-webhook-data-scope
source_url: https://developer.paddle.com/webhooks/overview
source_date: 2024-11-01

Paddle webhook data scope (what Keiracom actually receives). Webhook events include: subscription.created/updated/cancelled/paused with customer_id, subscription_id, status, billing_period, items array, customer object (name, email, locale, address.country, address.postal_code where collected); transaction.completed with similar customer fields + payment_method category (NEVER raw card data); invoice.paid with totals + tax breakdown. The DPA should enumerate this exact data set as the scope of Paddle-as-processor processing on Keiracom's behalf — broader claims trigger over-inclusion challenges.
