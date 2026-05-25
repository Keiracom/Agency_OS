"""keiracom_system.vault — secret-store adapters (Vault Transit envelope).

Phase A2 build per bd Agency_OS-31bk.
"""

from .vault_decryptor import (
    DEFAULT_KEY_NAME_PREFIX,
    VaultDecryptError,
    VaultDecryptor,
    from_env,
)

__all__ = [
    "DEFAULT_KEY_NAME_PREFIX",
    "VaultDecryptError",
    "VaultDecryptor",
    "from_env",
]
