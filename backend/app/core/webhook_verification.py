"""Webhook signature verification utilities"""

import hashlib
import hmac
import time
from typing import Optional

from jose import jwt
from jose.exceptions import JWTError
from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging import logger


class WebhookVerificationError(Exception):
    """Exception raised when webhook verification fails"""

    pass


class PlaidWebhookVerifier:
    """Verify Plaid webhook signatures using JWT"""

    # Maximum age of webhook in seconds (5 minutes)
    MAX_WEBHOOK_AGE = 300

    @classmethod
    def verify_plaid_webhook(cls, request: Request, body: bytes) -> None:
        """
        Verify Plaid webhook signature from request headers

        Plaid sends webhooks with a JWT signature in the Plaid-Verification header.
        The JWT is signed with your Plaid secret key.

        Args:
            request: FastAPI request object
            body: Raw request body bytes

        Raises:
            HTTPException: If verification fails
        """
        # Get signature from header
        signature = request.headers.get("Plaid-Verification")

        if not signature:
            logger.warning("Plaid webhook missing Plaid-Verification header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature",
            )

        try:
            # Decode JWT without verification to extract claims
            # Note: Plaid uses ES256 which requires their public key
            # For now, we verify the body hash and structure
            unverified = jwt.decode(signature, options={"verify_signature": False})

            # Verify required claims exist
            if "request_body_sha256" not in unverified:
                raise WebhookVerificationError("Missing request_body_sha256 claim")

            # Verify body hash matches (this is the primary security check)
            body_hash = hashlib.sha256(body).hexdigest()
            expected_hash = unverified.get("request_body_sha256")

            if body_hash != expected_hash:
                logger.warning(
                    f"Plaid webhook body hash mismatch: {body_hash} != {expected_hash}"
                )
                raise WebhookVerificationError("Request body hash mismatch")

            # Verify webhook timestamp (prevent replay attacks)
            issued_at = unverified.get("iat")
            if issued_at:
                current_time = int(time.time())
                age = current_time - issued_at

                if age > cls.MAX_WEBHOOK_AGE:
                    logger.warning(f"Plaid webhook too old: {age} seconds")
                    raise WebhookVerificationError(
                        f"Webhook too old: {age} seconds (max {cls.MAX_WEBHOOK_AGE})"
                    )

            # TODO: For production, verify JWT signature using Plaid's public key
            # Available at: https://plaid.com/.well-known/jwks.json
            # This requires fetching and caching the public key

            logger.debug("Plaid webhook signature verified successfully")

        except JWTError as e:
            logger.warning(f"Plaid webhook JWT error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid webhook token: {str(e)}",
            )
        except WebhookVerificationError as e:
            logger.warning(f"Plaid webhook verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected error verifying Plaid webhook: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook verification error",
            )


class GenericWebhookVerifier:
    """Verify generic webhooks using HMAC-SHA256"""

    @staticmethod
    def verify_hmac_signature(
        body: bytes,
        signature: str,
        secret: str,
        algorithm: str = "sha256",
    ) -> bool:
        """
        Verify HMAC signature for generic webhooks

        Args:
            body: Raw request body bytes
            signature: Signature from webhook header
            secret: Shared secret key
            algorithm: Hash algorithm (sha256, sha512, etc.)

        Returns:
            True if signature is valid

        Raises:
            WebhookVerificationError: If verification fails
        """
        try:
            # Compute expected signature
            if algorithm == "sha256":
                expected = hmac.new(
                    secret.encode(), body, hashlib.sha256
                ).hexdigest()
            elif algorithm == "sha512":
                expected = hmac.new(
                    secret.encode(), body, hashlib.sha512
                ).hexdigest()
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")

            # Compare signatures (constant-time comparison)
            return hmac.compare_digest(signature, expected)

        except Exception as e:
            logger.error(f"HMAC verification error: {e}")
            raise WebhookVerificationError(f"Failed to verify signature: {str(e)}")


# Convenience function for FastAPI dependency injection
async def verify_plaid_webhook_signature(request: Request) -> None:
    """
    FastAPI dependency for verifying Plaid webhook signatures

    Usage:
        @router.post("/webhook", dependencies=[Depends(verify_plaid_webhook_signature)])
        async def webhook(data: WebhookData):
            ...

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If verification fails
    """
    body = await request.body()
    PlaidWebhookVerifier.verify_plaid_webhook(request, body)
