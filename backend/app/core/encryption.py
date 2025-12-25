"""Encryption utilities for sensitive data using Fernet (symmetric encryption)"""

import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
from app.core.logging import logger


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""

    _fernet: Optional[Fernet] = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        """Get or create Fernet instance"""
        if cls._fernet is None:
            # Get encryption key from settings
            encryption_key = settings.ENCRYPTION_KEY

            # Validate key format (must be 32 url-safe base64-encoded bytes)
            try:
                # Ensure the key is properly formatted for Fernet
                if len(encryption_key) == 32:
                    # If raw 32-byte key, encode it
                    key = base64.urlsafe_b64encode(encryption_key.encode())
                else:
                    # Assume it's already base64 encoded
                    key = encryption_key.encode()

                cls._fernet = Fernet(key)
            except Exception as e:
                logger.error(f"Failed to initialize Fernet: {e}")
                raise ValueError(
                    "Invalid encryption key. Must be 32 url-safe base64-encoded bytes. "
                    "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )

        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        Encrypt a string using Fernet symmetric encryption

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return plaintext

        try:
            fernet = cls._get_fernet()
            encrypted_bytes = fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        """
        Decrypt a Fernet-encrypted string

        Args:
            ciphertext: Encrypted string (base64 encoded)

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ciphertext

        try:
            fernet = cls._get_fernet()
            decrypted_bytes = fernet.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            logger.error("Failed to decrypt: Invalid token or wrong encryption key")
            raise ValueError("Failed to decrypt data. Token may be corrupted or encryption key changed.")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    @classmethod
    def encrypt_plaid_token(cls, access_token: str) -> str:
        """
        Encrypt a Plaid access token

        Args:
            access_token: Plaid access token

        Returns:
            Encrypted token
        """
        return cls.encrypt(access_token)

    @classmethod
    def decrypt_plaid_token(cls, encrypted_token: str) -> str:
        """
        Decrypt a Plaid access token

        Args:
            encrypted_token: Encrypted Plaid access token

        Returns:
            Decrypted access token
        """
        return cls.decrypt(encrypted_token)


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key

    Returns:
        Base64-encoded encryption key suitable for use with Fernet
    """
    return Fernet.generate_key().decode()


# Example usage:
# from app.core.encryption import EncryptionService, generate_encryption_key
#
# # Generate a new key (do this once and store in secrets manager):
# key = generate_encryption_key()
# print(f"New encryption key: {key}")
#
# # Encrypt a token:
# encrypted = EncryptionService.encrypt_plaid_token("access-sandbox-token-123")
#
# # Decrypt a token:
# decrypted = EncryptionService.decrypt_plaid_token(encrypted)
