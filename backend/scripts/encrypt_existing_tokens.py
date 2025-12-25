#!/usr/bin/env python3
"""Encrypt existing plaintext Plaid access tokens in the database

This migration script encrypts all existing plaintext Plaid access tokens
using Fernet encryption. Run this ONCE when deploying the encryption feature
to an existing environment with bank accounts.

IMPORTANT:
- Backup your database before running this script
- Make sure ENCRYPTION_KEY is set in your environment
- This script is idempotent - tokens that are already encrypted will be skipped

Usage:
    python scripts/encrypt_existing_tokens.py [--dry-run]

Options:
    --dry-run    Show what would be encrypted without making changes
"""

import argparse
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.encryption import EncryptionService
from app.core.logging import logger
from app.models.bank_account import BankAccount


def is_encrypted(token: str) -> bool:
    """
    Check if a token appears to be encrypted

    Fernet tokens start with 'gAAAAA' (base64 of version byte)
    and are always longer than typical access tokens
    """
    if not token:
        return False

    # Fernet tokens are base64 encoded and quite long (typically 200+ chars)
    # Plaid access tokens are typically shorter (around 50-100 chars)
    if len(token) > 150 and token.startswith(('gAAAAA', 'gAAAAAB')):
        return True

    # Try to decrypt - if it fails, it's not encrypted (or using wrong key)
    try:
        EncryptionService.decrypt(token)
        return True
    except Exception:
        return False


def encrypt_existing_tokens(dry_run: bool = False) -> None:
    """Encrypt all plaintext Plaid access tokens"""

    logger.info("Starting Plaid token encryption migration")
    logger.info(f"Dry run mode: {dry_run}")

    # Validate encryption key is set
    try:
        EncryptionService._get_fernet()
        logger.info("Encryption key validated")
    except Exception as e:
        logger.error(f"Failed to initialize encryption: {e}")
        logger.error("Make sure ENCRYPTION_KEY is set in your environment")
        return

    # Create database session
    engine = create_engine(str(settings.DATABASE_URL))

    with Session(engine) as session:
        # Get all bank accounts
        accounts = session.query(BankAccount).all()

        logger.info(f"Found {len(accounts)} bank accounts")

        encrypted_count = 0
        skipped_count = 0
        error_count = 0

        for account in accounts:
            try:
                # Check if already encrypted
                if is_encrypted(account.plaid_access_token):
                    logger.debug(f"Account {account.id} token already encrypted, skipping")
                    skipped_count += 1
                    continue

                # Get plaintext token
                plaintext_token = account.plaid_access_token

                if dry_run:
                    logger.info(
                        f"[DRY RUN] Would encrypt token for account {account.id} "
                        f"({account.name}) - token length: {len(plaintext_token)}"
                    )
                    encrypted_count += 1
                else:
                    # Encrypt the token
                    encrypted_token = EncryptionService.encrypt(plaintext_token)

                    # Update in database using raw SQL to bypass ORM encryption
                    session.execute(
                        text("UPDATE bank_accounts SET plaid_access_token = :token WHERE id = :id"),
                        {"token": encrypted_token, "id": str(account.id)}
                    )

                    logger.info(
                        f"Encrypted token for account {account.id} ({account.name})"
                    )
                    encrypted_count += 1

            except Exception as e:
                logger.error(f"Error encrypting token for account {account.id}: {e}")
                error_count += 1

        if not dry_run:
            session.commit()
            logger.info("Changes committed to database")

        # Summary
        logger.info("=" * 80)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total accounts: {len(accounts)}")
        logger.info(f"Encrypted: {encrypted_count}")
        logger.info(f"Already encrypted (skipped): {skipped_count}")
        logger.info(f"Errors: {error_count}")

        if dry_run:
            logger.info("")
            logger.info("This was a DRY RUN - no changes were made")
            logger.info("Run without --dry-run to apply changes")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Encrypt existing Plaid access tokens in database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be encrypted without making changes"
    )

    args = parser.parse_args()

    encrypt_existing_tokens(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
