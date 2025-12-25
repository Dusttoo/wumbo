#!/usr/bin/env python3
"""Test script for Plaid webhook verification

This script demonstrates how webhook verification works and can be used
to test the verification logic with sample webhooks.

Usage:
    python scripts/test_webhook_verification.py
"""

import hashlib
import json
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jose import jwt


def create_test_webhook_jwt(body: dict, secret: str = "test_secret") -> str:
    """
    Create a test Plaid webhook JWT

    Args:
        body: Webhook body dictionary
        secret: Secret key (in production, this would be Plaid's private key)

    Returns:
        JWT string for the Plaid-Verification header
    """
    # Convert body to JSON bytes
    body_bytes = json.dumps(body, separators=(",", ":")).encode()

    # Calculate SHA256 hash of body
    body_hash = hashlib.sha256(body_bytes).hexdigest()

    # Create JWT payload
    payload = {
        "iat": int(time.time()),  # Issued at
        "request_body_sha256": body_hash,
    }

    # Create JWT (note: Plaid uses ES256, but for testing we can use HS256)
    token = jwt.encode(payload, secret, algorithm="HS256")

    return token


def test_webhook_verification():
    """Test webhook verification with sample data"""

    # Sample webhook body
    webhook_body = {
        "webhook_type": "TRANSACTIONS",
        "webhook_code": "SYNC_UPDATES_AVAILABLE",
        "item_id": "test_item_123",
    }

    print("=" * 80)
    print("PLAID WEBHOOK VERIFICATION TEST")
    print("=" * 80)
    print()

    # Create test JWT
    jwt_token = create_test_webhook_jwt(webhook_body)

    print("1. Sample Webhook Body:")
    print(json.dumps(webhook_body, indent=2))
    print()

    print("2. Generated JWT (Plaid-Verification header):")
    print(jwt_token)
    print()

    # Calculate body hash
    body_bytes = json.dumps(webhook_body, separators=(",", ":")).encode()
    body_hash = hashlib.sha256(body_bytes).hexdigest()

    print("3. Request Body SHA256 Hash:")
    print(body_hash)
    print()

    # Decode JWT
    decoded = jwt.decode(jwt_token, options={"verify_signature": False})

    print("4. Decoded JWT Payload:")
    print(json.dumps(decoded, indent=2))
    print()

    # Verify hash matches
    print("5. Verification:")
    if decoded["request_body_sha256"] == body_hash:
        print("   ✓ Body hash matches JWT claim")
    else:
        print("   ✗ Body hash DOES NOT match JWT claim")

    # Check timestamp
    current_time = int(time.time())
    age = current_time - decoded["iat"]
    print(f"   ✓ Webhook age: {age} seconds")

    print()
    print("=" * 80)
    print("HOW TO USE IN PRODUCTION")
    print("=" * 80)
    print()
    print("1. Plaid sends webhooks to: POST /api/v1/plaid/webhook")
    print("2. Include header: Plaid-Verification: <jwt_token>")
    print("3. Our middleware verifies:")
    print("   - JWT structure is valid")
    print("   - Request body hash matches JWT claim")
    print("   - Webhook is not too old (< 5 minutes)")
    print()
    print("4. Example curl command:")
    print()
    print(f"curl -X POST https://api.wumbo.app/api/v1/plaid/webhook \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -H 'Plaid-Verification: {jwt_token}' \\")
    print(f"  -d '{json.dumps(webhook_body)}'")
    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    test_webhook_verification()
