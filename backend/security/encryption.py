"""
encryption.py – Data encryption service for sensitive fields.
Encrypts face vectors, device fingerprints, and PII using AES-256.
"""
import os
import base64
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Encrypts and decrypts sensitive data using AES-256 (Fernet).
    The encryption key is derived from an environment variable.
    """

    _cipher = None

    @classmethod
    def _init_cipher(cls) -> None:
        """Initialize the encryption cipher from the secret key."""
        if cls._cipher is not None:
            return

        # Get or generate master key
        master_key = os.getenv("ENCRYPTION_KEY")

        if not master_key:
            # Generate a new key if not provided
            master_key = Fernet.generate_key().decode()
            logger.warning("⚠️  No ENCRYPTION_KEY set. Using generated key.")
            logger.warning(f"Set this in your environment: ENCRYPTION_KEY={master_key}")
        else:
            # Ensure the key is in the correct format
            if isinstance(master_key, str):
                master_key = master_key.encode()

        cls._cipher = Fernet(master_key)

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        Encrypt plaintext and return base64-encoded ciphertext.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        cls._init_cipher()
        ciphertext = cls._cipher.encrypt(plaintext.encode())
        return base64.b64encode(ciphertext).decode()

    @classmethod
    def decrypt(cls, encrypted: str) -> str:
        """
        Decrypt base64-encoded ciphertext.

        Args:
            encrypted: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        cls._init_cipher()
        try:
            ciphertext = base64.b64decode(encrypted)
            plaintext = cls._cipher.decrypt(ciphertext)
            return plaintext.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")

    @classmethod
    def encrypt_json(cls, data: dict) -> str:
        """Encrypt a dictionary by converting to JSON first."""
        import json
        plaintext = json.dumps(data)
        return cls.encrypt(plaintext)

    @classmethod
    def decrypt_json(cls, encrypted: str) -> dict:
        """Decrypt and parse JSON."""
        import json
        plaintext = cls.decrypt(encrypted)
        return json.loads(plaintext)
