"""
AU phone number classifier.

Normalises raw phone strings to E.164 (+61...) and classifies:
  mobile (04xx)      → sms_ok=True,  voice_ai_ok=True
  landline (02/03/07/08) → sms_ok=False, voice_ai_ok=True
  service (1300/1800/13xx) → sms_ok=False, voice_ai_ok=False
  unclassified       → sms_ok=False, voice_ai_ok=False

Ratified: 2026-04-13. Contact taxonomy: business_general vs dm_direct.
"""
from __future__ import annotations
import re
from typing import TypedDict


class PhoneClassification(TypedDict):
    raw: str
    normalized_e164: str
    phone_type: str  # mobile | landline | service_number | unclassified
    sms_ok: bool
    voice_ai_ok: bool


def classify_au_phone(raw: str) -> PhoneClassification:
    """Classify an Australian phone number."""
    cleaned = re.sub(r'[\s\-\.\(\)]', '', raw.strip())

    # Normalise to E.164
    if cleaned.startswith('+61'):
        e164 = cleaned
        local = '0' + cleaned[3:]
    elif cleaned.startswith('61') and len(cleaned) >= 11:
        e164 = '+' + cleaned
        local = '0' + cleaned[2:]
    elif cleaned.startswith('0'):
        e164 = '+61' + cleaned[1:]
        local = cleaned
    elif cleaned.startswith('1') and len(cleaned) <= 10:
        # 1300/1800/13xx — no E.164 conversion
        e164 = cleaned
        local = cleaned
    else:
        return PhoneClassification(
            raw=raw, normalized_e164=cleaned,
            phone_type='unclassified', sms_ok=False, voice_ai_ok=False,
        )

    # Classify by prefix
    if local.startswith('04') or e164.startswith('+614'):
        return PhoneClassification(
            raw=raw, normalized_e164=e164,
            phone_type='mobile', sms_ok=True, voice_ai_ok=True,
        )

    if local.startswith(('02', '03', '07', '08')) or e164.startswith(('+612', '+613', '+617', '+618')):
        return PhoneClassification(
            raw=raw, normalized_e164=e164,
            phone_type='landline', sms_ok=False, voice_ai_ok=True,
        )

    if local.startswith(('1300', '1800', '13')):
        return PhoneClassification(
            raw=raw, normalized_e164=local,  # service numbers don't have E.164
            phone_type='service_number', sms_ok=False, voice_ai_ok=False,
        )

    return PhoneClassification(
        raw=raw, normalized_e164=e164,
        phone_type='unclassified', sms_ok=False, voice_ai_ok=False,
    )
