#!/usr/bin/env python3
"""Generate a new Fernet encryption key for the application

This script generates a new encryption key that can be stored in AWS Secrets Manager
under the app-security secret's 'encryption_key' field.

Usage:
    python scripts/generate_encryption_key.py
"""

from cryptography.fernet import Fernet


def main():
    """Generate and print a new Fernet encryption key"""
    key = Fernet.generate_key().decode()

    print("=" * 80)
    print("NEW FERNET ENCRYPTION KEY")
    print("=" * 80)
    print()
    print(f"  {key}")
    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print()
    print("1. Store this key in AWS Secrets Manager:")
    print()
    print("   For development environment:")
    print(f'   aws secretsmanager update-secret \\')
    print(f'     --secret-id development/wumbo/app-security \\')
    print(f'     --secret-string \'{{"jwt_secret_key":"YOUR_JWT_KEY","encryption_key":"{key}","algorithm":"HS256"}}\'')
    print()
    print("   For production environment:")
    print(f'   aws secretsmanager update-secret \\')
    print(f'     --secret-id production/wumbo/app-security \\')
    print(f'     --secret-string \'{{"jwt_secret_key":"YOUR_JWT_KEY","encryption_key":"{key}","algorithm":"HS256"}}\'')
    print()
    print("2. Set in your local .env file for testing:")
    print(f"   ENCRYPTION_KEY={key}")
    print()
    print("WARNING: Keep this key secret! Anyone with this key can decrypt sensitive data.")
    print("         If you lose this key, you will not be able to decrypt existing data.")
    print()


if __name__ == "__main__":
    main()
