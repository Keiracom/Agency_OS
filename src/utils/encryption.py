"""
Contract: src/utils/encryption.py
Purpose: Credential encryption using Fernet (AES-256)
Layer: 1 - utilities
Imports: cryptography, settings
Consumers: services

Provides secure encryption/decryption for sensitive credentials
like LinkedIn passwords using Fernet symmetric encryption (AES-128-CBC + HMAC).
"""

from cryptography.fernet import Fernet, InvalidToken

from src.config.settings import settings

# Module-level Fernet instance (lazy initialized)
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """
    Get or create Fernet encryption instance.

    Raises:
        ValueError: If CREDENTIAL_ENCRYPTION_KEY is not configured
    """
    global _fernet

    if _fernet is None:
        key = settings.credential_encryption_key
        if not key:
            raise ValueError(
                "CREDENTIAL_ENCRYPTION_KEY not configured. "
                'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        # Handle both string and bytes key formats
        key_bytes = key.encode() if isinstance(key, str) else key
        _fernet = Fernet(key_bytes)

    return _fernet


def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt a credential string.

    Args:
        plaintext: The sensitive credential to encrypt

    Returns:
        Base64-encoded encrypted string

    Raises:
        ValueError: If encryption key not configured
    """
    if not plaintext:
        raise ValueError("Cannot encrypt empty credential")

    fernet = _get_fernet()
    encrypted_bytes = fernet.encrypt(plaintext.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_credential(ciphertext: str) -> str:
    """
    Decrypt a credential string.

    Args:
        ciphertext: The encrypted credential (base64 encoded)

    Returns:
        Original plaintext credential

    Raises:
        ValueError: If decryption fails or key not configured
        InvalidToken: If ciphertext is invalid or tampered
    """
    if not ciphertext:
        raise ValueError("Cannot decrypt empty ciphertext")

    fernet = _get_fernet()
    try:
        decrypted_bytes = fernet.decrypt(ciphertext.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        raise ValueError(
            "Failed to decrypt credential. "
            "The encryption key may have changed or the data is corrupted."
        )


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Use this to create a new CREDENTIAL_ENCRYPTION_KEY.

    Returns:
        Base64-encoded 32-byte key string
    """
    return Fernet.generate_key().decode("utf-8")


def reset_fernet() -> None:
    """
    Reset the cached Fernet instance.

    Useful for testing or when the encryption key changes.
    """
    global _fernet
    _fernet = None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded keys
# [x] Key loaded from settings
# [x] Encrypt function
# [x] Decrypt function
# [x] Key generation helper
# [x] Error handling for missing key
# [x] Error handling for invalid tokens
# [x] Type hints on all functions
# [x] Docstrings on all functions
