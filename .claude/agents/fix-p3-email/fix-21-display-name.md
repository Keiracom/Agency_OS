---
name: Fix 21 - Email Display Name Format
description: Enforces standard display name format
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 21: Display Name Format

## Gap Reference
- **TODO.md Item:** #21
- **Priority:** P3 Medium (Email Engine)
- **Location:** `src/engines/email.py`
- **Issue:** Standard format not enforced

## Pre-Flight Checks

1. Check existing display name handling:
   ```bash
   grep -rn "display.name\|from.*name\|sender.*name" src/engines/email.py
   ```

2. Check email sending code:
   ```bash
   grep -rn "from.*:\|From.*:" src/engines/email.py
   ```

3. Review EMAIL.md for format requirements:
   ```bash
   grep -n "display.*name\|format\|from" docs/architecture/distribution/EMAIL.md
   ```

## Implementation Steps

1. **Define display name format:**
   ```python
   # Standard format: "First Last | Company"
   # Example: "John Smith | Acme Corp"

   DISPLAY_NAME_FORMAT = "{first_name} {last_name} | {company}"
   DISPLAY_NAME_FORMAT_NO_COMPANY = "{first_name} {last_name}"
   ```

2. **Create display name formatter:**
   ```python
   import re

   def format_display_name(
       first_name: str,
       last_name: str,
       company: Optional[str] = None
   ) -> str:
       """Format display name for email From header.

       Standard format: "First Last | Company"
       Fallback: "First Last" (if no company)

       Args:
           first_name: Sender's first name
           last_name: Sender's last name
           company: Company name (optional)

       Returns:
           Formatted display name
       """
       # Clean inputs
       first = first_name.strip().title()
       last = last_name.strip().title()

       if company:
           company = company.strip()
           return DISPLAY_NAME_FORMAT.format(
               first_name=first,
               last_name=last,
               company=company
           )

       return DISPLAY_NAME_FORMAT_NO_COMPANY.format(
           first_name=first,
           last_name=last
       )

   def validate_display_name(display_name: str) -> tuple[bool, str]:
       """Validate display name meets format requirements.

       Returns (is_valid, reason).
       """
       if not display_name or not display_name.strip():
           return False, "Display name is empty"

       # Check for special characters that might cause issues
       if re.search(r'[<>"\']', display_name):
           return False, "Display name contains invalid characters"

       # Check length (most email clients truncate at 78 chars)
       if len(display_name) > 78:
           return False, "Display name too long (max 78 chars)"

       return True, "ok"
   ```

3. **Create full From header formatter:**
   ```python
   def format_from_header(
       email_address: str,
       first_name: str,
       last_name: str,
       company: Optional[str] = None
   ) -> str:
       """Format complete From header value.

       Example: "John Smith | Acme Corp <john@acme.com>"
       """
       display_name = format_display_name(first_name, last_name, company)

       # Validate
       is_valid, reason = validate_display_name(display_name)
       if not is_valid:
           logger.warning(f"Invalid display name: {reason}, using email only")
           return email_address

       return f'"{display_name}" <{email_address}>'
   ```

4. **Integrate into email sending:**
   ```python
   async def send_email(
       db: Session,
       mailbox_id: UUID,
       to_address: str,
       subject: str,
       body: str,
       **kwargs
   ) -> dict:
       """Send email with properly formatted From header."""

       mailbox = db.query(Mailbox).get(mailbox_id)
       user = mailbox.user
       client = mailbox.client

       from_header = format_from_header(
           email_address=mailbox.email_address,
           first_name=user.first_name,
           last_name=user.last_name,
           company=client.company_name
       )

       # Send via email provider
       result = await email_provider.send(
           from_=from_header,
           to=to_address,
           subject=subject,
           body=body,
           **kwargs
       )

       return result
   ```

5. **Add mailbox validation on setup:**
   ```python
   async def validate_mailbox_config(mailbox: Mailbox) -> list[str]:
       """Validate mailbox configuration including display name."""
       issues = []

       # Check display name
       display_name = format_display_name(
           mailbox.user.first_name,
           mailbox.user.last_name,
           mailbox.client.company_name
       )
       is_valid, reason = validate_display_name(display_name)
       if not is_valid:
           issues.append(f"Display name issue: {reason}")

       return issues
   ```

## Acceptance Criteria

- [ ] DISPLAY_NAME_FORMAT constant defined
- [ ] format_display_name() creates "First Last | Company" format
- [ ] validate_display_name() checks for issues
- [ ] format_from_header() creates complete From header
- [ ] All outgoing emails use formatted display name
- [ ] Graceful fallback if display name invalid

## Validation

```bash
# Check display name functions
grep -n "display_name\|format_from_header" src/engines/email.py

# Check format constant
grep -n "DISPLAY_NAME_FORMAT" src/engines/email.py

# Verify no syntax errors
python -m py_compile src/engines/email.py

# Type check
mypy src/engines/email.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #21
2. Report: "Fixed #21. Email display name format enforced: 'First Last | Company'."
