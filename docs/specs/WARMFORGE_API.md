# WarmForge API Reference

**Base URL:** https://api.warmforge.ai/public/v1
**Auth:** `Authorization: {api_key}` header (plain key)
**Swagger UI:** https://api.warmforge.ai/public/swagger/index.html

## Endpoints

### `/mailboxes`
- **GET**: Get mailboxes

### `/mailboxes/bulk-update`
- **POST**: Update mailboxes

### `/mailboxes/connect-oauth2`
- **POST**: Connect OAuth2 mailbox

### `/mailboxes/connect-smtp`
- **POST**: Connect SMTP mailbox

### `/mailboxes/{address}`
- **GET**: Get mailbox
- **DELETE**: Delete mailbox
- **PATCH**: Update mailbox

### `/mailboxes/{address}/warmup/stats`
- **GET**: Get warmup stats

### `/placement-tests`
- **GET**: Get placement tests
- **POST**: Create placement test

### `/placement-tests/{placementTestID}`
- **GET**: Get placement test
- **DELETE**: Delete placement test

