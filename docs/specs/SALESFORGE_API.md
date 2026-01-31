# Salesforge API Reference

**Base URL:** https://api.salesforge.ai/public/v2
**Auth:** `Authorization: {api_key}` header (plain key, not Bearer)
**Swagger UI:** https://api.salesforge.ai/public/v2/swagger/index.html

## Endpoints

### `/me`
- **GET**: Get current user info

### `/workspaces`
- **GET**: Get workspaces
- **POST**: Create workspace

### `/workspaces/{workspaceID}`
- **GET**: Get workspace

### `/workspaces/{workspaceID}/contacts`
- **GET**: Get contacts
- **POST**: Create contact

### `/workspaces/{workspaceID}/contacts/bulk`
- **POST**: Bulk create contacts

### `/workspaces/{workspaceID}/contacts/{contactID}`
- **GET**: Get contact

### `/workspaces/{workspaceID}/custom-vars`
- **GET**: Get Custom Variables

### `/workspaces/{workspaceID}/dnc/bulk`
- **POST**: Bulk create DNCs

### `/workspaces/{workspaceID}/integrations/webhooks`
- **GET**: Get webhooks
- **POST**: Create webhook

### `/workspaces/{workspaceID}/integrations/webhooks/{webhookID}`
- **GET**: Get webhook

### `/workspaces/{workspaceID}/mailboxes`
- **GET**: Get mailboxes

### `/workspaces/{workspaceID}/mailboxes/{mailboxID}`
- **GET**: Get mailbox

### `/workspaces/{workspaceID}/mailboxes/{mailboxID}/emails/{emailID}/reply`
- **POST**: Create Email Reply

### `/workspaces/{workspaceID}/mailboxes/{mailboxID}/threads/{threadID}`
- **GET**: Get thread

### `/workspaces/{workspaceID}/products`
- **GET**: Get products
- **POST**: Create Product

### `/workspaces/{workspaceID}/products/{productID}`
- **GET**: Get product

### `/workspaces/{workspaceID}/sending-data`
- **GET**: Get sequence contact sending data

### `/workspaces/{workspaceID}/sequence-metrics`
- **GET**: Get workspace sequence metrics

### `/workspaces/{workspaceID}/sequences`
- **GET**: Get workspace sequences
- **POST**: Create sequence

### `/workspaces/{workspaceID}/sequences/{sequenceID}`
- **GET**: Get sequence by ID
- **PUT**: Update sequence
- **DELETE**: Delete sequence

### `/workspaces/{workspaceID}/sequences/{sequenceID}/analytics`
- **GET**: Get sequence analytics

### `/workspaces/{workspaceID}/sequences/{sequenceID}/contacts`
- **PUT**: Assign contacts

### `/workspaces/{workspaceID}/sequences/{sequenceID}/contacts/count`
- **GET**: Get sequence contacts count

### `/workspaces/{workspaceID}/sequences/{sequenceID}/contacts/validation/confirm`
- **POST**: Confirm validation results

### `/workspaces/{workspaceID}/sequences/{sequenceID}/contacts/validation/result`
- **GET**: Get sequence contact validation results

### `/workspaces/{workspaceID}/sequences/{sequenceID}/contacts/validation/skip`
- **POST**: Skip validation results

### `/workspaces/{workspaceID}/sequences/{sequenceID}/contacts/validation/start`
- **POST**: Start sequence contact validation

### `/workspaces/{workspaceID}/sequences/{sequenceID}/contacts/validation/validate`
- **POST**: Validate sequence contacts

### `/workspaces/{workspaceID}/sequences/{sequenceID}/import-lead`
- **PUT**: Import lead

### `/workspaces/{workspaceID}/sequences/{sequenceID}/mailboxes`
- **PUT**: Assign mailboxes

### `/workspaces/{workspaceID}/sequences/{sequenceID}/schedules`
- **PUT**: Update sequence schedules

### `/workspaces/{workspaceID}/sequences/{sequenceID}/status`
- **PUT**: Update sequence status

### `/workspaces/{workspaceID}/sequences/{sequenceID}/steps`
- **PUT**: Update sequence steps

### `/workspaces/{workspaceID}/threads`
- **GET**: Get workspace threads

