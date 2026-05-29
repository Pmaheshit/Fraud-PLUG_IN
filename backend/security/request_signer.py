"""
request_signer.py – HMAC-SHA256 request signing for API integrity.
Signs requests to verify they haven't been tampered with during transit.
"""
import hmac
import hashlib
import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RequestSigner:
    """HMAC-SHA256 request signing for API integrity verification."""

    @staticmethod
    def get_signing_key() -> str:
        """Get the secret key for signing."""
        key = os.getenv("REQUEST_SIGNING_KEY", "default_signing_key_change_in_prod")
        if key == "default_signing_key_change_in_prod":
            logger.warning("⚠️  Using default signing key. Set REQUEST_SIGNING_KEY in production!")
        return key

    @staticmethod
    def sign_request(
        body: dict,
        timestamp: str,
        method: str = "POST",
        path: str = "/api/v1",
    ) -> str:
        """
        Generate HMAC-SHA256 signature for a request.

        Args:
            body: Request body as dictionary
            timestamp: ISO-8601 timestamp
            method: HTTP method
            path: API path

        Returns:
            Base64-encoded HMAC signature
        """
        key = RequestSigner.get_signing_key().encode()
        body_str = json.dumps(body, sort_keys=True)
        message = f"{method}|{path}|{timestamp}|{body_str}".encode()
        signature = hmac.new(key, message, hashlib.sha256).hexdigest()
        return signature

    @staticmethod
    def verify_signature(
        signature: str,
        body: dict,
        timestamp: str,
        method: str = "POST",
        path: str = "/api/v1",
    ) -> bool:
        """
        Verify request signature.

        Args:
            signature: Provided HMAC signature
            body: Request body
            timestamp: Request timestamp
            method: HTTP method
            path: API path

        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = RequestSigner.sign_request(body, timestamp, method, path)
        return hmac.compare_digest(signature, expected_signature)

    @staticmethod
    def extract_signature(headers: dict) -> Optional[str]:
        """Extract signature from X-Signature header."""
        return headers.get("X-Signature") or headers.get("x-signature")

    @staticmethod
    def extract_timestamp(headers: dict) -> Optional[str]:
        """Extract timestamp from X-Timestamp header."""
        return headers.get("X-Timestamp") or headers.get("x-timestamp")
