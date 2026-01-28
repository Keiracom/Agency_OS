---
name: Fix 20 - Email Signature Generation
description: Implements dynamic email signature generation
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 20: Signature Generation

## Gap Reference
- **TODO.md Item:** #20
- **Priority:** P3 Medium (Email Engine)
- **Location:** `src/engines/email.py`
- **Issue:** Dynamic signature not implemented

## Pre-Flight Checks

1. Check existing signature handling:
   ```bash
   grep -rn "signature\|Signature" src/engines/email.py
   ```

2. Check user/sender profile fields:
   ```bash
   grep -rn "signature\|title\|phone\|linkedin" src/models/user.py
   ```

3. Review EMAIL.md spec:
   ```bash
   grep -n "signature" docs/architecture/distribution/EMAIL.md
   ```

## Implementation Steps

1. **Create signature template constants:**
   ```python
   SIGNATURE_TEMPLATES = {
       "minimal": """
   {name}
   {title}
   """,
       "standard": """
   Best regards,

   {name}
   {title} | {company}
   {phone}
   """,
       "full": """
   Best regards,

   {name}
   {title} | {company}
   {phone} | {email}
   {linkedin_url}
   """,
       "html_standard": """
   <p>Best regards,</p>
   <p>
   <strong>{name}</strong><br>
   {title} | {company}<br>
   <a href="tel:{phone}">{phone}</a>
   </p>
   """,
   }
   ```

2. **Create signature generator:**
   ```python
   from typing import Optional, Literal

   SignatureStyle = Literal["minimal", "standard", "full", "html_standard"]

   def generate_signature(
       sender_name: str,
       sender_title: Optional[str] = None,
       company: Optional[str] = None,
       phone: Optional[str] = None,
       email: Optional[str] = None,
       linkedin_url: Optional[str] = None,
       style: SignatureStyle = "standard"
   ) -> str:
       """Generate email signature from sender details.

       Args:
           sender_name: Full name of sender
           sender_title: Job title
           company: Company name
           phone: Phone number
           email: Email address
           linkedin_url: LinkedIn profile URL
           style: Signature template style

       Returns:
           Formatted signature string
       """
       template = SIGNATURE_TEMPLATES.get(style, SIGNATURE_TEMPLATES["standard"])

       signature = template.format(
           name=sender_name,
           title=sender_title or "",
           company=company or "",
           phone=phone or "",
           email=email or "",
           linkedin_url=linkedin_url or ""
       )

       # Clean up empty lines from missing fields
       lines = [line for line in signature.split("\n") if line.strip()]
       return "\n".join(lines)

   async def get_signature_for_mailbox(
       db: Session,
       mailbox_id: UUID
   ) -> str:
       """Get signature for a specific mailbox."""
       mailbox = db.query(Mailbox).get(mailbox_id)
       if not mailbox:
           return ""

       # Get sender profile
       user = mailbox.user
       client = mailbox.client

       return generate_signature(
           sender_name=user.full_name,
           sender_title=user.title,
           company=client.company_name,
           phone=user.phone or client.phone,
           email=mailbox.email_address,
           linkedin_url=user.linkedin_url,
           style=mailbox.signature_style or "standard"
       )
   ```

3. **Integrate into email composition:**
   ```python
   async def compose_email(
       db: Session,
       mailbox_id: UUID,
       to_address: str,
       subject: str,
       body: str,
       include_signature: bool = True
   ) -> dict:
       """Compose email with optional signature."""

       full_body = body

       if include_signature:
           signature = await get_signature_for_mailbox(db, mailbox_id)
           full_body = f"{body}\n\n{signature}"

       return {
           "from": mailbox.email_address,
           "to": to_address,
           "subject": subject,
           "body": full_body
       }
   ```

4. **Add signature_style to Mailbox model if needed:**
   ```python
   # In migration
   ALTER TABLE mailboxes ADD COLUMN signature_style VARCHAR(20) DEFAULT 'standard';
   ```

## Acceptance Criteria

- [ ] SIGNATURE_TEMPLATES with multiple styles
- [ ] generate_signature() creates signature from fields
- [ ] get_signature_for_mailbox() retrieves sender details
- [ ] compose_email() appends signature by default
- [ ] Handles missing fields gracefully (no empty lines)
- [ ] Supports both text and HTML signatures

## Validation

```bash
# Check signature functions exist
grep -n "signature\|generate_signature\|get_signature" src/engines/email.py

# Check templates
grep -n "SIGNATURE_TEMPLATES" src/engines/email.py

# Verify no syntax errors
python -m py_compile src/engines/email.py

# Type check
mypy src/engines/email.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #20
2. Report: "Fixed #20. Dynamic email signature generation implemented with 4 template styles."
